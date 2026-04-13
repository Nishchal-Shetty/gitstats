from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from classifier import classify_repository
from database import Developer, Repository, RepoClassification, get_db, init_db
from scraper import (
    GENRE_QUERIES,
    get_developer_stats, get_repository_details, get_user_repos,
    scrape_and_store, search_repositories, strip_tz,
)

load_dotenv()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="GitStats API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://gitstats-frontend-53707559181.us-central1.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    genres: list[str]
    repos_per_genre: int = 50


class RecommendationsRefineRequest(BaseModel):
    username: str
    prompt: str
    repos: list[dict]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo_dict(repo: Repository, clf: RepoClassification | None) -> dict:
    return {
        "id": repo.id,
        "github_id": repo.github_id,
        "full_name": repo.full_name,
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "forks": repo.forks,
        "watchers": repo.watchers,
        "open_issues": repo.open_issues,
        "topics": repo.topics,
        "size": repo.size,
        "contributor_count": repo.contributor_count,
        "commit_count": repo.commit_count,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
        "scraped_at": repo.scraped_at,
        "genre": clf.genre if clf else None,
        "tags": clf.tags if clf else [],
        "confidence": clf.confidence if clf else None,
    }


async def _fetch_classify_store(full_name: str, db: AsyncSession) -> tuple[Repository, RepoClassification]:
    """Pull a repo from GitHub, classify it, persist both rows, and return them."""
    details = await get_repository_details(full_name)

    repo = Repository(
        github_id=details["github_id"],
        full_name=details["full_name"],
        description=details["description"],
        readme=details["readme"],
        stars=details["stars"],
        forks=details["forks"],
        watchers=details["watchers"],
        open_issues=details["open_issues"],
        language=details["language"],
        topics=details["topics"],
        size=details["size"],
        created_at=strip_tz(datetime.fromisoformat(details["created_at"].replace("Z", "+00:00"))),
        updated_at=strip_tz(datetime.fromisoformat(details["updated_at"].replace("Z", "+00:00"))),
        contributor_count=details["contributor_count"],
        commit_count=details["commit_count"],
    )
    db.add(repo)
    await db.flush()

    classification = await classify_repository(details)
    clf = RepoClassification(
        repo_id=repo.id,
        genre=classification["genre"],
        tags=classification["tags"],
        confidence=classification["confidence"],
    )
    db.add(clf)
    await db.commit()
    await db.refresh(repo)
    await db.refresh(clf)
    return repo, clf


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/scrape/start")
async def scrape_start(body: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_and_store, body.genres, body.repos_per_genre)
    return {"message": "scrape started", "genres": body.genres}


@app.get("/stats/repo/{owner}/{repo}")
async def stats_repo(owner: str, repo: str, db: AsyncSession = Depends(get_db)):
    full_name = f"{owner}/{repo}"

    # Check DB cache
    result = await db.execute(
        select(Repository)
        .where(Repository.full_name == full_name)
        .options(selectinload(Repository.classification))
    )
    repo_row = result.scalar_one_or_none()

    if repo_row is None:
        try:
            repo_row, clf = await _fetch_classify_store(full_name, db)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        clf = repo_row.classification

        # Re-classify if genre or confidence is missing
        if clf is None or not clf.genre or clf.genre == "unknown" or clf.confidence is None:
            log.info("Re-classifying %s (genre=%s, confidence=%s)", full_name, clf.genre if clf else None, clf.confidence if clf else None)
            try:
                result = await classify_repository({
                    "full_name": repo_row.full_name,
                    "description": repo_row.description,
                    "readme": repo_row.readme,
                    "language": repo_row.language,
                    "topics": repo_row.topics,
                })
                if clf is None:
                    clf = RepoClassification(repo_id=repo_row.id)
                    db.add(clf)
                clf.genre = result["genre"]
                clf.tags = result["tags"]
                clf.confidence = result["confidence"]
                await db.commit()
                await db.refresh(clf)
                log.info("Re-classified %s → genre=%s confidence=%s", full_name, clf.genre, clf.confidence)
            except Exception as exc:
                log.error("Re-classification failed for %s: %s", full_name, exc)

    # Genre comparison stats
    genre_stats: dict = {}
    if clf and clf.genre and clf.genre != "unknown":
        agg = await db.execute(
            select(
                func.avg(Repository.stars).label("avg_stars"),
                func.avg(Repository.forks).label("avg_forks"),
                func.avg(Repository.open_issues).label("avg_issues"),
                func.count(Repository.id).label("total_in_genre"),
            )
            .join(RepoClassification, RepoClassification.repo_id == Repository.id)
            .where(RepoClassification.genre == clf.genre)
        )
        row = agg.one()
        genre_stats = {
            "genre": clf.genre,
            "avg_stars": round(row.avg_stars or 0),
            "avg_forks": round(row.avg_forks or 0),
            "avg_issues": round(row.avg_issues or 0),
            "total_in_genre": row.total_in_genre,
        }

    return {**_repo_dict(repo_row, clf), "genre_comparison": genre_stats}


