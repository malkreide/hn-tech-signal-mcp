# Changelog

All notable changes to `hn-tech-signal-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-07-28

Expands the HackerNews layer to the parts of the [official Firebase API](https://github.com/HackerNews/API) the server was not yet using, and closes two resilience gaps in the shared HTTP path. Verified against a live probe of the API on 2026-07-28.

### Added
- **`hn_top_stories` now serves all six HN feeds.** `ask` (Ask HN), `show` (Show HN) and `job` (YC job posts) join the existing `top` / `best` / `new`. `show` is the individual-level counterpart to the GitHub practice layer; `ask` surfaces what practitioners are stuck on.
- **New tool `hn_discussion`** — reads the nested comment thread under a story. This is the one thing the Algolia index cannot provide: it can search comment text but returns no thread structure, so replies cannot be attributed to what they answer. Comments come back as plain text with HN's HTML markup stripped.
- Live tests for the three new feeds and for `hn_discussion`, including the null-item path.

### Changed
- **Retry with exponential backoff for every upstream call.** `_request_with_retry` makes up to `RETRY_ATTEMPTS` (4) attempts, waiting 2s / 4s / 8s. Network errors, 5xx and 429 are retried; other 4xx fail immediately. Previously a single transient blip on any of the four sources surfaced to the user as an error.
- **One pooled `httpx.AsyncClient` for the process**, created lazily and closed through a new FastMCP lifespan. Previously every request opened and discarded its own client, so a feed fan-out paid a full TCP + TLS handshake per HackerNews item.
- **The HN item fan-out is bounded** by `HN_MAX_CONCURRENCY` (12) and sized against the connection pool. It was previously unbounded at up to 120 simultaneous requests.
- `_format_hn_story` reports the item `type` and tolerates absent or null `url` / `score` / `descendants`.
- CI coverage floor raised from 45 % to 65 % (actual: 69 %) now that the HackerNews paths have respx fixtures.

### Fixed
- **The `job` feed would have returned nothing.** `_fetch_hn_stories` filtered on `type == "story"`, but `jobstories.json` yields items of `type: "job"` — they were dropped silently. Both types are now accepted.
- `version` in `pyproject.toml` (`0.2.4`) disagreed with `__init__.py` (`0.2.1`). Since `[tool.hatch.version]` reads the latter, builds carried the wrong number. Both are now `0.3.0`, and `test_version_matches_pyproject` fails on any future drift.
- The `User-Agent` header was pinned at `hn-tech-signal-mcp/0.1.0` regardless of the actual release.
- **`lobsters_hot` was broken against the current Lobste.rs API** (found while verifying the release, unrelated to the HackerNews work). Lobste.rs changed `submitter_user` from an object to a bare username string, so `.get("username")` raised `AttributeError` and every call returned an error string. `_lobsters_submitter` now accepts both shapes.

### Known findings (live probe, 2026-07-28)
- **The HN API answers unknown item IDs with HTTP 200 and a body of `null`, not a 404.** Any code path that fetches an item by ID has to test for the null body — an HTTP-level error check will report success on a nonexistent item. `hn_discussion` turns this into an explicit message.
- `HEAD` on the Firebase API returns **405 Method Not Allowed**; it only serves GET. Not usable as a health check.
- No rate-limit headers, and `Cache-Control: no-cache` on every response — caching is entirely the client's responsibility.
- Feed sizes differ by an order of magnitude: `top`/`new` hold 500 IDs, `best`/`show` 200, `ask` and `job` roughly 30. A uniform `limit` therefore behaves differently per feed.
- Job items carry no `descendants` key, Ask HN items carry no `url` key. Absent, not null — `.get(key, default)` is not enough on its own where the key can also be present and null.

## [0.2.1] — 2026-05-12

First successful PyPI publish after the 2026-05-12 audit. Contents are the same as the `v0.2.0` GitHub release tag; the `v0.2.0` PyPI upload failed because `version` in `pyproject.toml` and `__init__.py` was not bumped, so the build produced `0.1.0` artefacts that PyPI rejected with `400 File already exists`. This release re-publishes the audit-closure baseline under the correct version.

### Security
- **SEC-001:** `GITHUB_TOKEN` is now only attached to requests targeting `api.github.com`. Previously, the token was sent as `Authorization: Bearer` to **all** upstream APIs (HackerNews, Algolia, arXiv, Lobste.rs) due to a shared header builder, leaking the credential to third-party hosts.
- **SEC-002:** The `streamable_http` transport now defaults to binding `127.0.0.1`. Non-loopback values for `MCP_HOST` require `MCP_BEARER_TOKEN` to be set; otherwise the server refuses to start. Prevents accidental public exposure of the unauthenticated HTTP endpoint.
- **SEC-003:** arXiv XML responses are now parsed with `defusedxml` instead of `xml.etree.ElementTree`. Mitigates XXE and billion-laughs class of XML attacks.
- **SEC-004:** `arxiv_search.category` is now validated against the same `ARXIV_AI_CATEGORIES` whitelist as `arxiv_latest.categories`. Empty string normalises to `None`.

### Changed
- **ARCH-001:** Replaced the stale `fastmcp>=2.0.0` dependency with `mcp>=1.2.0` — the actually imported package. Added `defusedxml>=0.7.1` as a direct dependency.
- **SDK-001:** Replaced six occurrences of deprecated `datetime.utcnow()` with a timezone-aware `_now_iso()` helper. Removes `DeprecationWarning` noise on Python 3.12+.
- **SDK-002:** Renamed the module-level FastMCP instance from `mcp` to `server` to stop shadowing the `mcp` SDK package import.
- **SCALE-001:** The in-memory TTL cache is now an `OrderedDict` with LRU eviction at `_CACHE_MAX_ENTRIES = 512` entries. Prevents unbounded memory growth in long-running `streamable_http` mode.
- **OBS-001:** Activated the previously-declared `hn-tech-signal-mcp` logger. `_handle_error` emits a `WARNING` per upstream failure, individual HN item fetch failures are logged at `DEBUG`, and `main()` initialises `logging.basicConfig` (controlled by `LOG_LEVEL`, default `INFO`).
- Long error and cache-key strings reformatted for the new `ruff format` gate.

### Added
- `MCP_HOST` environment variable (default `127.0.0.1`).
- `MCP_BEARER_TOKEN` environment variable (required for public bind).
- `LOG_LEVEL` environment variable (default `INFO`).
- `SECURITY.md` describing the vulnerability reporting process.
- `.github/dependabot.yml` for weekly pip and monthly github-actions updates.
- `.github/CODEOWNERS` for review routing.
- CI now runs `ruff check`, `ruff format --check` and `pytest --cov` with a 45 % floor.
- Regression tests for all 11 audit findings in `tests/test_server.py` (30 unit tests total).

### Fixed
- Bumped `version` to `0.2.1` in `pyproject.toml`, `src/hn_tech_signal_mcp/__init__.py` and the version assertion in `tests/test_server.py`. Root cause of the v0.2.0 PyPI failure.

## [0.1.0] — 2026-03-22

### Added
- `hn_top_stories` — HackerNews top/best/new/ask/show/job stories with optional AI keyword filter
- `hn_search` — HackerNews full-text search via Algolia (full history, date range filter)
- `arxiv_latest` — Latest arXiv papers by category (cs.AI, cs.LG, cs.CL, cs.CV, cs.RO, stat.ML)
- `arxiv_search` — arXiv paper search by keyword, title (`ti:`), author (`au:`), abstract (`abs:`)
- `lobsters_hot` — Lobste.rs hottest stories with tag filter
- `github_trending_ai` — GitHub repository search by topic, stars, sort order
- `tech_signal_digest` — Aggregated cross-source Markdown briefing (anchor demo tool)
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud/Render.com)
- Optional `GITHUB_TOKEN` support for higher GitHub rate limits
- 21 unit tests + 5 live integration tests
- README.md (English) + README.de.md (German / Schweizer Rechtschreibung)
- CONTRIBUTING.md
