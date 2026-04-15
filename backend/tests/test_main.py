"""
Tests for main.py — FastAPI endpoint integration tests using httpx.AsyncClient.
All external dependencies (DB, GitHub API, classifier) are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_repo_row(full_name="facebook/react", stars=220000, forks=45000,
                   open_issues=900, watchers=220000, language="JavaScript"):
    """Build a mock Repository ORM object."""
    row = MagicMock()
    row.id = 1
    row.github_id = 10270250
    row.full_name = full_name
    row.description = "A UI library"
    row.readme = "# React"
    row.language = language
    row.stars = stars
    row.forks = forks
    row.watchers = watchers
    row.open_issues = open_issues
    row.topics = ["react"]
    row.size = 300000
    row.contributor_count = 1800
    row.commit_count = 17000
    row.created_at = "2013-05-24T16:15:54"
    row.updated_at = "2024-01-01T00:00:00"
    row.scraped_at = "2024-01-15T00:00:00"
    return row


def _mock_classification(genre="web_frontend", tags=None, confidence=0.95):
    """Build a mock RepoClassification ORM object."""
    clf = MagicMock()
    clf.genre = genre
    clf.tags = tags or ["react", "javascript"]
    clf.confidence = confidence
    return clf


def _mock_session():
    """Create a fresh AsyncMock session."""
    return AsyncMock()


# ── Health ───────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── Stats endpoints ──────────────────────────────────────────────────────────

class TestStatsRepo:
    @pytest.mark.asyncio
    async def test_repo_found_in_db(self):
        """When a repo exists in the DB, should return it directly."""
        from main import app
        from database import get_db

        repo_row = _mock_repo_row()
        clf = _mock_classification()
        repo_row.classification = clf

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = repo_row

        mock_agg_row = MagicMock()
        mock_agg_row.avg_stars = 50000
        mock_agg_row.avg_forks = 10000
        mock_agg_row.avg_issues = 300
        mock_agg_row.total_in_genre = 25

        mock_agg_result = MagicMock()
        mock_agg_result.one.return_value = mock_agg_row

        session = _mock_session()
        session.execute = AsyncMock(side_effect=[mock_result, mock_agg_result])

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/stats/repo/facebook/react")

            assert resp.status_code == 200
            data = resp.json()
            assert data["full_name"] == "facebook/react"
            assert data["stars"] == 220000
            assert data["genre"] == "web_frontend"
            assert "genre_comparison" in data
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestStatsRepoNotFound:
    @pytest.mark.asyncio
    async def test_repo_not_in_db_fetches_from_github(self):
        """When a repo is not cached, it should call _fetch_classify_store."""
        from main import app
        from database import get_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not in DB

        repo_row = _mock_repo_row()
        clf = _mock_classification()
        repo_row.classification = clf

        session = _mock_session()
        session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with patch("main._fetch_classify_store", new_callable=AsyncMock,
                        return_value=(repo_row, clf)):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/stats/repo/facebook/react")

            assert resp.status_code == 200
            assert resp.json()["full_name"] == "facebook/react"
        finally:
            app.dependency_overrides.pop(get_db, None)


# ── Search endpoint ──────────────────────────────────────────────────────────

class TestSearchRepos:
    @pytest.mark.asyncio
    async def test_search_requires_min_length(self):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/repos/search", params={"q": "a"})

        assert resp.status_code == 422  # validation error — min_length=2

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        from main import app
        from database import get_db

        repo_row = _mock_repo_row()
        clf = _mock_classification()
        repo_row.classification = clf

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [repo_row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        session = _mock_session()
        session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/repos/search", params={"q": "react"})

            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["full_name"] == "facebook/react"
        finally:
            app.dependency_overrides.pop(get_db, None)


# ── Similar repos endpoint ───────────────────────────────────────────────────

class TestSimilarRepos:
    @pytest.mark.asyncio
    async def test_similar_repos_not_in_db_returns_error(self):
        """When the repo is not cached, the endpoint tries to fetch it.
        If that fails, it returns 502."""
        from main import app
        from database import get_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # repo not in DB

        session = _mock_session()
        session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with patch("main._fetch_classify_store", new_callable=AsyncMock,
                        side_effect=Exception("Not found on GitHub")):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/repos/similar/unknown/repo")

            assert resp.status_code == 502
        finally:
            app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_similar_repos_no_genre_returns_404(self):
        """When the repo exists but has no genre, returns 404."""
        from main import app
        from database import get_db

        repo_row = _mock_repo_row(full_name="unknown/repo")
        clf = _mock_classification(genre="unknown")
        repo_row.classification = clf

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = repo_row

        session = _mock_session()
        session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/repos/similar/unknown/repo")

            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)
