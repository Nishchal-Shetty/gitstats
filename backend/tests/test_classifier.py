"""
Tests for classifier.py — prompt building, response parsing, classify_repository.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from classifier import _build_prompt, _parse_response, classify_repository


# ── _build_prompt ────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_includes_repo_name(self, sample_repo_data):
        prompt = _build_prompt(sample_repo_data)
        assert "facebook/react" in prompt

    def test_includes_language(self, sample_repo_data):
        prompt = _build_prompt(sample_repo_data)
        assert "JavaScript" in prompt

    def test_includes_description(self, sample_repo_data):
        prompt = _build_prompt(sample_repo_data)
        assert "declarative" in prompt

    def test_handles_missing_fields(self):
        prompt = _build_prompt({})
        assert "unknown" in prompt
        assert "none" in prompt

    def test_truncates_long_readme(self):
        repo = {"readme": "x" * 5000, "full_name": "a/b"}
        prompt = _build_prompt(repo)
        # Readme in prompt should be capped at 2000 chars
        lines = prompt.split("\n")
        readme_section = [l for l in lines if "xxxx" in l]
        for line in readme_section:
            assert len(line) <= 2001  # up to 2000 + newline


# ── _parse_response ──────────────────────────────────────────────────────────

class TestParseResponse:
    def test_valid_json(self):
        raw = json.dumps({"genre": "web_frontend", "tags": ["react"], "confidence": 0.9})
        result = _parse_response(raw)
        assert result["genre"] == "web_frontend"
        assert result["tags"] == ["react"]
        assert result["confidence"] == 0.9

    def test_strips_markdown_fences(self):
        raw = '```json\n{"genre": "devtools", "tags": ["cli"], "confidence": 0.8}\n```'
        result = _parse_response(raw)
        assert result["genre"] == "devtools"

    def test_unknown_genre_falls_back(self):
        raw = json.dumps({"genre": "not_a_real_genre", "tags": [], "confidence": 0.5})
        result = _parse_response(raw)
        assert result["genre"] == "unknown"

    def test_filters_invalid_tags(self):
        raw = json.dumps({
            "genre": "web_frontend",
            "tags": ["react", "FAKE_TAG", "vue"],
            "confidence": 0.7,
        })
        result = _parse_response(raw)
        assert "FAKE_TAG" not in result["tags"]
        assert "react" in result["tags"]

    def test_clamps_confidence(self):
        raw = json.dumps({"genre": "mobile", "tags": [], "confidence": 5.0})
        result = _parse_response(raw)
        assert result["confidence"] == 1.0

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response("this is not json")

    def test_limits_tags_to_seven(self):
        # Create 10 valid tags
        from genres import ALL_TAGS
        many_tags = ALL_TAGS[:10]
        raw = json.dumps({"genre": "devtools", "tags": many_tags, "confidence": 0.8})
        result = _parse_response(raw)
        assert len(result["tags"]) <= 7


# ── classify_repository ─────────────────────────────────────────────────────

class TestClassifyRepository:
    @pytest.mark.asyncio
    async def test_successful_classification(self, sample_repo_data):
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text=json.dumps({
                "genre": "web_frontend",
                "tags": ["react", "javascript", "ui"],
                "confidence": 0.95,
            }))
        ]

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_message

        with patch("classifier._client", mock_client):
            result = await classify_repository(sample_repo_data)

        assert result["genre"] == "web_frontend"
        assert result["confidence"] == 0.95
        assert "react" in result["tags"]

    @pytest.mark.asyncio
    async def test_returns_fallback_on_error(self, sample_repo_data):
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")

        with patch("classifier._client", mock_client):
            result = await classify_repository(sample_repo_data)

        assert result["genre"] == "unknown"
        assert result["tags"] == []
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_fallback_on_bad_json(self, sample_repo_data):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="NOT JSON AT ALL")]

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_message

        with patch("classifier._client", mock_client):
            result = await classify_repository(sample_repo_data)

        assert result["genre"] == "unknown"
