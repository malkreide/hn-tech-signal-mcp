"""HN Tech Signal MCP Server – 8 Tools for Tech & AI Intelligence.

Aggregates signals from four complementary sources:
  - HackerNews  (community discourse, broad tech)
  - arXiv       (AI/ML research frontier: cs.AI / cs.LG / cs.CL)
  - Lobste.rs   (curated tech signal, higher quality filter)
  - GitHub      (what is actually being built)

No API key required for any source.
Optional: GITHUB_TOKEN for higher GitHub rate limits (5,000 req/h vs 60).

Architecture:
  FRONTIER  →  arXiv API          (cs.AI / cs.LG / cs.CL / cs.CV / stat.ML)
  DISCOURSE →  HackerNews API     (top / best / new / ask / show / job feeds,
                                   plus comment threads via hn_discussion)
               Lobste.rs JSON API (curated tech community)
  PRACTICE  →  GitHub Search API  (trending repos by topic)
  AGGREGATE →  tech_signal_digest (all sources, one call)
"""

import asyncio
import html
import json
import logging
import os
import re
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from xml.etree.ElementTree import Element as _XmlElement

import httpx
from defusedxml import ElementTree as _DefusedET
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger("hn-tech-signal-mcp")


def _now_iso() -> str:
    """Timezone-aware UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1"
ARXIV_BASE_URL = "https://export.arxiv.org/api/query"
LOBSTERS_BASE_URL = "https://lobste.rs"
GITHUB_BASE_URL = "https://api.github.com"

DEFAULT_TIMEOUT = 20.0
ARXIV_AI_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML"]

# HN story feeds. The Firebase API exposes one endpoint per feed following the
# pattern "<feed>stories.json". 'job' is included but yields items of type
# "job", not "story" — see _fetch_hn_stories.
HN_FEEDS = ("top", "best", "new", "ask", "show", "job")

# Retry policy for all upstream HTTP calls: 3 retries after the initial attempt,
# waiting 2s / 4s / 8s. Retried on network errors, 5xx and 429; other 4xx fail
# fast because they will not resolve themselves.
RETRY_ATTEMPTS = 4
RETRY_BASE_DELAY = 2.0

# The HN item endpoint is one request per item, so a single tool call fans out
# to dozens of requests. Bound the concurrency so we neither hammer the upstream
# nor exhaust the connection pool.
HN_MAX_CONCURRENCY = 12

# Connection pool sizing for the shared client. Slightly above the HN fan-out
# limit to leave headroom for the parallel sources in tech_signal_digest.
_POOL_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)

# In-memory TTL cache, LRU-bounded to prevent unbounded growth in long-running HTTP mode.
_CACHE_MAX_ENTRIES = 512
_cache: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
CACHE_TTL: dict[str, int] = {
    "hn_top": 600,
    "hn_search": 300,
    "hn_discussion": 300,
    "arxiv": 1800,
    "lobsters": 900,
    "github": 1800,
    "digest": 600,
}


def _cache_get(key: str, ttl_type: str) -> Optional[Any]:
    if key not in _cache:
        return None
    ts, data = _cache[key]
    if time.time() - ts > CACHE_TTL.get(ttl_type, 600):
        del _cache[key]
        return None
    _cache.move_to_end(key)
    return data


def _cache_set(key: str, data: Any) -> None:
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = (time.time(), data)
    while len(_cache) > _CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Close the shared HTTP client on shutdown so sockets are released cleanly."""
    try:
        yield
    finally:
        await _aclose_shared_client()


server = FastMCP(
    "hn_tech_signal_mcp",
    instructions=(
        "Tech & AI intelligence server aggregating signals from HackerNews, arXiv, "
        "Lobste.rs and GitHub. No API keys required. "
        "Use tech_signal_digest for a full briefing in a single call, "
        "and hn_discussion to read the actual argument thread under a story."
    ),
    lifespan=_lifespan,
)


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

_BASE_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "hn-tech-signal-mcp/0.3.0",
}


def _headers_for(url: str) -> dict[str, str]:
    headers = dict(_BASE_HEADERS)
    if url.startswith(GITHUB_BASE_URL):
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Lazily create the process-wide AsyncClient.

    One client for the whole server, so connections are pooled and reused. The
    previous implementation opened a fresh client per request, which meant a
    full TCP + TLS handshake for every single HN item in a fan-out.
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, limits=_POOL_LIMITS)
    return _client


