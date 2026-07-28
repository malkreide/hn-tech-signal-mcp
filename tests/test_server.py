"""Tests for hn-tech-signal-mcp server.

Run unit tests (no network):
    PYTHONPATH=src pytest tests/ -m "not live"

Run live integration tests:
    PYTHONPATH=src pytest tests/ -m "live"
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest
import respx

HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"


@pytest.fixture(autouse=True)
def _isolate_server_state():
    """Each test starts with an empty cache and no shared HTTP client.

    The client is a module-level singleton; leaving one behind would carry a
    respx-patched transport into the next test.
    """
    from hn_tech_signal_mcp import server as srv

    srv._cache.clear()
    srv._client = None
    yield
    srv._cache.clear()
    srv._client = None


@pytest.fixture
def no_backoff(monkeypatch):
    """Collapse the retry backoff so retry tests run instantly."""
    from hn_tech_signal_mcp import server as srv

    monkeypatch.setattr(srv, "RETRY_BASE_DELAY", 0.0)


def _mock_items(items: dict[int, dict | None]) -> None:
    """Register respx routes for HN item IDs. None means the API's null body."""
    for item_id, payload in items.items():
        respx.get(HN_ITEM.format(item_id)).mock(return_value=httpx.Response(200, json=payload))


def _comment(cid: int, kids: list[int] | None = None, **extra) -> dict:
    return {
        "id": cid,
        "type": "comment",
        "by": f"user{cid}",
        "time": 1700000000,
        "text": f"comment {cid}",
        "kids": kids or [],
        **extra,
    }


# ---------------------------------------------------------------------------
# Unit tests – no network calls
# ---------------------------------------------------------------------------


def test_imports():
    """Server module imports cleanly."""
    from hn_tech_signal_mcp.server import main, server

    assert server is not None
    assert callable(main)


def test_version():
    """Package version is defined."""
    import hn_tech_signal_mcp

    assert hn_tech_signal_mcp.__version__ == "0.3.0"


def test_version_matches_pyproject():
    """pyproject and __init__ must agree — a mismatch breaks the PyPI publish."""
    import re
    from pathlib import Path

    import hn_tech_signal_mcp

    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert declared is not None
    assert declared.group(1) == hn_tech_signal_mcp.__version__


