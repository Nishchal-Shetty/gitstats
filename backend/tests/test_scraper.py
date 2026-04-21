"""
Tests for scraper.py — rate-limit retry, developer stats, repo details.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from scraper import strip_tz, _headers, get_developer_stats, get_repository_details


# ── strip_tz ─────────────────────────────────────────────────────────────────

class TestStripTz:
    def test_removes_timezone(self):
        from datetime import datetime, timezone
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = strip_tz(dt)
        assert result.tzinfo is None
        assert result.year == 2024

    def test_none_input(self):
        assert strip_tz(None) is None

    def test_naive_datetime_unchanged(self):
        from datetime import datetime
        dt = datetime(2024, 6, 15, 10, 30)
        result = strip_tz(dt)
        assert result == dt


# ── _headers ─────────────────────────────────────────────────────────────────

class TestHeaders:
    def test_uses_provided_token(self):
        h = _headers("my-token")
        assert h["Authorization"] == "Bearer my-token"
        assert "application/vnd.github" in h["Accept"]

    def test_uses_env_token_by_default(self):
        h = _headers()
        assert h["Authorization"].startswith("Bearer ")


# ── get_repository_details ───────────────────────────────────────────────────

class TestGetRepositoryDetails:
    @pytest.mark.asyncio
    async def test_returns_correct_shape(self):
        """Mocks all 4 GitHub API calls and verifies the returned dict."""
        repo_json = {
            "id": 10270250,
            "full_name": "facebook/react",
            "description": "A UI library",
            "stargazers_count": 220000,
            "forks_count": 45000,
            "watchers_count": 220000,
            "open_issues_count": 900,
            "language": "JavaScript",
            "topics": ["react"],
            "size": 300000,
            "created_at": "2013-05-24T16:15:54Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        readme_b64 = base64.b64encode(b"# React\nHello").decode()

        def make_resp(json_data, status=200, headers=None):
            r = MagicMock()
            r.status_code = status
            r.json.return_value = json_data
            r.raise_for_status = MagicMock()
            r.headers = headers or {}
            return r

        call_count = 0

        async def mock_get(client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "/readme" in url:
                return make_resp({"content": readme_b64})
            if "/contributors" in url:
                return make_resp([{}], headers={"x-total-count": "50"})
            if "/commits" in url:
                return make_resp([{}], headers={"x-total-count": "1000"})
            return make_resp(repo_json)

        with patch("scraper._get", side_effect=mock_get):
            with patch("scraper.asyncio.sleep", new_callable=AsyncMock):
                result = await get_repository_details("facebook/react")

        assert result["full_name"] == "facebook/react"
        assert result["stars"] == 220000
        assert result["contributor_count"] == 50
        assert result["commit_count"] == 1000
        assert "React" in result["readme"]
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_handles_missing_readme(self):
        """README endpoint returns 404 — should still return empty string."""
        repo_json = {
            "id": 1,
            "full_name": "a/b",
            "description": None,
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "open_issues_count": 0,
            "language": None,
            "topics": [],
            "size": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        async def mock_get(client, url, **kwargs):
            r = MagicMock()
            r.raise_for_status = MagicMock()
            r.headers = {}
            if "/readme" in url:
                r.status_code = 404
                r.json.return_value = {}
            elif "/contributors" in url:
                r.status_code = 200
                r.json.return_value = []
            elif "/commits" in url:
                r.status_code = 200
                r.json.return_value = []
            else:
                r.status_code = 200
                r.json.return_value = repo_json
            return r

        with patch("scraper._get", side_effect=mock_get):
            with patch("scraper.asyncio.sleep", new_callable=AsyncMock):
                result = await get_repository_details("a/b")

        assert result["readme"] == ""


# ── get_developer_stats ──────────────────────────────────────────────────────

class TestGetDeveloperStats:
    @pytest.mark.asyncio
    async def test_returns_correct_stats(self, sample_github_user):
        repos = [
            {"stargazers_count": 100, "language": "Python"},
            {"stargazers_count": 200, "language": "Python"},
            {"stargazers_count": 50, "language": "JavaScript"},
        ]

        call_count = 0

        async def mock_get(client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.raise_for_status = MagicMock()
            if "/repos" in url:
                r.json.return_value = repos
            else:
                r.json.return_value = sample_github_user
            return r

        with patch("scraper._get", side_effect=mock_get):
            with patch("scraper.asyncio.sleep", new_callable=AsyncMock):
                result = await get_developer_stats("testuser")

        assert result["github_username"] == "testuser"
        assert result["total_stars"] == 350
        assert result["top_languages"][0] == "Python"
        assert len(result["top_languages"]) == 2
