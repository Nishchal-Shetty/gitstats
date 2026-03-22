import asyncio
import json
import logging
import os

import anthropic
from dotenv import load_dotenv

from genres import ALL_GENRES, ALL_TAGS, GENRE_DESCRIPTIONS

load_dotenv()

log = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_FALLBACK = {"genre": "unknown", "tags": [], "confidence": 0.0}

_GENRE_LIST = "\n".join(
    f'  "{g}": {GENRE_DESCRIPTIONS[g]}' for g in ALL_GENRES
)
_TAG_LIST = ", ".join(ALL_TAGS)


def _build_prompt(repo: dict) -> str:
    name        = repo.get("full_name") or repo.get("name", "unknown")
    description = repo.get("description") or "none"
    language    = repo.get("language") or "unknown"
    topics      = ", ".join(repo.get("topics", [])) or "none"
    readme      = (repo.get("readme") or "")[:2000]

    return f"""You are an expert software project classifier. Classify the GitHub repository below.

## Repository
- Name: {name}
- Primary language: {language}
- Topics: {topics}
- Description: {description}
- README excerpt:
{readme}

## Task
1. Choose the SINGLE best genre from this list (use the exact key):
{_GENRE_LIST}

2. Choose 3–7 tags from this list that best describe the project:
{_TAG_LIST}

3. Give a confidence score between 0.0 and 1.0 reflecting how certain you are.
   Use 0.9+ only when the project clearly fits one genre.
   Use 0.5–0.7 for projects that overlap multiple genres.

## Response format
Respond with ONLY valid JSON — no markdown, no explanation:
{{
  "genre": "<exact genre key>",
  "tags": ["tag1", "tag2", ...],
  "confidence": <float 0.0–1.0>
}}"""


def _parse_response(text: str) -> dict:
    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    data = json.loads(text)

    genre = data.get("genre", "unknown")
    if genre not in ALL_GENRES:
        log.warning("Claude returned unknown genre %r, falling back to 'unknown'", genre)
        genre = "unknown"

    tags = [t for t in data.get("tags", []) if t in ALL_TAGS][:7]

    try:
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    return {"genre": genre, "tags": tags, "confidence": confidence}


async def classify_repository(repo_data: dict) -> dict:
    """
    Classify a single repository using Claude Haiku.

    Args:
        repo_data: dict with keys: name/full_name, description, readme,
                   language, topics.

    Returns:
        dict with keys: genre (str), tags (list[str]), confidence (float).
        Falls back to {"genre": "unknown", "tags": [], "confidence": 0.0}
        on any error.
    """
    prompt = _build_prompt(repo_data)

    for attempt in range(3):
        try:
            message = await _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return _parse_response(message.content[0].text)
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            log.warning(
                "classify_repository: rate limited (attempt %d), waiting %ds…",
                attempt + 1, wait,
            )
            await asyncio.sleep(wait)
        except json.JSONDecodeError as exc:
            log.error(
                "classify_repository: JSON parse error for %r: %s",
                repo_data.get("full_name", "?"), exc,
            )
            break
        except Exception as exc:
            log.error(
                "classify_repository: Claude error for %r: %s",
                repo_data.get("full_name", "?"), exc,
            )
            break

    return _FALLBACK.copy()


async def batch_classify(repos: list[dict]) -> list[dict]:
    """
    Classify a list of repositories one by one with a 2 second delay between calls.

    Args:
        repos: list of repo dicts (same shape as classify_repository input).

    Returns:
        list of classification dicts in the same order as the input.
    """
    results = []
    total = len(repos)

    for i, repo in enumerate(repos, 1):
        name = repo.get("full_name") or repo.get("name", "?")
        log.info("batch_classify: %d/%d  %s", i, total, name)

        result = await classify_repository(repo)
        results.append(result)

        if i < total:
            await asyncio.sleep(2)

    return results