def test_constants():
    """Key constants are defined."""
    from hn_tech_signal_mcp.server import (
        ARXIV_AI_CATEGORIES,
        ARXIV_BASE_URL,
        GITHUB_BASE_URL,
        HN_BASE_URL,
        LOBSTERS_BASE_URL,
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
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import HnTopStoriesInput

    with pytest.raises(ValidationError):
        HnTopStoriesInput(feed="invalid")


def test_arxiv_latest_input_invalid_category():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import ArxivLatestInput

    with pytest.raises(ValidationError):
        ArxivLatestInput(categories=["not.a.cat"])


def test_arxiv_latest_input_valid():
    from hn_tech_signal_mcp.server import ArxivLatestInput

    m = ArxivLatestInput(categories=["cs.AI", "cs.CL"])
    assert "cs.AI" in m.categories


def test_github_input_invalid_sort():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import GithubTrendingAiInput

    with pytest.raises(ValidationError):
        GithubTrendingAiInput(sort="popularity")


def test_hn_search_input_empty_query():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import HnSearchInput

    with pytest.raises(ValidationError):
        HnSearchInput(query="")


# ---------------------------------------------------------------------------
# SEC-004 regression: arxiv_search.category must be whitelisted
# ---------------------------------------------------------------------------


def test_arxiv_search_input_invalid_category():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import ArxivSearchInput

    with pytest.raises(ValidationError):
        ArxivSearchInput(query="LLM", category="not.a.cat")


def test_arxiv_search_input_valid_category():
    from hn_tech_signal_mcp.server import ArxivSearchInput

    m = ArxivSearchInput(query="LLM", category="cs.AI")
    assert m.category == "cs.AI"


def test_arxiv_search_input_empty_category_is_none():
    """Empty string should normalize to None for backwards compatibility."""
    from hn_tech_signal_mcp.server import ArxivSearchInput

    m = ArxivSearchInput(query="LLM", category="")
    assert m.category is None


# ---------------------------------------------------------------------------
# SCALE-001 regression: cache is LRU-bounded
# ---------------------------------------------------------------------------


def test_cache_evicts_oldest_when_full():
    from hn_tech_signal_mcp import server

    server._cache.clear()
    for i in range(server._CACHE_MAX_ENTRIES + 50):
        server._cache_set(f"k{i}", i)
    assert len(server._cache) == server._CACHE_MAX_ENTRIES
    assert "k0" not in server._cache
    assert f"k{server._CACHE_MAX_ENTRIES + 49}" in server._cache
    server._cache.clear()


# ---------------------------------------------------------------------------
# SDK-002 regression: server symbol exported, mcp removed
# ---------------------------------------------------------------------------


def test_server_symbol_replaces_mcp():
    from hn_tech_signal_mcp import server as srv

    assert hasattr(srv, "server")
    assert not hasattr(srv, "mcp")


# ---------------------------------------------------------------------------
# SDK-001 regression: no usage of deprecated datetime.utcnow()
# ---------------------------------------------------------------------------


def test_no_datetime_utcnow_in_source():
    """datetime.utcnow() is deprecated in Python 3.12+; ensure it's gone."""
    from pathlib import Path

    src = Path(__file__).parent.parent / "src" / "hn_tech_signal_mcp" / "server.py"
    assert "datetime.utcnow" not in src.read_text(), "datetime.utcnow() reintroduced"


def test_now_iso_is_timezone_aware():
    from hn_tech_signal_mcp.server import _now_iso

    s = _now_iso()
    assert s.endswith(" UTC")
    assert len(s) == len("YYYY-MM-DD HH:MM UTC")


# ---------------------------------------------------------------------------
# SEC-003 regression: XML parsing uses defusedxml
# ---------------------------------------------------------------------------


def test_xml_parser_is_defused():
    """arXiv XML must be parsed with defusedxml, not stdlib xml.etree."""
    from hn_tech_signal_mcp import server

    assert server._DefusedET.__name__.startswith("defusedxml"), (
        f"Expected defusedxml, got {server._DefusedET.__name__}"
    )


# ---------------------------------------------------------------------------
# OBS-001 regression: errors are logged
# ---------------------------------------------------------------------------


def test_handle_error_logs_warning(caplog):
    import logging

    import httpx

    from hn_tech_signal_mcp.server import _handle_error

    caplog.set_level(logging.WARNING, logger="hn-tech-signal-mcp")
    _handle_error(httpx.TimeoutException("test timeout"), source="UnitTest")
    assert any("UnitTest" in r.message and "TimeoutException" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# SEC-001 regression: GITHUB_TOKEN must only be sent to api.github.com
# ---------------------------------------------------------------------------


def test_github_token_only_sent_to_github(monkeypatch):
    """Bearer header must only attach to github.com URLs."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_secret")
    from hn_tech_signal_mcp.server import GITHUB_BASE_URL, _headers_for

    for foreign in (
        "https://hacker-news.firebaseio.com/v0/topstories.json",
        "https://hn.algolia.com/api/v1/search",
        "https://export.arxiv.org/api/query",
        "https://lobste.rs/hottest.json",
    ):
        assert "Authorization" not in _headers_for(foreign), foreign

    gh = _headers_for(f"{GITHUB_BASE_URL}/search/repositories")
    assert gh["Authorization"] == "Bearer ghp_test_secret"


def test_no_auth_header_without_token(monkeypatch):
    """Without GITHUB_TOKEN no Authorization header anywhere."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from hn_tech_signal_mcp.server import GITHUB_BASE_URL, _headers_for

    assert "Authorization" not in _headers_for(f"{GITHUB_BASE_URL}/search/repositories")
    assert "Authorization" not in _headers_for("https://export.arxiv.org/api/query")


# ---------------------------------------------------------------------------
# SEC-002 regression: streamable_http refuses public bind without bearer
# ---------------------------------------------------------------------------


def test_http_default_binds_loopback(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)
    from hn_tech_signal_mcp.server import _resolve_http_bind

    host, port = _resolve_http_bind()
    assert host == "127.0.0.1"
    assert port == 8000


def test_http_refuses_public_bind_without_bearer(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.delenv("MCP_BEARER_TOKEN", raising=False)
    from hn_tech_signal_mcp.server import _resolve_http_bind

    with pytest.raises(RuntimeError, match="MCP_BEARER_TOKEN"):
        _resolve_http_bind()


def test_http_allows_public_bind_with_bearer(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_BEARER_TOKEN", "secret-xyz")
    from hn_tech_signal_mcp.server import _resolve_http_bind

    host, _ = _resolve_http_bind()
    assert host == "0.0.0.0"


def test_eight_tools_registered():
    """All 8 tools are registered on the server."""
    from hn_tech_signal_mcp.server import server

    tool_names = [t.name for t in server._tool_manager.list_tools()]
    expected = {
        "hn_top_stories",
        "hn_search",
        "hn_discussion",
        "arxiv_latest",
        "arxiv_search",
        "lobsters_hot",
        "github_trending_ai",
        "tech_signal_digest",
    }
    assert expected == set(tool_names), f"Unexpected tools: {set(tool_names) ^ expected}"


# ---------------------------------------------------------------------------
# Resilience: retry with exponential backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_retry_recovers_after_503(no_backoff):
    """A transient 503 is retried and the second attempt's payload is returned."""
    from hn_tech_signal_mcp.server import _get

    route = respx.get("https://example.test/data").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    assert await _get("https://example.test/data") == {"ok": True}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_recovers_after_network_error(no_backoff):
    """Connection errors are retried, not surfaced on the first blip."""
    from hn_tech_signal_mcp.server import _get

    route = respx.get("https://example.test/data").mock(
        side_effect=[
            httpx.ConnectError("connection refused"),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    assert await _get("https://example.test/data") == {"ok": True}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_gives_up_after_all_attempts(no_backoff):
    """Persistent failure raises after exactly RETRY_ATTEMPTS tries."""
    from hn_tech_signal_mcp.server import RETRY_ATTEMPTS, _get

    route = respx.get("https://example.test/data").mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await _get("https://example.test/data")
    assert route.call_count == RETRY_ATTEMPTS


@pytest.mark.asyncio
@respx.mock
async def test_no_retry_on_client_error(no_backoff):
    """4xx other than 429 fail fast — waiting will not fix a bad request."""
    from hn_tech_signal_mcp.server import _get

    route = respx.get("https://example.test/data").mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        await _get("https://example.test/data")
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_timeout_is_retried_then_reported(no_backoff):
    """A full timeout produces a clean error string, not a stack trace."""
    from hn_tech_signal_mcp.server import HnTopStoriesInput, hn_top_stories

    respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    result = await hn_top_stories(HnTopStoriesInput(limit=3))
    assert "timed out" in result.lower()
    assert "HackerNews" in result


def test_rate_limit_is_retryable():
    """429 is transient; other 4xx are not."""
    from hn_tech_signal_mcp.server import _is_retryable

    def status_error(code: int) -> httpx.HTTPStatusError:
        response = httpx.Response(code, request=httpx.Request("GET", "https://example.test"))
        return httpx.HTTPStatusError("err", request=response.request, response=response)

    assert _is_retryable(status_error(429))
    assert _is_retryable(status_error(503))
    assert not _is_retryable(status_error(404))
    assert not _is_retryable(status_error(403))
    assert _is_retryable(httpx.ConnectError("boom"))


# ---------------------------------------------------------------------------
# Resilience: shared connection-pooled client
# ---------------------------------------------------------------------------


def test_shared_client_is_reused():
    """Repeated calls hand back the same pooled client."""
    from hn_tech_signal_mcp.server import _get_client

    assert _get_client() is _get_client()


@pytest.mark.asyncio
async def test_close_shared_client_is_idempotent():
    """Closing twice, or without ever creating a client, must not raise."""
    from hn_tech_signal_mcp import server as srv

    await srv._aclose_shared_client()
    client = srv._get_client()
    await srv._aclose_shared_client()
    await srv._aclose_shared_client()
    assert client.is_closed
    assert srv._client is None


@pytest.mark.asyncio
async def test_client_recreated_after_close():
    """A closed client is replaced rather than reused."""
    from hn_tech_signal_mcp import server as srv

    first = srv._get_client()
    await srv._aclose_shared_client()
    assert srv._get_client() is not first


def test_hn_fanout_is_bounded():
    """The HN item fan-out must stay inside the connection pool."""
    from hn_tech_signal_mcp.server import _POOL_LIMITS, HN_MAX_CONCURRENCY

    assert HN_MAX_CONCURRENCY <= _POOL_LIMITS.max_connections


# ---------------------------------------------------------------------------
# Feeds: ask / show / job
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("feed", ["top", "best", "new", "ask", "show", "job"])
def test_all_six_feeds_accepted(feed):
    from hn_tech_signal_mcp.server import HN_FEEDS, HnTopStoriesInput

    assert HnTopStoriesInput(feed=feed).feed == feed
    assert feed in HN_FEEDS


def test_unknown_feed_rejected():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import HnTopStoriesInput

    with pytest.raises(ValidationError):
        HnTopStoriesInput(feed="askstories")


@pytest.mark.asyncio
@respx.mock
async def test_job_feed_returns_job_items():
    """Regression: jobstories items are type 'job' and were silently dropped."""
    from hn_tech_signal_mcp.server import HnTopStoriesInput, hn_top_stories

    respx.get("https://hacker-news.firebaseio.com/v0/jobstories.json").mock(
        return_value=httpx.Response(200, json=[900, 901])
    )
    _mock_items(
        {
            900: {
                "id": 900,
                "type": "job",
                "title": "Acme (YC W23) is hiring",
                "url": "https://acme.test/jobs",
                "time": 1700000000,
                "score": 1,
            },
            901: {
                "id": 901,
                "type": "job",
                "title": "Beta (YC S24) is hiring",
                "url": "https://beta.test/jobs",
                "time": 1700000000,
                "score": 1,
            },
        }
    )
    data = json.loads(await hn_top_stories(HnTopStoriesInput(feed="job", limit=5)))
    assert data["count"] == 2
    assert data["stories"][0]["type"] == "job"
    # Job posts carry no 'descendants' field at all.
    assert data["stories"][0]["comments"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_ask_feed_falls_back_to_hn_link():
    """Ask HN posts have no 'url' — the discussion itself is the content."""
    from hn_tech_signal_mcp.server import HnTopStoriesInput, hn_top_stories

    respx.get("https://hacker-news.firebaseio.com/v0/askstories.json").mock(
        return_value=httpx.Response(200, json=[800])
    )
    _mock_items(
        {
            800: {
                "id": 800,
                "type": "story",
                "title": "Ask HN: How do you test MCP servers?",
                "text": "I am curious.",
                "score": 23,
                "descendants": 12,
                "time": 1700000000,
            }
        }
    )
    data = json.loads(await hn_top_stories(HnTopStoriesInput(feed="ask", limit=5)))
    assert data["stories"][0]["url"] == "https://news.ycombinator.com/item?id=800"


def test_format_hn_story_tolerates_null_fields():
    """Explicit nulls must not leak into the output as None."""
    from hn_tech_signal_mcp.server import _format_hn_story

    out = _format_hn_story({"id": 7, "type": "job", "title": "T", "url": None, "score": None})
    assert out["url"] == "https://news.ycombinator.com/item?id=7"
    assert out["score"] == 0
    assert out["comments"] == 0


# ---------------------------------------------------------------------------
# hn_discussion: comment text cleaning
# ---------------------------------------------------------------------------


def test_clean_hn_text_converts_paragraphs_and_entities():
    from hn_tech_signal_mcp.server import _clean_hn_text

    raw = "First line.<p>Second &amp; third &#x27;quoted&#x27;.<p><i>emphasis</i>"
    out = _clean_hn_text(raw, 500)
    assert "<p>" not in out and "<i>" not in out
    assert "&amp;" not in out and "&#x27;" not in out
    assert "Second & third 'quoted'." in out
    assert "\n\n" in out


def test_clean_hn_text_strips_links_and_truncates():
    from hn_tech_signal_mcp.server import _clean_hn_text

    raw = '<a href="https://example.test" rel="nofollow">link text</a> ' + "x" * 500
    out = _clean_hn_text(raw, 100)
    assert "href" not in out
    assert "link text" in out
    assert out.endswith("…")
    assert len(out) <= 101


def test_clean_hn_text_handles_missing_body():
    from hn_tech_signal_mcp.server import _clean_hn_text

    assert _clean_hn_text(None, 100) == ""
    assert _clean_hn_text("", 100) == ""


# ---------------------------------------------------------------------------
# hn_discussion: tree traversal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_comment_tree_respects_budget_and_depth():
    from hn_tech_signal_mcp.server import _fetch_comment_tree

    # 4 roots, each with 2 replies, each reply with 2 replies.
    items: dict[int, dict | None] = {}
    roots = [10, 11, 12, 13]
    next_id = 100
    for r in roots:
        kids = [next_id, next_id + 1]
        next_id += 2
        items[r] = _comment(r, kids)
        for k in kids:
            grandkids = [next_id, next_id + 1]
            next_id += 2
            items[k] = _comment(k, grandkids)
            for g in grandkids:
                items[g] = _comment(g)
    _mock_items(items)

    tree, fetched, truncated = await _fetch_comment_tree(
        roots, max_depth=2, max_comments=6, text_chars=200
    )
    assert fetched <= 6
    # Budget split across two levels: roots must not consume all of it.
    assert len(tree) < 6
    assert any(node["replies"] for node in tree)
    assert truncated is True
    # max_depth=2 means no third level anywhere.
    assert all(not reply["replies"] for node in tree for reply in node["replies"])


@pytest.mark.asyncio
@respx.mock
async def test_comment_tree_spreads_budget_across_siblings():
    """One hot sub-thread must not swallow the whole reply budget."""
    from hn_tech_signal_mcp.server import _fetch_comment_tree

    items: dict[int, dict | None] = {
        10: _comment(10, list(range(100, 120))),  # 20 replies
        11: _comment(11, [200]),
        12: _comment(12, [300]),
    }
    for k in list(range(100, 120)) + [200, 300]:
        items[k] = _comment(k)
    _mock_items(items)

    tree, _fetched, _trunc = await _fetch_comment_tree(
        [10, 11, 12], max_depth=2, max_comments=9, text_chars=200
    )
    assert len(tree) == 3
    # The 20-reply thread must not starve its two siblings.
    assert all(node["replies"] for node in tree)


@pytest.mark.asyncio
@respx.mock
async def test_comment_tree_skips_deleted_and_dead():
    from hn_tech_signal_mcp.server import _fetch_comment_tree

    _mock_items(
        {
            10: _comment(10),
            11: {"id": 11, "type": "comment", "deleted": True},
            12: _comment(12, dead=True),
            13: None,  # HN answers unknown IDs with a null body
        }
    )
    tree, fetched, _trunc = await _fetch_comment_tree(
        [10, 11, 12, 13], max_depth=1, max_comments=10, text_chars=200
    )
    assert fetched == 1
    assert [node["id"] for node in tree] == [10]


@pytest.mark.asyncio
@respx.mock
async def test_comment_tree_not_truncated_when_thread_fits():
    from hn_tech_signal_mcp.server import _fetch_comment_tree

    _mock_items({10: _comment(10), 11: _comment(11)})
    tree, fetched, truncated = await _fetch_comment_tree(
        [10, 11], max_depth=3, max_comments=50, text_chars=200
    )
    assert fetched == 2
    assert len(tree) == 2
    assert truncated is False


@pytest.mark.asyncio
@respx.mock
async def test_comment_tree_handles_story_without_comments():
    from hn_tech_signal_mcp.server import _fetch_comment_tree

    tree, fetched, truncated = await _fetch_comment_tree([], 2, 25, 200)
    assert tree == []
    assert fetched == 0
    assert truncated is False


# ---------------------------------------------------------------------------
# hn_discussion: tool behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_hn_discussion_returns_story_and_thread():
    from hn_tech_signal_mcp.server import HnDiscussionInput, hn_discussion

    _mock_items(
        {
            500: {
                "id": 500,
                "type": "story",
                "title": "A story",
                "url": "https://example.test/a",
                "score": 120,
                "descendants": 40,
                "time": 1700000000,
                "by": "author",
                "kids": [501],
            },
            501: _comment(501),
        }
    )
    data = json.loads(await hn_discussion(HnDiscussionInput(story_id=500, max_comments=5)))
    assert data["story"]["title"] == "A story"
    assert data["total_comments"] == 40
    assert data["fetched_comments"] == 1
    assert data["comments"][0]["by"] == "user501"


@pytest.mark.asyncio
@respx.mock
async def test_hn_discussion_reports_missing_item():
    """The API returns HTTP 200 + null for unknown IDs, so this needs handling."""
    from hn_tech_signal_mcp.server import HnDiscussionInput, hn_discussion

    _mock_items({999999999999: None})
    result = await hn_discussion(HnDiscussionInput(story_id=999999999999))
    assert "No item found" in result


@pytest.mark.asyncio
@respx.mock
async def test_hn_discussion_rejects_comment_id():
    """Passing a comment ID should point the caller at the parent story."""
    from hn_tech_signal_mcp.server import HnDiscussionInput, hn_discussion

    _mock_items({600: {"id": 600, "type": "comment", "parent": 599, "text": "hi"}})
    result = await hn_discussion(HnDiscussionInput(story_id=600))
    assert "is a comment" in result
    assert "599" in result


@pytest.mark.asyncio
@respx.mock
async def test_hn_discussion_ask_story_includes_body_text():
    """For Ask HN the story's own text is the question — it must survive."""
    from hn_tech_signal_mcp.server import HnDiscussionInput, hn_discussion

    _mock_items(
        {
            700: {
                "id": 700,
                "type": "story",
                "title": "Ask HN: something?",
                "text": "Body &amp; question<p>second para",
                "time": 1700000000,
                "kids": [],
            }
        }
    )
    data = json.loads(await hn_discussion(HnDiscussionInput(story_id=700)))
    assert "Body & question" in data["story_text"]
    assert "<p>" not in data["story_text"]


# ---------------------------------------------------------------------------
# Lobste.rs: submitter_user changed from object to string upstream
# ---------------------------------------------------------------------------


def test_lobsters_submitter_accepts_both_shapes():
    from hn_tech_signal_mcp.server import _lobsters_submitter

    assert _lobsters_submitter({"submitter_user": "thang"}) == "thang"
    assert _lobsters_submitter({"submitter_user": {"username": "thang"}}) == "thang"
    assert _lobsters_submitter({"submitter_user": None}) == ""
    assert _lobsters_submitter({}) == ""


@pytest.mark.asyncio
@respx.mock
async def test_lobsters_hot_survives_string_submitter():
    """Regression: a bare submitter string used to raise AttributeError."""
    from hn_tech_signal_mcp.server import LobstersHotInput, lobsters_hot

    respx.get("https://lobste.rs/hottest.json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "title": "On AI",
                    "url": "https://example.test/on-ai",
                    "score": 93,
                    "comment_count": 46,
                    "tags": ["ai"],
                    "submitter_user": "thang",
                    "created_at": "2026-07-27T03:52:37.520-05:00",
                    "comments_url": "https://lobste.rs/s/zljfgp",
                }
            ],
        )
    )
    data = json.loads(await lobsters_hot(LobstersHotInput(limit=5)))
    assert data["count"] == 1
    assert data["stories"][0]["submitter"] == "thang"


def test_hn_discussion_input_validation():
    from pydantic import ValidationError

    from hn_tech_signal_mcp.server import HnDiscussionInput

    with pytest.raises(ValidationError):
        HnDiscussionInput(story_id=0)
    with pytest.raises(ValidationError):
        HnDiscussionInput(story_id=1, max_depth=5)
    with pytest.raises(ValidationError):
        HnDiscussionInput(story_id=1, max_comments=101)

    m = HnDiscussionInput(story_id=1)
    assert (m.max_depth, m.max_comments, m.text_chars) == (2, 25, 600)


# ---------------------------------------------------------------------------
# Live integration tests – require network
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_top_stories():
    """Live: fetch HN top stories."""
    from hn_tech_signal_mcp.server import HnTopStoriesInput, hn_top_stories

    result = await hn_top_stories(HnTopStoriesInput(limit=3))
    data = json.loads(result)
    assert data["count"] > 0
    assert len(data["stories"]) > 0
    assert data["stories"][0]["title"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_search():
    """Live: search HN for AI content."""
    from hn_tech_signal_mcp.server import HnSearchInput, hn_search

    result = await hn_search(HnSearchInput(query="large language models", limit=3, days_back=30))
    data = json.loads(result)
    assert "hits" in data


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_arxiv_latest():
    """Live: fetch latest arXiv cs.AI papers."""
    from hn_tech_signal_mcp.server import ArxivLatestInput, arxiv_latest

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
    from hn_tech_signal_mcp.server import ArxivSearchInput, arxiv_search

    result = await arxiv_search(ArxivSearchInput(query="LLM agents", limit=3))
    data = json.loads(result)
    assert data["count"] > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_lobsters_hot():
    """Live: fetch Lobste.rs hottest stories."""
    from hn_tech_signal_mcp.server import LobstersHotInput, lobsters_hot

    result = await lobsters_hot(LobstersHotInput(limit=5))
    data = json.loads(result)
    assert data["count"] > 0
    assert data["stories"][0]["title"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_github_trending():
    """Live: fetch trending LLM repos on GitHub."""
    from hn_tech_signal_mcp.server import GithubTrendingAiInput, github_trending_ai

    result = await github_trending_ai(GithubTrendingAiInput(topic="llm", limit=3, min_stars=100))
    data = json.loads(result)
    assert data["count"] > 0
    assert data["repos"][0]["stars"] >= 100


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_digest():
    """Live: generate tech signal digest."""
    from hn_tech_signal_mcp.server import TechSignalDigestInput, tech_signal_digest

    result = await tech_signal_digest(
        TechSignalDigestInput(
            focus=None, hn_limit=3, arxiv_limit=3, lobsters_limit=3, github_limit=3
        )
    )
    data = json.loads(result)
    assert "sources" in data
    assert "hn" in data["sources"]
    assert "arxiv" in data["sources"]
    assert "lobsters" in data["sources"]
    assert "github" in data["sources"]


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize("feed", ["ask", "show", "job"])
async def test_live_hn_extended_feeds(feed):
    """Live: the three feeds added in 0.3.0 return usable items."""
    from hn_tech_signal_mcp.server import HnTopStoriesInput, hn_top_stories

    data = json.loads(await hn_top_stories(HnTopStoriesInput(feed=feed, limit=3)))
    assert data["count"] > 0, f"{feed} feed came back empty"
    assert data["stories"][0]["title"]
    assert data["stories"][0]["type"] in {"story", "job"}


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_discussion():
    """Live: read a real thread, top story of the moment."""
    from hn_tech_signal_mcp.server import (
        HnDiscussionInput,
        HnTopStoriesInput,
        hn_discussion,
        hn_top_stories,
    )

    top = json.loads(await hn_top_stories(HnTopStoriesInput(feed="top", limit=1)))
    story_id = top["stories"][0]["id"]

    data = json.loads(
        await hn_discussion(HnDiscussionInput(story_id=story_id, max_depth=2, max_comments=10))
    )
    assert data["story"]["id"] == story_id
    assert data["fetched_comments"] <= 10
    for comment in data["comments"]:
        assert "<p>" not in comment["text"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_hn_discussion_missing_item():
    """Live: the API's HTTP 200 + null response for unknown IDs is handled."""
    from hn_tech_signal_mcp.server import HnDiscussionInput, hn_discussion

    result = await hn_discussion(HnDiscussionInput(story_id=999999999999))
    assert "No item found" in result
