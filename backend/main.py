from __future__ import annotations
import logging
import os
import redis.asyncio as redis
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from metrics import PrometheusHTTPMiddleware, metrics_response
from classifier import classify_repository
from auth import create_access_token, exchange_code_for_token, get_current_user
from database import (
    Developer, Repository, RepoClassification, User, GenreSummary, 
    LanguageSummary, PlatformSummary, TrendingRepos, get_db, init_db
)
from scraper import (
    fetch_github_user, get_developer_stats, get_repository_details,
    scrape_and_store, strip_tz,
)
from recommendations import router as recommendations_router

load_dotenv()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    r_host = os.getenv("REDIS_HOST", "localhost")
    r_port = int(os.getenv("REDIS_PORT", 6379))

    redis_client = redis.Redis(host=r_host, port=r_port, decode_responses=True)
    
    FastAPICache.init(RedisBackend(redis_client), prefix="gitstats")
    yield

    await redis_client.close()

app = FastAPI(title="GitStats API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://gitstats-frontend-53707559181.us-central1.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusHTTPMiddleware)

app.include_router(recommendations_router, prefix="/api/recommendations", tags=["Recommendations"])


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

    # upsert
    stmt = pg_insert(Repository).values(
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
    ).on_conflict_do_update(
        index_elements=["github_id"],
        set_=dict(
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
    ).returning(Repository)

    result = await db.execute(stmt)
    await db.flush()
    repo = result.scalar_one()

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


@app.get("/api/metrics")
async def metrics():
    return metrics_response()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class GitHubAuthRequest(BaseModel):
    code: str


@app.post("/api/auth/github")
async def auth_github(body: GitHubAuthRequest, db: AsyncSession = Depends(get_db)):
    """Exchange GitHub OAuth code for a JWT. Creates user if new, updates last_login if existing."""
    # 1. Exchange code for GitHub access token
    try:
        gh_token = await exchange_code_for_token(body.code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth failed: {exc}")

    # 2. Fetch GitHub user profile
    try:
        gh_user = await fetch_github_user(gh_token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch GitHub user: {exc}")

    github_id = gh_user["id"]
    username = gh_user["login"]

    # 3. Find or create user
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            github_id=github_id,
            username=username,
            display_name=gh_user.get("name"),
            avatar_url=gh_user.get("avatar_url"),
            email=gh_user.get("email"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        log.info("Registered new user: %s (github_id=%d)", username, github_id)
    else:
        user.last_login = datetime.utcnow()
        user.avatar_url = gh_user.get("avatar_url", user.avatar_url)
        user.display_name = gh_user.get("name", user.display_name)
        await db.commit()
        await db.refresh(user)
        log.info("User logged in: %s (github_id=%d)", username, github_id)

    # 4. Issue JWT
    token = create_access_token({"sub": str(user.github_id), "username": user.username})

    return {
        "token": token,
        "user": {
            "id": user.id,
            "github_id": user.github_id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "email": user.email,
        },
    }


@app.get("/api/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the currently authenticated user's profile."""
    github_id = int(current_user["sub"])
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "github_id": user.github_id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "email": user.email,
    }


@app.post("/api/scrape/start")
async def scrape_start(body: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_and_store, body.genres, body.repos_per_genre)
    return {"message": "scrape started", "genres": body.genres}


@app.get("/api/stats/repo/{owner}/{repo}")
@cache(expire=3600, namespace="repo")
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


@app.get("/api/stats/developer/{username}")
@cache(expire=3600, namespace="developer")
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

        # upsert to avoid uniqueViolationError
        stmt = pg_insert(Developer).values(
            github_username=data["github_username"],
            display_name=data["display_name"],
            avatar_url=data["avatar_url"],
            followers=data["followers"],
            following=data["following"],
            public_repos=data["public_repos"],
            total_stars=data["total_stars"],
            top_languages=data["top_languages"],
        ).on_conflict_do_update(
            index_elements=["github_username"],
            set_=dict(
                display_name=data["display_name"],
                avatar_url=data["avatar_url"],
                followers=data["followers"],
                following=data["following"],
                public_repos=data["public_repos"],
                total_stars=data["total_stars"],
                top_languages=data["top_languages"],
            )
        ).returning(Developer)

        result = await db.execute(stmt)
        await db.commit()
        dev = result.scalar_one()

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


@app.get("/api/repos/similar/{owner}/{repo}")
@cache(expire=21600, namespace="similar")
async def similar_repos(owner: str, repo: str, db: AsyncSession = Depends(get_db)):
    full_name = f"{owner}/{repo}"

    # Resolve genre for the target repo
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

    if clf is None or not clf.genre or clf.genre == "unknown":
        raise HTTPException(status_code=404, detail="No genre classification available for this repo.")

    genre = clf.genre

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


@app.post("/api/admin/reclassify")
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
    # prevent stale cache hits during reclassify
    await FastAPICache.clear(namespace="repo")
    await FastAPICache.clear(namespace="similar")
    await FastAPICache.clear(namespace="recommendations")
    await FastAPICache.clear(namespace="analytics")
    return {"reclassified": count}


@app.get("/api/repos/search")
@cache(expire=600, namespace="search")
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

@app.get("/api/analytics/genres")
async def analytics_genres(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GenreSummary).order_by(GenreSummary.repo_count.desc())
    )
    summaries = result.scalars().all()
    return [
        {
            "genre": s.genre,
            "repo_count": s.repo_count,
            "avg_stars": s.avg_stars,
            "avg_forks": s.avg_forks,
            "avg_issues": s.avg_issues,
            "top_languages": s.top_languages,
            "top_repos": s.top_repos,
            "computed_at": s.computed_at,
        }
        for s in summaries
    ]

@app.get("/api/analytics/languages")
async def analytics_languages(db: AsyncSession = Depends(get_db)):
    """Fetch precomputed language analytics and top repositories per language."""
    result = await db.execute(
        select(LanguageSummary).order_by(LanguageSummary.repo_count.desc())
    )
    summaries = result.scalars().all()
    
    return [
        {
            "language": s.language,
            "repo_count": s.repo_count,
            "avg_stars": s.avg_stars,
            "avg_forks": s.avg_forks,
            "avg_issues": s.avg_issues,
            "top_genres": s.top_genres,
            "top_repos": s.top_repos,
            "computed_at": s.computed_at,
        }
        for s in summaries
    ]

@app.get("/api/analytics/platform")
async def analytics_platform(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlatformSummary).where(PlatformSummary.id == 1))
    summary = result.scalar_one_or_none()
    if summary is None:
        # Handles the window between first startup and first computation
        raise HTTPException(status_code=503, detail="Analytics not yet computed.")
    return summary

@app.get("/api/analytics/trending")
async def analytics_trending(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrendingRepos).order_by(TrendingRepos.trend_score.desc())
    )
    return result.scalars().all()