@app.get("/stats/developer/{username}")
async def stats_developer(username: str, db: AsyncSession = Depends(get_db)):
    # Check DB cache
    result = await db.execute(
        select(Developer).where(Developer.github_username == username)
    )
    dev = result.scalar_one_or_none()

    if dev is None:
        try:
            data = await get_developer_stats(username)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        dev = Developer(
            github_username=data["github_username"],
            display_name=data["display_name"],
            avatar_url=data["avatar_url"],
            followers=data["followers"],
            following=data["following"],
            public_repos=data["public_repos"],
            total_stars=data["total_stars"],
            top_languages=data["top_languages"],
        )
        db.add(dev)
        await db.commit()
        await db.refresh(dev)

    # Top repos for this developer from DB
    top_repos_result = await db.execute(
        select(Repository)
        .where(Repository.full_name.like(f"{username}/%"))
        .options(selectinload(Repository.classification))
        .order_by(Repository.stars.desc())
        .limit(10)
    )
    top_repos = top_repos_result.scalars().all()

    return {
        "github_username": dev.github_username,
        "display_name": dev.display_name,
        "avatar_url": dev.avatar_url,
        "followers": dev.followers,
        "following": dev.following,
        "public_repos": dev.public_repos,
        "total_stars": dev.total_stars,
        "top_languages": dev.top_languages,
        "fetched_at": dev.fetched_at,
        "top_repos": [_repo_dict(r, r.classification) for r in top_repos],
    }


@app.get("/repos/similar/{owner}/{repo}")
async def similar_repos(owner: str, repo: str, db: AsyncSession = Depends(get_db)):
    full_name = f"{owner}/{repo}"

    # Resolve genre for the target repo
    result = await db.execute(
        select(Repository)
        .where(Repository.full_name == full_name)
        .options(selectinload(Repository.classification))
    )
    repo_row = result.scalar_one_or_none()

    if repo_row is None or repo_row.classification is None:
        raise HTTPException(status_code=404, detail="Repo not found in DB. Fetch /stats/repo first.")

    genre = repo_row.classification.genre
    if not genre or genre == "unknown":
        raise HTTPException(status_code=404, detail="No genre classification available for this repo.")

    similar_result = await db.execute(
        select(Repository)
        .join(RepoClassification, RepoClassification.repo_id == Repository.id)
        .where(
            RepoClassification.genre == genre,
            Repository.full_name != full_name,
        )
        .options(selectinload(Repository.classification))
        .order_by(Repository.stars.desc())
        .limit(5)
    )
    similar = similar_result.scalars().all()

    return [_repo_dict(r, r.classification) for r in similar]


@app.post("/admin/reclassify")
async def admin_reclassify(db: AsyncSession = Depends(get_db)):
    """Re-classify all repos in the DB that have genre=null or genre='unknown'."""
    result = await db.execute(
        select(Repository)
        .outerjoin(RepoClassification, RepoClassification.repo_id == Repository.id)
        .where(
            (RepoClassification.genre == None) |
            (RepoClassification.genre == "unknown") |
            (RepoClassification.id == None)
        )
        .options(selectinload(Repository.classification))
    )
    repos = result.scalars().all()
    log.info("admin_reclassify: found %d repos to reclassify", len(repos))

    count = 0
    for repo_row in repos:
        try:
            result = await classify_repository({
                "full_name": repo_row.full_name,
                "description": repo_row.description,
                "readme": repo_row.readme,
                "language": repo_row.language,
                "topics": repo_row.topics,
            })
            clf = repo_row.classification
            if clf is None:
                clf = RepoClassification(repo_id=repo_row.id)
                db.add(clf)
            clf.genre = result["genre"]
            clf.tags = result["tags"]
            clf.confidence = result["confidence"]
            await db.flush()
            count += 1
            log.info("Reclassified %s → %s (%.2f)", repo_row.full_name, clf.genre, clf.confidence or 0)
        except Exception as exc:
            log.error("Reclassify failed for %s: %s", repo_row.full_name, exc)

    await db.commit()
    return {"reclassified": count}