async def _aclose_shared_client() -> None:
    """Close the shared client. Idempotent; safe to call when never created."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _is_retryable(exc: Exception) -> bool:
    """Network errors and transient server responses are worth another attempt."""
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code < 600
    return False


async def _request_with_retry(url: str, params: Optional[dict] = None) -> httpx.Response:
    """GET with exponential backoff (2s / 4s / 8s) on transient failures.

    4xx other than 429 are raised immediately — a malformed query or a missing
    item will not fix itself by waiting.
    """
    client = _get_client()
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        if attempt > 0:
            await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
        try:
            r = await client.get(url, params=params, headers=_headers_for(url))
            r.raise_for_status()
            return r
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            if not _is_retryable(exc):
                raise
            last_error = exc
            logger.debug(
                "Retryable upstream failure (attempt %d/%d) for %s: %s",
                attempt + 1,
                RETRY_ATTEMPTS,
                url,
                exc,
            )
    assert last_error is not None
    raise last_error


async def _get(url: str, params: Optional[dict] = None) -> Any:
    return (await _request_with_retry(url, params)).json()


async def _get_text(url: str, params: Optional[dict] = None) -> str:
    return (await _request_with_retry(url, params)).text


def _handle_error(e: Exception, source: str = "") -> str:
    logger.warning(
        "Upstream error from %s: %s: %s",
        source or "unknown",
        type(e).__name__,
        str(e)[:200],
    )
    prefix = f"[{source}] " if source else ""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 429:
            return (
                f"{prefix}Error: Rate limit exceeded. "
                "For GitHub, set GITHUB_TOKEN for higher limits."
            )
        if code == 403:
            return f"{prefix}Error: Forbidden (HTTP 403). For GitHub, set GITHUB_TOKEN."
        return f"{prefix}Error: HTTP {code}"
    if isinstance(e, httpx.TimeoutException):
        return f"{prefix}Error: Request timed out. Try again in a moment."
    return f"{prefix}Error: {type(e).__name__}: {str(e)[:200]}"


def _ts_to_iso(ts: Optional[int]) -> str:
    if not ts:
        return "unknown"
    from datetime import timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# HackerNews helpers
# ---------------------------------------------------------------------------


# Item types accepted as a "story" for feed purposes. The jobstories feed
# returns items of type "job", which the previous story-only filter silently
# dropped — the feed would have come back empty.
_FEED_ITEM_TYPES = {"story", "job"}


async def _fetch_hn_item(item_id: int) -> Optional[dict]:
    """Fetch a single HN item.

    Returns None both for fetch failures and for the API's null response.
    Note: the Firebase API answers unknown IDs with HTTP 200 and a body of
    `null` rather than a 404, so a missing item is not an error here.
    """
    try:
        item = await _get(f"{HN_BASE_URL}/item/{item_id}.json")
    except Exception as e:
        logger.debug("HN item %s fetch failed: %s", item_id, e)
        return None
    return item if isinstance(item, dict) else None


async def _fetch_hn_stories(story_type: str, limit: int) -> list[dict]:
    ids: list[int] = await _get(f"{HN_BASE_URL}/{story_type}stories.json")
    ids = ids[: min(limit * 3, 120)]

    sem = asyncio.Semaphore(HN_MAX_CONCURRENCY)

    async def fetch_item(item_id: int) -> Optional[dict]:
        async with sem:
            return await _fetch_hn_item(item_id)

    items = await asyncio.gather(*[fetch_item(i) for i in ids])
    stories = [i for i in items if i and i.get("type") in _FEED_ITEM_TYPES and i.get("title")]
    return stories[:limit]


def _format_hn_story(s: dict) -> dict:
    item_id = s.get("id")
    hn_link = f"https://news.ycombinator.com/item?id={item_id}"
    return {
        "id": item_id,
        "type": s.get("type", "story"),
        "title": s.get("title", ""),
        # Ask HN posts carry no 'url' — the discussion itself is the content.
        "url": s.get("url") or hn_link,
        "score": s.get("score") or 0,
        # Job posts carry no 'descendants'.
        "comments": s.get("descendants") or 0,
        "by": s.get("by", ""),
        "posted": _ts_to_iso(s.get("time")),
        "hn_link": hn_link,
    }


# ---------------------------------------------------------------------------
# HackerNews comment threads
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_hn_text(raw: Optional[str], max_chars: int) -> str:
    """Turn HN's HTML comment markup into plain text for an LLM to read.

    HN serves comment bodies as a small HTML subset (`<p>`, `<i>`, `<pre>`,
    `<a href>`) with entity-escaped content. This is a readability conversion,
    not a sanitiser — the output is meant to be read, never re-rendered as HTML.
    """
    if not raw:
        return ""
    text = raw.replace("<p>", "\n\n").replace("</p>", "")
    text = _TAG_RE.sub("", text)
    text = html.unescape(text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _format_hn_comment(c: dict, text_chars: int) -> dict:
    return {
        "id": c.get("id"),
        "by": c.get("by", ""),
        "posted": _ts_to_iso(c.get("time")),
        "text": _clean_hn_text(c.get("text"), text_chars),
        "reply_count": len(c.get("kids") or []),
        "replies": [],
    }


def _is_visible_comment(c: Optional[dict]) -> bool:
    """Deleted and dead (flagged/killed) comments carry no usable signal."""
    if not c or c.get("type") != "comment":
        return False
    return not (c.get("deleted") or c.get("dead"))


async def _fetch_comment_tree(
    root_kids: list[int], max_depth: int, max_comments: int, text_chars: int
) -> tuple[list[dict], int, bool]:
    """Breadth-first walk of a comment tree under a global node budget.

    Breadth-first on purpose: HN orders `kids` by rank, so the first IDs at
    each level are the ones a reader actually wants. A depth-first walk would
    sink the whole budget into the first thread.

    The budget is split across levels rather than consumed greedily. On a story
    with 285 top-level comments, a greedy walk spends every slot on level 1 and
    returns no replies at all — which defeats the point of reading a thread.
    Each level may therefore claim only `remaining // levels_left` nodes, with
    the last level taking whatever is left. Levels that are narrower than their
    share simply pass the remainder down.

    Returns (comments, fetched_count, truncated).
    """
    sem = asyncio.Semaphore(HN_MAX_CONCURRENCY)

    async def fetch(item_id: int) -> Optional[dict]:
        async with sem:
            return await _fetch_hn_item(item_id)

    roots: list[dict] = []
    # Each level: the parent nodes to attach to, and the IDs to fetch for them.
    level: list[tuple[Optional[dict], list[int]]] = [(None, list(root_kids))]
    fetched = 0
    truncated = False

    for depth in range(max_depth):
        remaining = max_comments - fetched
        if remaining <= 0:
            truncated = truncated or bool(level)
            break
        levels_left = max_depth - depth
        level_budget = remaining if levels_left == 1 else max(1, remaining // levels_left)

        # Round-robin across the parents of this level: one hot sub-thread must
        # not swallow the level's budget while its siblings get nothing.
        pending: list[tuple[Optional[dict], int]] = []
        slot = 0
        exhausted = False
        while len(pending) < level_budget and not exhausted:
            exhausted = True
            for parent, kid_ids in level:
                if slot >= len(kid_ids):
                    continue
                exhausted = False
                if len(pending) >= level_budget:
                    break
                pending.append((parent, kid_ids[slot]))
            slot += 1
        if len(pending) < sum(len(kid_ids) for _, kid_ids in level):
            truncated = True
        if not pending:
            break

        items = await asyncio.gather(*[fetch(kid_id) for _, kid_id in pending])
        next_level: list[tuple[Optional[dict], list[int]]] = []
        for (parent, _kid_id), item in zip(pending, items):
            if not _is_visible_comment(item):
                continue
            assert item is not None
            node = _format_hn_comment(item, text_chars)
            fetched += 1
            if parent is None:
                roots.append(node)
            else:
                parent["replies"].append(node)
            kids = item.get("kids") or []
            if kids:
                next_level.append((node, list(kids)))
        level = next_level
        if not level:
            break
    else:
        # Depth budget exhausted while replies were still unexplored.
        truncated = truncated or bool(level)

    return roots, fetched, truncated


# ---------------------------------------------------------------------------
# arXiv helpers
# ---------------------------------------------------------------------------


def _parse_arxiv_entry(entry: _XmlElement, ns: str) -> dict:
    def t(tag: str) -> str:
        el = entry.find(f"{ns}{tag}")
        return el.text.strip() if el is not None and el.text else ""

    authors = [
        a.find(f"{ns}name").text.strip()
        for a in entry.findall(f"{ns}author")
        if a.find(f"{ns}name") is not None
    ][:5]

    link_el = entry.find(f"{ns}link[@rel='alternate']")
    pdf_el = entry.find(f"{ns}link[@title='pdf']")
    cat_el = entry.find("{http://arxiv.org/schemas/atom}primary_category")

    return {
        "id": t("id").split("/abs/")[-1],
        "title": t("title").replace("\n", " "),
        "abstract": t("summary").replace("\n", " ")[:400] + "…",
        "authors": authors,
        "published": t("published")[:10],
        "category": cat_el.get("term", "") if cat_el is not None else "",
        "url": link_el.get("href", t("id")) if link_el is not None else t("id"),
        "pdf": pdf_el.get("href", "") if pdf_el is not None else "",
    }


async def _fetch_arxiv(search_query: str, limit: int) -> list[dict]:
    xml_text = await _get_text(
        ARXIV_BASE_URL,
        {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
    )
    root = _DefusedET.fromstring(xml_text)
    ns = "{http://www.w3.org/2005/Atom}"
    return [_parse_arxiv_entry(e, ns) for e in root.findall(f"{ns}entry")]


# ---------------------------------------------------------------------------
# Lobste.rs helpers
# ---------------------------------------------------------------------------


def _lobsters_submitter(item: dict) -> str:
    """Read the submitter name from either shape of `submitter_user`.

    Lobste.rs used to nest the submitter as an object (`{"username": ...}`)
    and now returns a bare username string. Accept both so a future flip back
    does not break the tool again.
    """
    user = item.get("submitter_user")
    if isinstance(user, dict):
        return user.get("username", "")
    return user or ""


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class HnTopStoriesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    feed: str = Field(
        default="top",
        description=(
            "Feed type: 'top' (frontpage), 'best' (highest voted), 'new' (latest), "
            "'ask' (Ask HN questions), 'show' (Show HN projects), 'job' (YC job posts). "
            "Note: 'ask' and 'job' are short feeds (~30 items upstream)."
        ),
        pattern="^(top|best|new|ask|show|job)$",
    )
    limit: int = Field(default=10, description="Number of stories to return (1–30)", ge=1, le=30)
    min_score: int = Field(default=0, description="Minimum score filter (0 = no filter)", ge=0)


class HnDiscussionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    story_id: int = Field(
        ...,
        description="HackerNews item ID, e.g. from hn_top_stories or hn_search results",
        gt=0,
    )
    max_depth: int = Field(
        default=2,
        description="Reply nesting levels to walk (1–4). 1 = top-level comments only.",
        ge=1,
        le=4,
    )
    max_comments: int = Field(
        default=25,
        description="Total comments to fetch across all levels (1–100)",
        ge=1,
        le=100,
    )
    text_chars: int = Field(
        default=600,
        description="Truncate each comment body to N characters (100–2000)",
        ge=100,
        le=2000,
    )


class HnSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Search query (e.g. 'Claude MCP', 'LLM agents')",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(default=10, description="Number of results (1–20)", ge=1, le=20)
    days_back: int = Field(default=7, description="Look back N days (1–365)", ge=1, le=365)
    tags: Optional[str] = Field(
        default=None,
        description="HN tag filter: 'story', 'ask_hn', 'show_hn'. Leave empty for all.",
    )


class ArxivLatestInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    categories: list[str] = Field(
        default_factory=lambda: ["cs.AI", "cs.LG"],
        description=(
            "arXiv categories. Options: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, stat.ML. "
            "Default: ['cs.AI', 'cs.LG']"
        ),
    )
    limit: int = Field(default=10, description="Papers per category (1–20)", ge=1, le=20)

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        valid = set(ARXIV_AI_CATEGORIES)
        for cat in v:
            if cat not in valid:
                raise ValueError(f"Invalid category '{cat}'. Valid: {sorted(valid)}")
        if not v:
            raise ValueError("At least one category required.")
        return v


class ArxivSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Search terms (e.g. 'large language models agents')",
        min_length=1,
        max_length=300,
    )
    category: Optional[str] = Field(
        default=None, description="Restrict to category (e.g. 'cs.AI'). Empty = all."
    )
    limit: int = Field(default=10, description="Number of papers (1–20)", ge=1, le=20)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if v not in ARXIV_AI_CATEGORIES:
            raise ValueError(f"Invalid category '{v}'. Valid: {sorted(ARXIV_AI_CATEGORIES)}")
        return v


class LobstersHotInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    limit: int = Field(default=10, description="Number of stories (1–25)", ge=1, le=25)
    tag_filter: Optional[str] = Field(
        default=None,
        description="Filter by tag keyword (e.g. 'ai', 'ml', 'security'). Case-insensitive.",
    )


class GithubTrendingAiInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    topic: str = Field(
        default="llm",
        description="GitHub topic (e.g. 'llm', 'mcp', 'ai-agents', 'rag', 'openai', 'anthropic')",
        min_length=1,
        max_length=100,
    )
    limit: int = Field(default=10, description="Number of repos (1–15)", ge=1, le=15)
    min_stars: int = Field(default=100, description="Minimum star count", ge=0)
    sort: str = Field(
        default="stars",
        description="Sort by: 'stars' (total stars) or 'updated' (recently active)",
        pattern="^(stars|updated)$",
    )


class TechSignalDigestInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    focus: Optional[str] = Field(
        default=None,
        description="Topic focus (e.g. 'MCP', 'agents', 'open source'). Empty = broad overview.",
        max_length=100,
    )
    hn_limit: int = Field(
        default=5, description="HackerNews stories to include (1–10)", ge=1, le=10
    )
    arxiv_limit: int = Field(default=5, description="arXiv papers to include (1–10)", ge=1, le=10)
    lobsters_limit: int = Field(
        default=5, description="Lobste.rs stories to include (1–10)", ge=1, le=10
    )
    github_limit: int = Field(default=5, description="GitHub repos to include (1–10)", ge=1, le=10)


# ---------------------------------------------------------------------------
# Tool 1: hn_top_stories
# ---------------------------------------------------------------------------


@server.tool(
    name="hn_top_stories",
    annotations={
        "title": "HackerNews Top/Best/New Stories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def hn_top_stories(params: HnTopStoriesInput) -> str:
    """Fetch stories from any of the six HackerNews front-page feeds.

    Feeds: 'top' (frontpage), 'best' (highest voted), 'new' (latest),
    'ask' (Ask HN — questions to the community), 'show' (Show HN — projects
    people are shipping), 'job' (YC company job posts).

    'show' is the strongest signal for what practitioners are actually
    building; 'ask' for what they are stuck on. Upstream, 'ask' and 'job'
    hold only ~30 items, so a large limit may return fewer results.

    Args:
        params (HnTopStoriesInput):
            - feed (str): 'top', 'best', 'new', 'ask', 'show', or 'job'
            - limit (int): Stories to return (1–30)
            - min_score (int): Minimum score filter (job posts score 1)

    Returns:
        str: JSON with feed, count, stories[]. Each story: id, type, title, url,
             score, comments, by, posted, hn_link.
    """
    cache_key = f"hn_top|{params.feed}|{params.limit}|{params.min_score}"
    if cached := _cache_get(cache_key, "hn_top"):
        return cached
    try:
        stories = await _fetch_hn_stories(params.feed, params.limit * 2)
        if params.min_score > 0:
            stories = [s for s in stories if s.get("score", 0) >= params.min_score]
        stories = stories[: params.limit]
        result = json.dumps(
            {
                "feed": params.feed,
                "fetched_at": _now_iso(),
                "count": len(stories),
                "stories": [_format_hn_story(s) for s in stories],
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "HackerNews")


# ---------------------------------------------------------------------------
# Tool 2: hn_search
# ---------------------------------------------------------------------------


@server.tool(
    name="hn_search",
    annotations={
        "title": "HackerNews Full-Text Search (Algolia)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def hn_search(params: HnSearchInput) -> str:
    """Search HackerNews by keyword using the Algolia search API.

    Covers all historical HN content. Find discussions on specific
    technologies, papers, companies, or events.

    Args:
        params (HnSearchInput):
            - query (str): Search terms
            - limit (int): Results (1–20)
            - days_back (int): Recency window in days
            - tags (Optional[str]): 'story', 'ask_hn', 'show_hn', or empty

    Returns:
        str: JSON with query, total_found, count, hits[]. Each hit: id, title,
             url, score, comments, author, posted, hn_link, excerpt.
    """
    cache_key = f"hn_search|{params.query}|{params.limit}|{params.days_back}|{params.tags}"
    if cached := _cache_get(cache_key, "hn_search"):
        return cached
    try:
        cutoff = int(time.time()) - params.days_back * 86400
        algolia_params: dict[str, Any] = {
            "query": params.query,
            "hitsPerPage": params.limit,
            "numericFilters": f"created_at_i>{cutoff}",
        }
        if params.tags:
            algolia_params["tags"] = params.tags
        data = await _get(f"{HN_ALGOLIA_URL}/search", algolia_params)
        hits = [
            {
                "id": h.get("objectID"),
                "title": h.get("title") or h.get("story_title", ""),
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "score": h.get("points", 0),
                "comments": h.get("num_comments", 0),
                "author": h.get("author", ""),
                "posted": h.get("created_at", ""),
                "hn_link": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "excerpt": (h.get("story_text") or "")[:200],
            }
            for h in data.get("hits", [])
        ]
        result = json.dumps(
            {
                "query": params.query,
                "days_back": params.days_back,
                "total_found": data.get("nbHits", 0),
                "count": len(hits),
                "hits": hits,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "HN Algolia")


# ---------------------------------------------------------------------------
# Tool 3: hn_discussion
# ---------------------------------------------------------------------------


@server.tool(
    name="hn_discussion",
    annotations={
        "title": "HackerNews Comment Thread",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def hn_discussion(params: HnDiscussionInput) -> str:
    """Read the comment thread under a HackerNews story.

    Where hn_top_stories and hn_search tell you *what* is being discussed,
    this tells you *what is actually being argued* — the counter-arguments,
    the practitioner caveats, the "we tried this in production" replies that
    carry the real signal. Algolia can search comment text but does not
    return thread structure, so this is the only way to see who replied
    to whom.

    Get a story_id from hn_top_stories or hn_search first.

    Comments are walked breadth-first, so the highest-ranked top-level
    comments come back first. Deleted and flagged comments are skipped.
    Popular threads run to several hundred comments and each one costs a
    request upstream, so both depth and total count are capped — check the
    'truncated' flag to see whether the thread was cut short.

    Args:
        params (HnDiscussionInput):
            - story_id (int): HackerNews item ID
            - max_depth (int): Reply nesting levels (1–4, default 2)
            - max_comments (int): Total comment budget (1–100, default 25)
            - text_chars (int): Per-comment text truncation (100–2000)

    Returns:
        str: JSON with story{}, total_comments (as reported by HN),
             fetched_comments, truncated, comments[]. Each comment: id, by,
             posted, text, reply_count, replies[] (same shape, nested).
    """
    cache_key = (
        f"hn_discussion|{params.story_id}|{params.max_depth}"
        f"|{params.max_comments}|{params.text_chars}"
    )
    if cached := _cache_get(cache_key, "hn_discussion"):
        return cached
    try:
        item = await _fetch_hn_item(params.story_id)
        if item is None:
            # The API answers unknown IDs with HTTP 200 and a null body, so
            # this is the only place a "not found" can surface.
            return (
                f"[HackerNews] No item found with ID {params.story_id}. "
                "IDs come from hn_top_stories or hn_search results."
            )
        if item.get("type") == "comment":
            parent = item.get("parent")
            hint = f" Its parent item is {parent}." if parent else ""
            return (
                f"[HackerNews] Item {params.story_id} is a comment, not a story."
                f"{hint} Pass a story ID to read its thread."
            )

        roots, fetched, truncated = await _fetch_comment_tree(
            item.get("kids") or [],
            params.max_depth,
            params.max_comments,
            params.text_chars,
        )

        result = json.dumps(
            {
                "fetched_at": _now_iso(),
                "story": _format_hn_story(item),
                "story_text": _clean_hn_text(item.get("text"), params.text_chars),
                "total_comments": item.get("descendants") or 0,
                "fetched_comments": fetched,
                "truncated": truncated,
                "comments": roots,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "HackerNews")


# ---------------------------------------------------------------------------
# Tool 4: arxiv_latest
# ---------------------------------------------------------------------------


@server.tool(
    name="arxiv_latest",
    annotations={
        "title": "arXiv Latest AI/ML Papers by Category",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def arxiv_latest(params: ArxivLatestInput) -> str:
    """Fetch the most recently submitted papers from arXiv AI/ML categories.

    Papers appear hours before press coverage — the fastest signal of
    what is happening at the AI research frontier.

    Categories: cs.AI (Artificial Intelligence), cs.LG (Machine Learning),
    cs.CL (NLP), cs.CV (Computer Vision), cs.NE (Neural Computing), stat.ML.

    Args:
        params (ArxivLatestInput):
            - categories (List[str]): arXiv category codes
            - limit (int): Papers per category (1–20)

    Returns:
        str: JSON with categories, total_papers, by_category dict.
             Each paper: id, title, abstract (400 chars), authors, published, url, pdf.
    """
    cache_key = f"arxiv_latest|{'_'.join(sorted(params.categories))}|{params.limit}"
    if cached := _cache_get(cache_key, "arxiv"):
        return cached
    try:
        results_raw = await asyncio.gather(
            *[_fetch_arxiv(f"cat:{c}", params.limit) for c in params.categories]
        )
        by_category = {cat: papers for cat, papers in zip(params.categories, results_raw)}
        result = json.dumps(
            {
                "fetched_at": _now_iso(),
                "categories": params.categories,
                "total_papers": sum(len(p) for p in by_category.values()),
                "by_category": by_category,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "arXiv")


# ---------------------------------------------------------------------------
# Tool 5: arxiv_search
# ---------------------------------------------------------------------------


@server.tool(
    name="arxiv_search",
    annotations={
        "title": "arXiv Full-Text Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def arxiv_search(params: ArxivSearchInput) -> str:
    """Search arXiv for papers matching a query, sorted by submission date.

    Searches title, abstract and author fields. Optionally restrict to a
    specific AI/ML category.

    Args:
        params (ArxivSearchInput):
            - query (str): Search terms (e.g. 'LLM agents tool use')
            - category (Optional[str]): arXiv category filter
            - limit (int): Papers to return (1–20)

    Returns:
        str: JSON with query, category, count, papers[].
             Each paper: id, title, abstract, authors, published, url, pdf.
    """
    cache_key = f"arxiv_search|{params.query}|{params.category}|{params.limit}"
    if cached := _cache_get(cache_key, "arxiv"):
        return cached
    try:
        if params.category:
            search_query = f"all:{params.query} AND cat:{params.category}"
        else:
            search_query = f"all:{params.query}"
        papers = await _fetch_arxiv(search_query, params.limit)
        result = json.dumps(
            {
                "query": params.query,
                "category": params.category,
                "fetched_at": _now_iso(),
                "count": len(papers),
                "papers": papers,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "arXiv")


# ---------------------------------------------------------------------------
# Tool 6: lobsters_hot
# ---------------------------------------------------------------------------


@server.tool(
    name="lobsters_hot",
    annotations={
        "title": "Lobste.rs Hottest Tech Stories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def lobsters_hot(params: LobstersHotInput) -> str:
    """Fetch the hottest stories from Lobste.rs, a curated tech community.

    Lobste.rs is smaller and more technically focused than HackerNews.
    Invitation-only membership ensures higher signal-to-noise ratio.

    Args:
        params (LobstersHotInput):
            - limit (int): Stories to return (1–25)
            - tag_filter (Optional[str]): Tag substring filter (e.g. 'ai', 'ml')

    Returns:
        str: JSON with count, stories[]. Each story: title, url, score,
             comments, tags, submitter, submitted_at, lobsters_url.
    """
    cache_key = f"lobsters|{params.limit}|{params.tag_filter}"
    if cached := _cache_get(cache_key, "lobsters"):
        return cached
    try:
        data: list[dict] = await _get(f"{LOBSTERS_BASE_URL}/hottest.json")
        stories = []
        for item in data:
            if params.tag_filter:
                tags = item.get("tags", [])
                if not any(params.tag_filter.lower() in t.lower() for t in tags):
                    continue
            stories.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url") or item.get("comments_url", ""),
                    "score": item.get("score", 0),
                    "comments": item.get("comment_count", 0),
                    "tags": item.get("tags", []),
                    "submitter": _lobsters_submitter(item),
                    "submitted_at": (item.get("created_at", "")[:16] or "").replace("T", " ")
                    + " UTC",
                    "lobsters_url": item.get("comments_url", ""),
                }
            )
            if len(stories) >= params.limit:
                break
        result = json.dumps(
            {
                "tag_filter": params.tag_filter,
                "fetched_at": _now_iso(),
                "count": len(stories),
                "stories": stories,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "Lobste.rs")


# ---------------------------------------------------------------------------
# Tool 7: github_trending_ai
# ---------------------------------------------------------------------------


@server.tool(
    name="github_trending_ai",
    annotations={
        "title": "GitHub Trending AI/Tech Repos",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def github_trending_ai(params: GithubTrendingAiInput) -> str:
    """Search GitHub for trending repositories by topic.

    A surge of starred repos on a topic is a strong adoption signal.
    No auth required (60 req/h). Set GITHUB_TOKEN for 5,000 req/h.

    Args:
        params (GithubTrendingAiInput):
            - topic (str): GitHub topic tag (e.g. 'llm', 'mcp', 'ai-agents')
            - limit (int): Repos to return (1–15)
            - min_stars (int): Minimum stars filter
            - sort (str): 'stars' or 'updated'

    Returns:
        str: JSON with topic, total_found, count, repos[].
             Each repo: name, description, stars, forks, language, topics, updated_at, url.
    """
    cache_key = f"github|{params.topic}|{params.sort}|{params.min_stars}|{params.limit}"
    if cached := _cache_get(cache_key, "github"):
        return cached
    try:
        query = f"topic:{params.topic}"
        if params.min_stars > 0:
            query += f" stars:>={params.min_stars}"
        data = await _get(
            f"{GITHUB_BASE_URL}/search/repositories",
            {"q": query, "sort": params.sort, "order": "desc", "per_page": params.limit},
        )
        repos = [
            {
                "name": r["full_name"],
                "description": r.get("description", ""),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language", ""),
                "topics": r.get("topics", [])[:8],
                "updated_at": r.get("updated_at", "")[:10],
                "url": r.get("html_url", ""),
            }
            for r in data.get("items", [])
        ]
        result = json.dumps(
            {
                "topic": params.topic,
                "sort": params.sort,
                "fetched_at": _now_iso(),
                "total_found": data.get("total_count", 0),
                "count": len(repos),
                "repos": repos,
            },
            indent=2,
            ensure_ascii=False,
        )
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "GitHub")


# ---------------------------------------------------------------------------
# Tool 8: tech_signal_digest
# ---------------------------------------------------------------------------


@server.tool(
    name="tech_signal_digest",
    annotations={
        "title": "Aggregated Tech & AI Signal Digest",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def tech_signal_digest(params: TechSignalDigestInput) -> str:
    """Aggregate tech & AI signals from all four sources in one call.

    The primary tool for a comprehensive daily or weekly tech intelligence
    briefing. Combines HackerNews, arXiv, Lobste.rs and GitHub into one
    structured JSON digest. Use 'focus' to filter for a specific topic.

    Args:
        params (TechSignalDigestInput):
            - focus (Optional[str]): Topic filter (e.g. 'MCP', 'agents')
            - hn_limit (int): HN stories (1–10)
            - arxiv_limit (int): arXiv papers (1–10)
            - lobsters_limit (int): Lobste.rs stories (1–10)
            - github_limit (int): GitHub repos (1–10)

    Returns:
        str: JSON digest with generated_at, focus, sources{hn, arxiv, lobsters, github}.
             Each source has label, count, and its items list.
    """
    focus_lower = params.focus.lower() if params.focus else None
    cache_key = (
        f"digest|{params.focus}|{params.hn_limit}|{params.arxiv_limit}"
        f"|{params.lobsters_limit}|{params.github_limit}"
    )
    if cached := _cache_get(cache_key, "digest"):
        return cached

    def _matches_focus(items: list[dict], *fields: str) -> list[dict]:
        if not focus_lower:
            return items
        return [
            item
            for item in items
            if focus_lower in " ".join(str(item.get(f, "")) for f in fields).lower()
        ]

    try:
        hn_raw, arxiv_raw, lob_raw, gh_raw = await asyncio.gather(
            _fetch_hn_stories("top", params.hn_limit * 4),
            _fetch_arxiv("cat:cs.AI OR cat:cs.LG OR cat:cs.CL", params.arxiv_limit * 2),
            _get(f"{LOBSTERS_BASE_URL}/hottest.json"),
            _get(
                f"{GITHUB_BASE_URL}/search/repositories",
                {
                    "q": "topic:llm OR topic:ai-agents OR topic:mcp stars:>=100",
                    "sort": "updated",
                    "order": "desc",
                    "per_page": params.github_limit * 2,
                },
            ),
        )

        hn_stories = _matches_focus([_format_hn_story(s) for s in hn_raw], "title")[
            : params.hn_limit
        ]

        arxiv_papers = _matches_focus(arxiv_raw, "title", "abstract")[: params.arxiv_limit]

        lob_stories = _matches_focus(
            [
                {
                    "title": s.get("title", ""),
                    "url": s.get("url") or s.get("comments_url", ""),
                    "score": s.get("score", 0),
                    "tags": s.get("tags", []),
                    "lobsters_url": s.get("comments_url", ""),
                }
                for s in lob_raw
            ],
            "title",
            "tags",
        )[: params.lobsters_limit]

        gh_repos = _matches_focus(
            [
                {
                    "name": r["full_name"],
                    "description": r.get("description", ""),
                    "stars": r.get("stargazers_count", 0),
                    "language": r.get("language", ""),
                    "topics": r.get("topics", [])[:5],
                    "url": r.get("html_url", ""),
                }
                for r in gh_raw.get("items", [])
            ],
            "name",
            "description",
        )[: params.github_limit]

        digest = {
            "generated_at": _now_iso(),
            "focus": params.focus or "broad tech & AI",
            "sources": {
                "hn": {"label": "HackerNews", "count": len(hn_stories), "stories": hn_stories},
                "arxiv": {
                    "label": "arXiv (cs.AI/cs.LG/cs.CL)",
                    "count": len(arxiv_papers),
                    "papers": arxiv_papers,
                },
                "lobsters": {
                    "label": "Lobste.rs",
                    "count": len(lob_stories),
                    "stories": lob_stories,
                },
                "github": {"label": "GitHub Trending", "count": len(gh_repos), "repos": gh_repos},
            },
        }

        result = json.dumps(digest, indent=2, ensure_ascii=False)
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        return _handle_error(e, "digest")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _resolve_http_bind() -> tuple[str, int]:
    """Resolve MCP_HOST/MCP_PORT and refuse public bind without bearer token.

    Default bind is 127.0.0.1. Non-loopback binds require MCP_BEARER_TOKEN
    to prevent accidental public exposure of the server.
    """
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8000"))
    loopback = {"127.0.0.1", "localhost", "::1"}
    if host not in loopback and not os.environ.get("MCP_BEARER_TOKEN"):
        raise RuntimeError(
            f"Refusing to bind streamable_http to non-loopback host '{host}' "
            "without MCP_BEARER_TOKEN. Set MCP_BEARER_TOKEN, or bind to "
            "127.0.0.1 and place an authenticating reverse proxy in front."
        )
    return host, port


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    logger.info("Starting hn-tech-signal-mcp transport=%s", transport)
    if transport == "streamable_http":
        host, port = _resolve_http_bind()
        server.settings.host = host
        server.settings.port = port
        server.run(transport="streamable_http")
    else:
        server.run()


if __name__ == "__main__":
    main()
