from __future__ import annotations
import asyncio
import base64
import logging
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

load_dotenv()

log = logging.getLogger(__name__)


def strip_tz(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=None)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"

# Keywords used when searching GitHub for each genre (also used by recommendations)
GENRE_QUERIES: dict[str, list[str]] = {
    "web_frontend":    ["react component library", "vue framework", "css design system", "frontend ui"],
    "web_backend":     ["rest api framework", "graphql server", "microservices backend", "authentication server"],
    "mobile":          ["react native app", "flutter mobile", "ios swift", "android kotlin"],
    "devtools":        ["cli tool developer", "linter formatter", "build tool bundler", "code generator scaffold"],
    "data_science":    ["machine learning python", "deep learning pytorch", "data analysis pandas", "nlp transformer"],
    "infrastructure":  ["kubernetes operator", "terraform provider", "ci cd pipeline", "docker compose"],
    "security":        ["cryptography library", "penetration testing", "vulnerability scanner", "authentication security"],
    "game_dev":        ["game engine", "opengl rendering", "unity plugin", "godot game"],
    "systems":         ["operating system kernel", "compiler runtime", "embedded firmware", "memory allocator"],
    "open_source_lib": ["utility library sdk", "api client wrapper", "framework plugin integration", "helper utility"],
}


def _headers(token: str | None = None) -> dict:
    return {
        "Authorization": f"Bearer {token or GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """GET with automatic retry on 403/429 rate-limit responses."""
    for attempt in range(3):
        resp = await client.get(url, headers=_headers(), **kwargs)
        if resp.status_code in (403, 429):
            reset = resp.headers.get("x-ratelimit-reset")
            wait = 60
            if reset:
                wait = max(int(reset) - int(datetime.utcnow().timestamp()), 1)
                wait = min(wait, 300)  # cap at 5 min
            log.warning("Rate limited (attempt %d). Waiting %ds…", attempt + 1, wait)
            await asyncio.sleep(wait)
            continue
        return resp
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def search_repositories(
    query: str,
    min_stars: int = 50,
    per_page: int = 100,
    page: int = 1,
) -> list[dict]:
    """Search GitHub repos. Returns a list of basic repo dicts."""
    q = f"{query} stars:>={min_stars}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _get(
            client,
            f"{GITHUB_API}/search/repositories",
            params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page, "page": page},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

    return [
        {
            "github_id": r["id"],
            "full_name": r["full_name"],
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r["stargazers_count"],
            "forks": r["forks_count"],
            "watchers": r["watchers_count"],
            "open_issues": r["open_issues_count"],
            "topics": r.get("topics", []),
            "size": r.get("size", 0),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in items
    ]


async def get_repository_details(full_name: str) -> dict:
    """
    Fetch full repo details including README, contributor count, and commit count.
    Makes 4 API calls: repo info, readme, contributors, commits.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Core repo data
        repo_resp = await _get(client, f"{GITHUB_API}/repos/{full_name}")
        repo_resp.raise_for_status()
        repo = repo_resp.json()

        await asyncio.sleep(0.25)

        # 2. README (base64-encoded)
        readme_text = ""
        readme_resp = await _get(client, f"{GITHUB_API}/repos/{full_name}/readme")
        if readme_resp.status_code == 200:
            raw = readme_resp.json().get("content", "")
            try:
                readme_text = base64.b64decode(raw).decode("utf-8", errors="ignore")[:2000]
            except Exception:
                readme_text = ""

        await asyncio.sleep(0.25)

        # 3. Contributor count via x-total-count header
        contrib_resp = await _get(
            client,
            f"{GITHUB_API}/repos/{full_name}/contributors",
            params={"per_page": 1, "anon": "true"},
        )
        contributor_count = 0
        if contrib_resp.status_code == 200:
            try:
                contributor_count = int(contrib_resp.headers.get("x-total-count", 0))
            except (ValueError, TypeError):
                contributor_count = len(contrib_resp.json())

        await asyncio.sleep(0.25)

        # 4. Commit count via x-total-count header
        commit_resp = await _get(
            client,
            f"{GITHUB_API}/repos/{full_name}/commits",
            params={"per_page": 1},
        )
        commit_count = 0
        if commit_resp.status_code == 200:
            try:
                commit_count = int(commit_resp.headers.get("x-total-count", 0))
            except (ValueError, TypeError):
                commit_count = 0

    return {
        "github_id": repo["id"],
        "full_name": repo["full_name"],
        "description": repo.get("description"),
        "readme": readme_text,
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "watchers": repo["watchers_count"],
        "open_issues": repo["open_issues_count"],
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "size": repo.get("size", 0),
        "created_at": repo["created_at"],
        "updated_at": repo["updated_at"],
        "contributor_count": contributor_count,
        "commit_count": commit_count,
    }


async def get_developer_stats(username: str) -> dict:
    """
    Fetch GitHub user profile and aggregate stats across their public repos.
    Returns combined dict with top_languages and total_stars.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        user_resp = await _get(client, f"{GITHUB_API}/users/{username}")
        user_resp.raise_for_status()
        user = user_resp.json()

        await asyncio.sleep(0.5)

        repos_resp = await _get(
            client,
            f"{GITHUB_API}/users/{username}/repos",
            params={"per_page": 100, "sort": "stars", "type": "owner"},
        )
        repos_resp.raise_for_status()
        repos = repos_resp.json()

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    lang_counts: dict[str, int] = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_languages = [
        lang for lang, _ in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    ]

    return {
        "github_username": user["login"],
        "display_name": user.get("name"),
        "avatar_url": user.get("avatar_url"),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "total_stars": total_stars,
        "top_languages": top_languages,
    }


async def get_user_repos(username: str) -> list[dict]:
    """
    Return the user's own non-fork public repos with language, topics and stars.
    Used by the recommendations engine to classify the user's areas of expertise.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _get(
            client,
            f"{GITHUB_API}/users/{username}/repos",
            params={"per_page": 100, "sort": "stars", "type": "owner"},
        )
        resp.raise_for_status()
        repos = resp.json()

    return [
        {
            "full_name": r["full_name"],
            "name": r["name"],
            "description": r.get("description") or "",
            "language": r.get("language"),
            "topics": r.get("topics", []),
            "stars": r.get("stargazers_count", 0),
            "readme": "",  # List endpoint doesn't include README
        }
        for r in repos
        if not r.get("fork", False)  # Ignore forks — classify original work only
    ]


