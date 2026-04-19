from __future__ import annotations
import logging
import os
import tempfile
import json as _json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from fastapi_cache.decorator import cache
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pdfminer.high_level import extract_text
import anthropic

from classifier import classify_repository
from database import Repository, RepoClassification, get_db, AsyncSessionLocal
from scraper import (
    GENRE_QUERIES,
    fetch_repo_issues,
    get_repository_details,
    get_user_repos,
    search_repositories,
    strip_tz,
)

log = logging.getLogger(__name__)

router = APIRouter()

class RecommendationsRefineRequest(BaseModel):
    username: str
    prompt: str
    repos: list[dict]

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


async def _persist_live_repos(live_recs: list[dict]) -> None:
    """
    Background task: for each live GitHub repo not already in the DB,
    insert a basic row immediately, then enrich with full details + classification.
    """
    for rec in live_recs:
        github_id = rec.get("github_id")
        full_name = rec.get("full_name", "")
        if not github_id or not full_name:
            continue
        try:
            async with AsyncSessionLocal() as db:
                # 1. Skip if already in DB
                existing = await db.execute(
                    select(Repository).where(Repository.github_id == github_id)
                )
                if existing.scalar_one_or_none() is not None:
                    log.debug("_persist_live_repos: %s already in DB, skipping", full_name)
                    continue

                # 2. Quick insert with search-result fields
                repo = Repository(
                    github_id=github_id,
                    full_name=full_name,
                    description=rec.get("description"),
                    readme="",
                    stars=rec.get("stars", 0),
                    forks=rec.get("forks", 0),
                    watchers=rec.get("watchers", 0),
                    open_issues=rec.get("open_issues", 0),
                    language=rec.get("language"),
                    topics=rec.get("topics", []),
                    size=rec.get("size", 0),
                    contributor_count=0,
                    commit_count=0,
                    created_at=strip_tz(datetime.fromisoformat(
                        rec["created_at"].replace("Z", "+00:00")
                    )) if rec.get("created_at") else datetime.utcnow(),
                    updated_at=strip_tz(datetime.fromisoformat(
                        rec["updated_at"].replace("Z", "+00:00")
                    )) if rec.get("updated_at") else datetime.utcnow(),
                )
                db.add(repo)
                await db.commit()
                await db.refresh(repo)
                log.info("_persist_live_repos: inserted %s (id=%s)", full_name, repo.id)

            # 3. Enrich: fetch full details
            try:
                details = await get_repository_details(full_name)
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Repository).where(Repository.github_id == github_id)
                    )
                    repo = result.scalar_one_or_none()
                    if repo:
                        repo.readme          = details.get("readme", "")
                        repo.contributor_count = details.get("contributor_count", 0)
                        repo.commit_count    = details.get("commit_count", 0)
                        repo.stars           = details.get("stars", repo.stars)
                        repo.forks           = details.get("forks", repo.forks)
                        repo.open_issues     = details.get("open_issues", repo.open_issues)
                        await db.commit()
                        log.info("_persist_live_repos: enriched %s", full_name)
            except Exception as exc:
                log.warning("_persist_live_repos: enrich failed for %s: %s", full_name, exc)

            # 4. Classify with Claude
            try:
                clf_data = {
                    "full_name": full_name,
                    "description": rec.get("description") or "",
                    "language": rec.get("language") or "",
                    "topics": rec.get("topics", []),
                    "readme": "",
                }
                clf = await classify_repository(clf_data)
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Repository).where(Repository.github_id == github_id)
                    )
                    repo = result.scalar_one_or_none()
                    if repo and clf.get("genre") and clf["genre"] != "unknown":
                        existing_clf = await db.execute(
                            select(RepoClassification).where(
                                RepoClassification.repo_id == repo.id
                            )
                        )
                        if existing_clf.scalar_one_or_none() is None:
                            db.add(RepoClassification(
                                repo_id=repo.id,
                                genre=clf["genre"],
                                tags=clf.get("tags", []),
                                confidence=clf.get("confidence"),
                            ))
                            await db.commit()
                            log.info("_persist_live_repos: classified %s → %s", full_name, clf["genre"])
            except Exception as exc:
                log.warning("_persist_live_repos: classify failed for %s: %s", full_name, exc)

        except Exception as exc:
            log.error("_persist_live_repos: unexpected error for %s: %s", full_name, exc)


