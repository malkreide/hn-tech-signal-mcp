"""Output schemas of the eight tools — what `outputSchema` advertises.

Each model mirrors the JSON a tool already builds in `server.py`; nothing is
reshaped for the schema. The tool still returns that JSON as text (the text
block every client reads), and the same object goes out as `structuredContent`
next to it. The SDK validates `structuredContent` against the model before the
result leaves the server, so a schema that drifts from the code fails the call
instead of lying to the client.

Two deliberate choices:

* ``extra="forbid"``. Every key is set by this server, never passed through
  from upstream — so an unknown key can only mean a code change without a
  schema change. ``additionalProperties: false`` tells the client the list is
  complete; ``extra="allow"`` would let the two drift apart silently.
* Upstream-derived scalars are nullable. ``item.get("title", "")`` yields
  ``None`` when the source sends ``"title": null`` — the default only covers a
  missing key. A strict ``str`` would turn one null field upstream into a
  failed tool call here. Values this server computes itself (counts, links,
  timestamps) stay strict.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# HackerNews
# ---------------------------------------------------------------------------


class HnStory(_Out):
    id: Optional[int]
    type: Optional[str] = Field(description="'story' or 'job'")
    title: Optional[str]
    url: str = Field(description="Linked article, or the HN item itself for Ask HN")
    score: int
    comments: int
    by: Optional[str]
    posted: str = Field(description="UTC timestamp, or 'unknown'")
    hn_link: str


class HnTopStoriesOutput(_Out):
    feed: str
    fetched_at: str
    count: int
    stories: list[HnStory]


class HnSearchHit(_Out):
    id: Optional[str]
    title: Optional[str]
    url: Optional[str]
    score: Optional[int]
    comments: Optional[int]
    author: Optional[str]
    posted: Optional[str]
    hn_link: str
    excerpt: str


class HnSearchOutput(_Out):
    query: str
    days_back: int
    total_found: int = Field(description="Hits Algolia reports in total, not just returned")
    count: int
    hits: list[HnSearchHit]


class HnComment(_Out):
    id: Optional[int]
    by: Optional[str]
    posted: str
    text: str
    reply_count: int = Field(description="Direct replies upstream, fetched or not")
    replies: list[HnComment]


class HnDiscussionOutput(_Out):
    fetched_at: str
    story: HnStory
    story_text: str
    total_comments: int = Field(description="As reported by HN")
    fetched_comments: int
    truncated: bool = Field(description="True if depth or comment budget cut the thread short")
    comments: list[HnComment]


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------


class ArxivPaper(_Out):
    id: str
    title: str
    abstract: str = Field(description="First 400 characters")
    authors: list[str] = Field(description="First five")
    published: str
    category: str = Field(description="Primary category")
    categories: list[str] = Field(description="All categories, primary included")
    url: str
    pdf: str


class ArxivLatestOutput(_Out):
    fetched_at: str
    categories: list[str]
    total_papers: int
    distinct_papers: int
    by_category: dict[str, list[ArxivPaper]]
    incomplete_categories: Optional[list[str]] = Field(
        default=None,
        description="Present only when a category returned fewer than limit within the window",
    )
    note: Optional[str] = None


class ArxivSearchOutput(_Out):
    query: str
    category: Optional[str]
    fetched_at: str
    count: int
    papers: list[ArxivPaper]


# ---------------------------------------------------------------------------
# Lobste.rs
# ---------------------------------------------------------------------------


class LobstersStory(_Out):
    title: Optional[str]
    url: Optional[str]
    score: Optional[int]
    comments: Optional[int]
    tags: Optional[list[str]]
    submitter: Optional[str]
    submitted_at: str
    lobsters_url: Optional[str]


class LobstersHotOutput(_Out):
    tag_filter: Optional[str]
    fetched_at: str
    count: int
    stories: list[LobstersStory]


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


class GithubRepo(_Out):
    name: str
    description: Optional[str]
    stars: Optional[int]
    forks: Optional[int]
    language: Optional[str]
    topics: Optional[list[str]]
    updated_at: Optional[str]
    url: Optional[str]


class GithubTrendingOutput(_Out):
    topic: str
    sort: str
    fetched_at: str
    total_found: int
    count: int
    repos: list[GithubRepo]


# ---------------------------------------------------------------------------
# Digest
# ---------------------------------------------------------------------------


class _DigestSection(_Out):
    label: str
    count: int
    error: Optional[str] = Field(
        default=None,
        description="Present only when the source failed; count is then 0 and means unknown",
    )


class DigestLobstersStory(_Out):
    title: Optional[str]
    url: Optional[str]
    score: Optional[int]
    tags: Optional[list[str]]
    lobsters_url: Optional[str]


class DigestGithubRepo(_Out):
    name: str
    description: Optional[str]
    stars: Optional[int]
    language: Optional[str]
    topics: Optional[list[str]]
    url: Optional[str]


class DigestHnSection(_DigestSection):
    stories: list[HnStory]


class DigestArxivSection(_DigestSection):
    papers: list[ArxivPaper]


class DigestLobstersSection(_DigestSection):
    stories: list[DigestLobstersStory]


class DigestGithubSection(_DigestSection):
    repos: list[DigestGithubRepo]
    incomplete_topics: Optional[list[str]] = Field(
        default=None, description="Topics whose sweep failed; the section is short by them"
    )


class DigestSources(_Out):
    hn: DigestHnSection
    arxiv: DigestArxivSection
    lobsters: DigestLobstersSection
    github: DigestGithubSection


class TechSignalDigestOutput(_Out):
    generated_at: str
    focus: str
    degraded_sources: list[str] = Field(
        description="Sources that failed; treat their sections as unknown, not as empty"
    )
    sources: DigestSources