@app.get("/repos/search")
async def search_repos(q: str = Query(..., min_length=2), db: AsyncSession = Depends(get_db)):
    pattern = f"%{q}%"
    result = await db.execute(
        select(Repository)
        .where(
            Repository.full_name.ilike(pattern)
            | Repository.description.ilike(pattern)
        )
        .options(selectinload(Repository.classification))
        .order_by(Repository.stars.desc())
        .limit(10)
    )
    repos = result.scalars().all()
    return [_repo_dict(r, r.classification) for r in repos]


# ---------------------------------------------------------------------------
# Recommendations endpoints
# ---------------------------------------------------------------------------

@app.get("/recommendations/{username}")
async def get_recommendations(username: str, db: AsyncSession = Depends(get_db)):
    """
    Recommend public repos the developer might want to contribute to.

    Strategy:
      1. Fetch the user's own GitHub repos and classify up to 3 of them with
         Claude to derive genres + tags that represent their expertise.
      2. Build a priority-ordered list from the local DB (genre match → language
         match → top-starred fallback).
      3. Search the GitHub API live using genre-specific keywords derived from
         the classification, so results aren't limited to the local DB.
      4. Merge, deduplicate, and return with a `source` field ("db" | "github").
    """
    own_prefix = f"{username}/%"

    # ── 1. Fetch + classify user's own repos ─────────────────────────────────
    try:
        user_repos_raw = await get_user_repos(username)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch {username}'s repos: {exc}")

    # Derive top languages (fast, no API calls)
    lang_counts: dict[str, int] = {}
    for r in user_repos_raw:
        if r.get("language"):
            lang_counts[r["language"]] = lang_counts.get(r["language"], 0) + 1
    top_languages = [lang for lang, _ in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

    # Classify top 3 repos (by stars) with Claude → genres + tags
    user_genres: list[str] = []
    user_tags: list[str] = []
    to_classify = sorted(user_repos_raw, key=lambda r: r.get("stars", 0), reverse=True)[:3]
    for repo in to_classify:
        try:
            clf = await classify_repository(repo)
            genre = clf.get("genre", "unknown")
            if genre and genre != "unknown" and genre not in user_genres:
                user_genres.append(genre)
            for tag in clf.get("tags", []):
                if tag not in user_tags:
                    user_tags.append(tag)
        except Exception as exc:
            log.warning("Skipping classification for %s: %s", repo.get("full_name"), exc)

    # Fall back to DB-stored genres for this user if Claude found nothing
    if not user_genres:
        db_genre_result = await db.execute(
            select(RepoClassification.genre)
            .join(Repository, Repository.id == RepoClassification.repo_id)
            .where(Repository.full_name.ilike(own_prefix))
            .distinct()
        )
        user_genres = [row[0] for row in db_genre_result.all() if row[0] and row[0] != "unknown"]

    log.info("recommendations/%s: genres=%s  tags=%s  langs=%s",
             username, user_genres, user_tags[:5], top_languages)

    # Keep track of full_names we've already added (avoid duplicates)
    seen: set[str] = {r["full_name"] for r in user_repos_raw}  # never recommend own repos

    # ── 2. Query local DB ────────────────────────────────────────────────────
    base_db_query = (
        select(Repository)
        .where(~Repository.full_name.ilike(own_prefix))
        .options(selectinload(Repository.classification))
        .order_by(Repository.stars.desc())
    )

    db_repos: list = []

    if user_genres:
        genre_result = await db.execute(
            base_db_query
            .join(RepoClassification, RepoClassification.repo_id == Repository.id)
            .where(RepoClassification.genre.in_(user_genres))
            .limit(15)
        )
        db_repos = list(genre_result.scalars().all())

    if len(db_repos) < 8 and top_languages:
        lang_result = await db.execute(
            base_db_query.where(Repository.language.in_(top_languages)).limit(15)
        )
        for r in lang_result.scalars().all():
            if r.id not in {x.id for x in db_repos}:
                db_repos.append(r)
            if len(db_repos) >= 15:
                break

    if len(db_repos) < 5:
        fallback_result = await db.execute(base_db_query.limit(15))
        for r in fallback_result.scalars().all():
            if r.id not in {x.id for x in db_repos}:
                db_repos.append(r)
            if len(db_repos) >= 15:
                break

    db_recs = []
    for r in db_repos[:15]:
        d = _repo_dict(r, r.classification)
        d["source"] = "db"
        seen.add(r.full_name)
        db_recs.append(d)

    # ── 3. Live GitHub search ────────────────────────────────────────────────
    # Build search queries: first from genres, then from user's own tags
    search_queries: list[str] = []
    for genre in user_genres[:2]:
        qs = GENRE_QUERIES.get(genre, [])
        if qs:
            search_queries.append(qs[0])   # most representative query per genre

    if user_tags:
        # Build a combined tag query using the top 3 descriptive tags
        tag_query = " ".join(user_tags[:3])
        search_queries.append(tag_query)

    if not search_queries and top_languages:
        search_queries.append(top_languages[0])  # bare language fallback

    github_recs: list[dict] = []
    for query in search_queries[:3]:            # cap at 3 GitHub searches
        try:
            results = await search_repositories(query, min_stars=50, per_page=10)
            for r in results:
                if r["full_name"] in seen:
                    continue
                # Derive genre from whichever GENRE_QUERIES entry matched
                derived_genre = next(
                    (g for g, qs in GENRE_QUERIES.items() if query in qs), None
                )
                github_recs.append({
                    "id": None,
                    "github_id": r["github_id"],
                    "full_name": r["full_name"],
                    "description": r.get("description"),
                    "language": r.get("language"),
                    "stars": r.get("stars", 0),
                    "forks": r.get("forks", 0),
                    "watchers": r.get("watchers", 0),
                    "open_issues": r.get("open_issues", 0),
                    "topics": r.get("topics", []),
                    "size": r.get("size", 0),
                    "contributor_count": None,
                    "commit_count": None,
                    "created_at": r.get("created_at"),
                    "updated_at": r.get("updated_at"),
                    "scraped_at": None,
                    "genre": derived_genre,
                    "tags": [],
                    "confidence": None,
                    "source": "github",
                })
                seen.add(r["full_name"])
                if len(github_recs) >= 10:
                    break
        except Exception as exc:
            log.warning("GitHub live search failed for %r: %s", query, exc)
        if len(github_recs) >= 10:
            break

    # ── 4. Merge DB + GitHub results ─────────────────────────────────────────
    recommendations = db_recs + github_recs

    return {
        "username": username,
        "top_languages": top_languages,
        "user_genres": user_genres,
        "user_tags": user_tags[:15],
        "recommendations": recommendations,
    }


@app.post("/recommendations/refine")
async def refine_recommendations(body: RecommendationsRefineRequest):
    """
    Use Claude to filter / re-rank the provided repo list based on a free-text prompt.
    Returns the repos reordered / filtered according to the AI's judgment.
    """
    import json as _json
    import anthropic as _anthropic

    if not body.repos:
        return {"repos": []}

    repo_summaries = []
    for i, r in enumerate(body.repos):
        repo_summaries.append(
            "{}: {} | lang={} | genre={} | stars={} | desc={}".format(
                i,
                r.get("full_name", "?"),
                r.get("language", "?"),
                r.get("genre", "?"),
                r.get("stars", 0),
                str(r.get("description", ""))[:120],
            )
        )
    repo_list_str = "\n".join(repo_summaries)

    prompt = (
        "You are helping a GitHub developer named '{}' find public repos to contribute to.\n\n"
        "The user says: \"{}\"\n\n"
        "Below is a numbered list of candidate repositories "
        "(index: full_name | lang | genre | stars | description):\n"
        "{}\n\n"
        "Return ONLY valid JSON — a list of integer indices for the repos that best match "
        "the user's request, ordered by relevance (most relevant first). "
        "Include at most 10. Example: [3, 0, 7]"
    ).format(body.username, body.prompt, repo_list_str)

    client = _anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(line for line in raw.splitlines() if not line.startswith("```")).strip()
        indices = _json.loads(raw)
        if not isinstance(indices, list):
            raise ValueError("Claude returned non-list: {}".format(raw))
        refined = [body.repos[i] for i in indices if isinstance(i, int) and 0 <= i < len(body.repos)]
        log.info("refine_recommendations: Claude selected %d/%d repos", len(refined), len(body.repos))
        return {"repos": refined, "warning": None}
    except Exception as exc:
        log.error("refine_recommendations: error: %s", exc)
        return {"repos": body.repos, "warning": str(exc)}
