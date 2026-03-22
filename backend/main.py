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
from scraper import get_developer_stats, get_repository_details, scrape_and_store, strip_tz

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
    allow_origins=["http://localhost:5173"],
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
