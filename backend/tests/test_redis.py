import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from main import app
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

# Use pytest_asyncio's specific decorator
@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_cache():
    """
    Initialize an in-memory cache for testing.
    """
    # Clear any existing state
    FastAPICache.init(InMemoryBackend(), prefix="test-gitstats")
    yield
    # No explicit clear() needed for InMemoryBackend usually, 
    # but you can re-init to reset if needed.
    FastAPICache.reset()

@pytest.mark.asyncio
async def test_stats_repo_caching_behavior():
    owner = "fastapi"
    repo_name = "fastapi"
    endpoint = f"/api/stats/repo/{owner}/{repo_name}"

    mock_db = AsyncMock()
    
    # Mock Repository object
    mock_repo = MagicMock()
    mock_repo.full_name = f"{owner}/{repo_name}"
    # Ensure classification is not None to avoid the re-classification logic in main.py
    mock_repo.classification = MagicMock(genre="web-framework", confidence=0.95, tags=["python"])
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_db.execute.return_value = mock_result

    from database import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        # --- First Request ---
        response1 = await ac.get(endpoint)
        assert response1.status_code == 200
        
        # We expect 2 calls: one for the repo lookup, one for genre stats
        assert mock_db.execute.call_count == 2 
        
        # --- Second Request (Should be cached) ---
        response2 = await ac.get(endpoint)
        assert response2.status_code == 200
        
        # Total calls should STAY at 2 if the cache intercepted the request
        assert mock_db.execute.call_count == 2, "Cache was bypassed!"

    app.dependency_overrides.clear()