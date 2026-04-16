import asyncio
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from sqlalchemy import func, select, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import (
    Base, Developer, GenreSummary, PlatformSummary,
    Repository, RepoClassification, TrendingRepos,
)

load_dotenv()
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("SUPABASE_URL")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Aggregation jobs
# ---------------------------------------------------------------------------


async def compute_genre_summaries():
    """Precompute per-genre statistics and store in genre_summaries table."""
    log.info("Computing genre summaries...")
    async with AsyncSessionLocal() as db:
        # fetch all genres
        genres_result = await db.execute(
            select(RepoClassification.genre)
            .where(RepoClassification.genre != None)
            .where(RepoClassification.genre != "unknown")
            .distinct()
        )
        genres = [r[0] for r in genres_result.fetchall()]

        for genre in genres:
            # aggregate stats for this genre
            agg = await db.execute(
                select(
                    func.count(Repository.id).label("repo_count"),
                    func.avg(Repository.stars).label("avg_stars"),
                    func.avg(Repository.forks).label("avg_forks"),
                    func.avg(Repository.open_issues).label("avg_issues"),
                )
                .join(RepoClassification, RepoClassification.repo_id == Repository.id)
                .where(RepoClassification.genre == genre)
            )
            row = agg.one()

            # top languages in this genre
            lang_result = await db.execute(
                select(Repository.language, func.count(Repository.id).label("count"))
                .join(RepoClassification, RepoClassification.repo_id == Repository.id)
                .where(RepoClassification.genre == genre)
                .where(Repository.language != None)
                .group_by(Repository.language)
                .order_by(func.count(Repository.id).desc())
                .limit(5)
            )
            top_languages = [
                {"language": r.language, "count": r.count}
                for r in lang_result.fetchall()
            ]

            # top repos in this genre by stars
            top_repos_result = await db.execute(
                select(Repository.full_name, Repository.stars, Repository.description)
                .join(RepoClassification, RepoClassification.repo_id == Repository.id)
                .where(RepoClassification.genre == genre)
                .order_by(Repository.stars.desc())
                .limit(5)
            )
            top_repos = [
                {"full_name": r.full_name, "stars": r.stars, "description": r.description}
                for r in top_repos_result.fetchall()
            ]

            # upsert into genre_summaries
            stmt = pg_insert(GenreSummary).values(
                genre=genre,
                repo_count=row.repo_count,
                avg_stars=round(row.avg_stars or 0, 2),
                avg_forks=round(row.avg_forks or 0, 2),
                avg_issues=round(row.avg_issues or 0, 2),
                top_languages=top_languages,
                top_repos=top_repos,
                computed_at=datetime.now(),
            ).on_conflict_do_update(
                index_elements=["genre"],
                set_=dict(
                    repo_count=row.repo_count,
                    avg_stars=round(row.avg_stars or 0, 2),
                    avg_forks=round(row.avg_forks or 0, 2),
                    avg_issues=round(row.avg_issues or 0, 2),
                    top_languages=top_languages,
                    top_repos=top_repos,
                    computed_at=datetime.now(),
                )
            )
            await db.execute(stmt)

        await db.commit()
        log.info("Genre summaries computed for %d genres.", len(genres))


async def compute_platform_summary():
    """Precompute platform-wide statistics."""
    log.info("Computing platform summary...")
    async with AsyncSessionLocal() as db:
        total_repos = await db.scalar(select(func.count(Repository.id)))
        total_developers = await db.scalar(select(func.count(Developer.id)))
        total_genres = await db.scalar(
            select(func.count(RepoClassification.genre.distinct()))
            .where(RepoClassification.genre != None)
            .where(RepoClassification.genre != "unknown")
        )

        # language distribution across all repos
        lang_result = await db.execute(
            select(Repository.language, func.count(Repository.id).label("count"))
            .where(Repository.language != None)
            .group_by(Repository.language)
            .order_by(func.count(Repository.id).desc())
            .limit(10)
        )
        language_distribution = {r.language: r.count for r in lang_result.fetchall()}

        # genre distribution
        genre_result = await db.execute(
            select(RepoClassification.genre, func.count(RepoClassification.id).label("count"))
            .where(RepoClassification.genre != None)
            .where(RepoClassification.genre != "unknown")
            .group_by(RepoClassification.genre)
            .order_by(func.count(RepoClassification.id).desc())
        )
        genre_distribution = {r.genre: r.count for r in genre_result.fetchall()}

        # top repos overall
        top_result = await db.execute(
            select(Repository.full_name, Repository.stars, Repository.language)
            .order_by(Repository.stars.desc())
            .limit(10)
        )
        top_repos_overall = [
            {"full_name": r.full_name, "stars": r.stars, "language": r.language}
            for r in top_result.fetchall()
        ]

        # single-row upsert on id=1
        stmt = pg_insert(PlatformSummary).values(
            id=1,
            total_repos=total_repos,
            total_developers=total_developers,
            total_genres=total_genres,
            language_distribution=language_distribution,
            genre_distribution=genre_distribution,
            top_repos_overall=top_repos_overall,
            computed_at=datetime.now(),
        ).on_conflict_do_update(
            index_elements=["id"],
            set_=dict(
                total_repos=total_repos,
                total_developers=total_developers,
                total_genres=total_genres,
                language_distribution=language_distribution,
                genre_distribution=genre_distribution,
                top_repos_overall=top_repos_overall,
                computed_at=datetime.now(),
            )
        )
        await db.execute(stmt)
        await db.commit()
        log.info("Platform summary computed.")


async def compute_trending_repos():
    """
    Score repos by a simple trend metric and store top results.
    Trend score = stars + (forks * 2) + (watchers * 0.5) - (open_issues * 0.1)
    Weighted toward engagement over raw popularity.
    """
    log.info("Computing trending repos...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Repository,
                RepoClassification.genre,
                (
                    Repository.stars +
                    (Repository.forks * 2) +
                    (Repository.watchers * 0.5) -
                    (Repository.open_issues * 0.1)
                ).label("trend_score")
            )
            .outerjoin(RepoClassification, RepoClassification.repo_id == Repository.id)
            .order_by(text("trend_score DESC"))
            .limit(50)
        )
        rows = result.fetchall()

        # clear and reinsert trending table
        await db.execute(delete(TrendingRepos))
        for repo, genre, score in rows:
            db.add(TrendingRepos(
                full_name=repo.full_name,
                genre=genre,
                stars=repo.stars,
                forks=repo.forks,
                language=repo.language,
                description=repo.description,
                topics=repo.topics,
                trend_score=round(score or 0, 2),
                computed_at=datetime.now(),
            ))
        await db.commit()
        log.info("Trending repos computed: %d entries.", len(rows))

async def run_all():
    """Run all aggregation jobs in sequence."""
    await compute_genre_summaries()
    await compute_platform_summary()
    await compute_trending_repos()


# ---------------------------------------------------------------------------
# Scheduler entry point
# ---------------------------------------------------------------------------

async def main():
    await init_tables()

    scheduler = AsyncIOScheduler()

    await run_all()

    scheduler.add_job(
        run_all,
        "interval",
        hours=6,
        id="analytics",
        max_instances=1,
        coalesce=True   # Skip missed runs
    )
    scheduler.start()
    log.info("Analytics scheduler started.")

    # Keep the script alive
    # This sucks but it works for now
    try:
        while True: 
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(main())