async def fetch_github_user(token: str) -> dict:
    """Fetch the authenticated user's profile using their OAuth token."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GITHUB_API}/user",
            headers=_headers(token),
        )
        resp.raise_for_status()
        return resp.json()


async def scrape_and_store(
    genres_to_scrape: list[str],
    repos_per_genre: int = 100,
) -> None:
    """
    For each genre, search GitHub with relevant keywords, fetch full details,
    classify via Gemini, and persist to the database.
    """
    # Lazy imports to avoid circular dependencies at module level
    from database import AsyncSessionLocal, Repository, RepoClassification
    from classifier import classify_repository as classify_repo

    per_query = max(1, repos_per_genre // 4)  # spread across ~4 queries per genre

    async with AsyncSessionLocal() as db:
        for genre in genres_to_scrape:
            queries = GENRE_QUERIES.get(genre, [genre])
            collected: dict[int, dict] = {}  # github_id → basic data, deduped

            log.info("[%s] Searching GitHub…", genre)

            for query in queries:
                if len(collected) >= repos_per_genre:
                    break
                try:
                    results = await search_repositories(query, per_page=min(per_query, 100))
                    for r in results:
                        collected[r["github_id"]] = r
                    log.info("[%s] query=%r  found=%d  total_so_far=%d", genre, query, len(results), len(collected))
                except Exception as exc:
                    log.error("[%s] search failed for %r: %s", genre, query, exc)
                await asyncio.sleep(1)

            repos_to_process = list(collected.values())[:repos_per_genre]
            log.info("[%s] Processing %d repos…", genre, len(repos_to_process))

            for i, basic in enumerate(repos_to_process, 1):
                full_name = basic["full_name"]
                github_id = basic["github_id"]

                # Skip if already in DB
                existing = await db.execute(
                    select(Repository).where(Repository.github_id == github_id)
                )
                if existing.scalar_one_or_none():
                    log.info("[%s] %d/%d  skip (cached)  %s", genre, i, len(repos_to_process), full_name)
                    continue

                try:
                    details = await get_repository_details(full_name)
                except Exception as exc:
                    log.error("[%s] %d/%d  details failed  %s: %s", genre, i, len(repos_to_process), full_name, exc)
                    await asyncio.sleep(1)
                    continue

                # Persist repository row
                repo_row = Repository(
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
                db.add(repo_row)
                await db.flush()  # get repo_row.id before classification

                # Classify via Gemini
                try:
                    classification = await classify_repo(details)
                    if not classification:
                        print(f"[CLASSIFIER] WARNING: classify_repository returned None/empty for {full_name}")
                    else:
                        print(f"[CLASSIFIER] {full_name} → genre={classification['genre']}  tags={classification['tags']}  confidence={classification.get('confidence')}")
                        clf_row = RepoClassification(
                            repo_id=repo_row.id,
                            genre=classification["genre"],
                            tags=classification["tags"],
                            confidence=classification.get("confidence"),
                        )
                        db.add(clf_row)
                        await db.flush()
                        print(f"[CLASSIFIER] Saved RepoClassification id={clf_row.id} for repo_id={repo_row.id}")
                except Exception as exc:
                    print(f"[CLASSIFIER] ERROR: classification failed for {full_name}: {exc}")
                    log.error("[%s] classification failed for %s: %s", genre, full_name, exc)

                await db.commit()
                log.info("[%s] %d/%d  stored  %s", genre, i, len(repos_to_process), full_name)
                await asyncio.sleep(1)

        log.info("scrape_and_store complete.")
