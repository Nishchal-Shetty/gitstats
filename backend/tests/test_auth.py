"""
Tests for auth.py — JWT creation/decoding, OAuth exchange, current-user extraction.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    get_optional_user,
    exchange_code_for_token,
)


# ── JWT ──────────────────────────────────────────────────────────────────────

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token({"sub": "123", "username": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_roundtrip(self):
        payload = {"sub": "42", "username": "roundtrip"}
        token = create_access_token(payload)
        decoded = decode_access_token(token)
        assert decoded["sub"] == "42"
        assert decoded["username"] == "roundtrip"
        assert "exp" in decoded

    def test_decode_invalid_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("totally.invalid.token")
        assert exc_info.value.status_code == 401


# ── get_current_user ─────────────────────────────────────────────────────────

class TestGetCurrentUser:
    def test_returns_payload_for_valid_token(self):
        token = create_access_token({"sub": "99", "username": "me"})
        creds = MagicMock()
        creds.credentials = token
        result = get_current_user(creds)
        assert result["sub"] == "99"

    def test_raises_401_when_no_credentials(self):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        assert exc_info.value.status_code == 401


# ── get_optional_user ────────────────────────────────────────────────────────

class TestGetOptionalUser:
    def test_returns_none_when_no_credentials(self):
        assert get_optional_user(None) is None

    def test_returns_none_for_bad_token(self):
        creds = MagicMock()
        creds.credentials = "bad.token.here"
        assert get_optional_user(creds) is None

    def test_returns_payload_for_good_token(self):
        token = create_access_token({"sub": "7", "username": "opt"})
        creds = MagicMock()
        creds.credentials = token
        result = get_optional_user(creds)
        assert result["sub"] == "7"


# ── exchange_code_for_token ──────────────────────────────────────────────────

class TestExchangeCodeForToken:
    @pytest.mark.asyncio
    async def test_successful_exchange(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "gho_abc123"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client):
            token = await exchange_code_for_token("test-code")
            assert token == "gho_abc123"

    @pytest.mark.asyncio
    async def test_oauth_error_raises_http_exception(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await exchange_code_for_token("bad-code")
            assert exc_info.value.status_code == 400
            assert "expired" in exc_info.value.detail
