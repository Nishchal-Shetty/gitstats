"""
Shared pytest fixtures for backend tests.
"""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars BEFORE any app module imports
os.environ.setdefault("SUPABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GITHUB_TOKEN", "test-gh-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt")


@pytest.fixture
def sample_repo_data():
    """A realistic repo dict as returned by the scraper."""
    return {
        "github_id": 10270250,
        "full_name": "facebook/react",
        "description": "A declarative, efficient, and flexible JavaScript library for building user interfaces.",
        "readme": "# React\nReact is a JavaScript library for building user interfaces.",
        "stars": 220000,
        "forks": 45000,
        "watchers": 220000,
        "open_issues": 900,
        "language": "JavaScript",
        "topics": ["react", "javascript", "ui", "frontend"],
        "size": 300000,
        "created_at": "2013-05-24T16:15:54Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "contributor_count": 1800,
        "commit_count": 17000,
    }


@pytest.fixture
def sample_classification():
    """A realistic classification result."""
    return {
        "genre": "web_frontend",
        "tags": ["react", "javascript", "ui", "frontend", "component-library"],
        "confidence": 0.95,
    }


@pytest.fixture
def sample_github_user():
    """A realistic GitHub user API response."""
    return {
        "id": 12345,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        "email": "test@example.com",
        "followers": 100,
        "following": 50,
        "public_repos": 30,
    }
