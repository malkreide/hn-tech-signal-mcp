"""Tests for hn-tech-signal-mcp server.

Run unit tests (no network):
    PYTHONPATH=src pytest tests/ -m "not live"

Run live integration tests:
    PYTHONPATH=src pytest tests/ -m "live"
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Unit tests – no network calls
# ---------------------------------------------------------------------------

def test_imports():
    """Server module imports cleanly."""
    from hn_tech_signal_mcp.server import mcp, main
    assert mcp is not None
    assert callable(main)


def test_version():
    """Package version is defined."""
    import hn_tech_signal_mcp
    assert hn_tech_signal_mcp.__version__ == "0.1.0"


def test_constants():
    """Key constants are defined."""
    from hn_tech_signal_mcp.server import (
        HN_BASE_URL,
        ARXIV_BASE_URL,
        LOBSTERS_BASE_URL,
        GITHUB_BASE_URL,
        ARXIV_AI_CATEGORIES,
    )
    assert "hacker-news.firebaseio.com" in HN_BASE_URL
    assert "arxiv.org" in ARXIV_BASE_URL
    assert "lobste.rs" in LOBSTERS_BASE_URL
    assert "github.com" in GITHUB_BASE_URL
    assert "cs.AI" in ARXIV_AI_CATEGORIES
    assert "cs.LG" in ARXIV_AI_CATEGORIES
    assert "cs.CL" in ARXIV_AI_CATEGORIES


def test_ts_to_iso():
    """Timestamp conversion works."""
    from hn_tech_signal_mcp.server import _ts_to_iso
    # Real-world timestamp → formatted date
    result = _ts_to_iso(1700000000)
    assert "2023" in result
    assert "UTC" in result
    # None and 0 (falsy) → "unknown"
    assert _ts_to_iso(None) == "unknown"
    assert _ts_to_iso(0) == "unknown"


def test_handle_error_timeout():
    """Error handler formats timeout errors."""
    import httpx
    from hn_tech_signal_mcp.server import _handle_error
    e = httpx.TimeoutException("timed out")
    result = _handle_error(e)
    assert "timed out" in result.lower() or "timeout" in result.lower()


def test_handle_error_rate_limit():
    """Error handler advises on rate limits."""
    import httpx
    from hn_tech_signal_mcp.server import _handle_error
    mock_response = MagicMock()
    mock_response.status_code = 429
    e = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=mock_response)
    result = _handle_error(e)
    assert "rate limit" in result.lower() or "429" in result


def test_format_hn_story():
    """HN story formatter produces expected fields."""
    from hn_tech_signal_mcp.server import _format_hn_story
    story = {
        "id": 12345,
        "title": "Test Story",
        "url": "https://example.com",
        "score": 42,
        "descendants": 7,
        "by": "testuser",
        "time": 1700000000,
    }
    result = _format_hn_story(story)
    assert result["id"] == 12345
    assert result["title"] == "Test Story"
    assert result["score"] == 42
    assert result["comments"] == 7
    assert "ycombinator.com" in result["hn_link"]


def test_cache_set_and_get():
    """Cache stores and retrieves values within TTL."""
    from hn_tech_signal_mcp.server import _cache_get, _cache_set
    _cache_set("test_key_unit", "test_value")
    result = _cache_get("test_key_unit", "hn_top")
    assert result == "test_value"


def test_cache_miss():
    """Cache returns None for unknown key."""
    from hn_tech_signal_mcp.server import _cache_get
    result = _cache_get("nonexistent_key_xyz_123", "hn_top")
    assert result is None


# Pydantic input validation tests

def test_hn_top_stories_input_defaults():
    from hn_tech_signal_mcp.server import HnTopStoriesInput
    m = HnTopStoriesInput()
    assert m.feed == "top"
    assert m.limit == 10
    assert m.min_score == 0


def test_hn_top_stories_input_invalid_feed():
    from hn_tech_signal_mcp.server import HnTopStoriesInput
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HnTopStoriesInput(feed="invalid")


def test_arxiv_latest_input_invalid_category():
    from hn_tech_signal_mcp.server import ArxivLatestInput
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ArxivLatestInput(categories=["not.a.cat"])


def test_arxiv_latest_input_valid():
    from hn_tech_signal_mcp.server import ArxivLatestInput
    m = ArxivLatestInput(categories=["cs.AI", "cs.CL"])
    assert "cs.AI" in m.categories


def test_github_input_invalid_sort():
    from hn_tech_signal_mcp.server import GithubTrendingAiInput
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GithubTrendingAiInput(sort="popularity")


def test_hn_search_input_empty_query():
    from hn_tech_signal_mcp.server import HnSearchInput
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HnSearchInput(query="")


def test_seven_tools_registered():
    """All 7 tools are registered on the server."""
    from hn_tech_signal_mcp.server import mcp
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected = {
        "hn_top_stories",
        "hn_search",
        "arxiv_latest",
        "arxiv_search",
        "lobsters_hot",
        "github_trending_ai",
        "tech_signal_digest",
    }
    assert expected == set(tool_names), f"Unexpected tools: {set(tool_names) ^ expected}"


# ---------------------------------------------------------------------------
# Live integration tests – require network
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_top_stories():
    """Live: fetch HN top stories."""
    from hn_tech_signal_mcp.server import hn_top_stories, HnTopStoriesInput
    result = await hn_top_stories(HnTopStoriesInput(limit=3))
    data = json.loads(result)
    assert data["count"] > 0
    assert len(data["stories"]) > 0
    assert data["stories"][0]["title"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_search():
    """Live: search HN for AI content."""
    from hn_tech_signal_mcp.server import hn_search, HnSearchInput
    result = await hn_search(HnSearchInput(query="large language models", limit=3, days_back=30))
    data = json.loads(result)
    assert "hits" in data


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_arxiv_latest():
    """Live: fetch latest arXiv cs.AI papers."""
    from hn_tech_signal_mcp.server import arxiv_latest, ArxivLatestInput
    result = await arxiv_latest(ArxivLatestInput(categories=["cs.AI"], limit=3))
    data = json.loads(result)
    assert data["total_papers"] > 0
    papers = data["by_category"]["cs.AI"]
    assert len(papers) > 0
    assert papers[0]["title"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_arxiv_search():
    """Live: search arXiv for LLM papers."""
    from hn_tech_signal_mcp.server import arxiv_search, ArxivSearchInput
    result = await arxiv_search(ArxivSearchInput(query="LLM agents", limit=3))
    data = json.loads(result)
    assert data["count"] > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_lobsters_hot():
    """Live: fetch Lobste.rs hottest stories."""
    from hn_tech_signal_mcp.server import lobsters_hot, LobstersHotInput
    result = await lobsters_hot(LobstersHotInput(limit=5))
    data = json.loads(result)
    assert data["count"] > 0
    assert data["stories"][0]["title"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_github_trending():
    """Live: fetch trending LLM repos on GitHub."""
    from hn_tech_signal_mcp.server import github_trending_ai, GithubTrendingAiInput
    result = await github_trending_ai(GithubTrendingAiInput(topic="llm", limit=3, min_stars=100))
    data = json.loads(result)
    assert data["count"] > 0
    assert data["repos"][0]["stars"] >= 100


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_digest():
    """Live: generate tech signal digest."""
    from hn_tech_signal_mcp.server import tech_signal_digest, TechSignalDigestInput
    result = await tech_signal_digest(TechSignalDigestInput(
        focus=None, hn_limit=3, arxiv_limit=3, lobsters_limit=3, github_limit=3
    ))
    data = json.loads(result)
    assert "sources" in data
    assert "hn" in data["sources"]
    assert "arxiv" in data["sources"]
    assert "lobsters" in data["sources"]
    assert "github" in data["sources"]