@router.get("/{username}")
@cache(expire=3600, namespace="recommendations")
async def get_recommendations(
    username: str,
    background_tasks: BackgroundTasks,
    resume_keywords: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Recommend public repos the developer might want to contribute to.
    """
    own_prefix = f"{username}/%"

    try:
        user_repos_raw = await get_user_repos(username)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch {username}'s repos: {exc}")

    lang_counts: dict[str, int] = {}
    for r in user_repos_raw:
        if r.get("language"):
            lang_counts[r["language"]] = lang_counts.get(r["language"], 0) + 1
    top_languages = [lang for lang, _ in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

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

    seen: set[str] = {r["full_name"] for r in user_repos_raw}

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

    search_queries: list[str] = []
    for genre in user_genres[:2]:
        qs = GENRE_QUERIES.get(genre, [])
        if qs:
            search_queries.append(qs[0])

    if user_tags:
        tag_query = " ".join(user_tags[:3])
        search_queries.append(tag_query)
        
    if resume_keywords:
        search_queries.append(f"{resume_keywords} {top_languages[0] if top_languages else ''}".strip())

    if not search_queries and top_languages:
        search_queries.append(top_languages[0])

    github_recs: list[dict] = []
    for query in search_queries[:3]:
        try:
            results = await search_repositories(query, min_stars=50, per_page=10)
            for r in results:
                if r["full_name"] in seen:
                    continue
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

    recommendations = db_recs + github_recs

    if github_recs:
        background_tasks.add_task(_persist_live_repos, github_recs)
        log.info("Scheduled background persistence for %d live repos", len(github_recs))

    return {
        "username": username,
        "top_languages": top_languages,
        "user_genres": user_genres,
        "user_tags": user_tags[:15],
        "recommendations": recommendations,
    }


@router.post("/refine")
async def refine_recommendations(body: RecommendationsRefineRequest):
    """
    Use Claude to filter / re-rank the provided repo list based on a free-text prompt.
    """
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

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
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


@router.get("/issues/{owner}/{repo}")
async def get_repo_issues_for_user(
    owner: str,
    repo: str,
    username: str = Query(default=""),
    genres: str = Query(default=""),
    tags: str = Query(default=""),
):
    """
    Fetch 3 open GitHub issues from `owner/repo` that are most suitable
    for the given user to work on.
    """
    full_name = "{}/{}".format(owner, repo)

    try:
        issues = await fetch_repo_issues(owner, repo, per_page=20)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not fetch issues for {}: {}".format(full_name, exc))

    if not issues:
        return {"issues": [], "full_name": full_name}
    if len(issues) <= 3:
        return {"issues": issues[:3], "full_name": f"{owner}/{repo}"}

    user_genres_list = [g.strip() for g in genres.split(",") if g.strip()]
    user_tags_list   = [t.strip() for t in tags.split(",") if t.strip()]

    issue_lines = []
    for i, iss in enumerate(issues):
        label_str = ", ".join(iss["labels"]) or "none"
        issue_lines.append(
            "{}: #{} | {} | labels=[{}] | comments={} | excerpt: {}".format(
                i, iss["number"], iss["title"], label_str,
                iss["comments"], iss["body_excerpt"][:120],
            )
        )
    issue_list_str = "\n".join(issue_lines)

    prompt = (
        "You are helping a developer find GitHub issues to contribute to in the repo '{}'.\n\n"
        "The developer skills: genres=[{}], tags=[{}], username={}.\n\n"
        "Below are open issues (index: #number | title | labels | comments | excerpt):\n"
        "{}\n\n"
        "Choose exactly 3 indices (integers) that are the MOST suitable for this developer "
        "given their skills - prefer labelled issues, achievable scope, and relevance.\n"
        "Return ONLY a valid JSON list of 3 integers. Example: [2, 0, 5]"
    ).format(
        full_name,
        ", ".join(user_genres_list) or "unknown",
        ", ".join(user_tags_list) or "unknown",
        username or "unknown",
        issue_list_str,
    )

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(ln for ln in raw.splitlines() if not ln.startswith("```")).strip()
        indices = _json.loads(raw)
        if not isinstance(indices, list) or len(indices) == 0:
            raise ValueError("unexpected response: {}".format(raw))
        selected = [issues[i] for i in indices[:3] if isinstance(i, int) and 0 <= i < len(issues)]
        seen_nums = {s["number"] for s in selected}
        for iss in issues:
            if len(selected) >= 3:
                break
            if iss["number"] not in seen_nums:
                selected.append(iss)
        log.info("get_repo_issues: picked %s for %s", [s["number"] for s in selected], full_name)
    except Exception as exc:
        log.warning("get_repo_issues: Claude failed (%s), using top-3", exc)
        selected = issues[:3]

    return {"issues": selected, "full_name": full_name}


@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts a PDF resume, parses its text, and asks Claude to extract the top technical keywords.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        try:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    try:
        text = extract_text(tmp_path)
    except Exception as e:
        log.error("Failed to parse PDF resume: %s", e)
        raise HTTPException(status_code=400, detail="Failed to parse PDF content.")
    finally:
        os.remove(tmp_path)

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No readable text found in PDF.")

    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    prompt = (
        "Extract the top 5-10 core technical keywords, frameworks, skills, and programming "
        "languages from the following resume text. Output ONLY a comma-separated list of "
        "keywords, nothing else. Do not include soft skills.\n\n"
        f"Resume:\n{text[:8000]}"
    )

    try:
        resp = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}]
        )
        content_text = resp.content[0].text.strip()
        keywords = [k.strip() for k in content_text.split(",") if k.strip()]
        return {"keywords": keywords}
    except Exception as e:
        log.error("Claude keyword extraction failed: %s", e)
        return {"keywords": []}
