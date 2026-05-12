# Changelog

All notable changes to `hn-tech-signal-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **SEC-001:** `GITHUB_TOKEN` is now only attached to requests targeting `api.github.com`. Previously, the token was sent as `Authorization: Bearer` to **all** upstream APIs (HackerNews, Algolia, arXiv, Lobste.rs) due to a shared header builder, leaking the credential to third-party hosts.
- **SEC-002:** The `streamable_http` transport now defaults to binding `127.0.0.1`. Non-loopback values for `MCP_HOST` require `MCP_BEARER_TOKEN` to be set; otherwise the server refuses to start. Prevents accidental public exposure of the unauthenticated HTTP endpoint.
- **SEC-003:** arXiv XML responses are now parsed with `defusedxml` instead of `xml.etree.ElementTree`. Mitigates XXE and billion-laughs class of XML attacks.

### Changed
- **ARCH-001:** Replaced the stale `fastmcp>=2.0.0` dependency with `mcp>=1.2.0` — the actually imported package. Added `defusedxml>=0.7.1` as a direct dependency.
- **SDK-001:** Replaced six occurrences of deprecated `datetime.utcnow()` with a timezone-aware `_now_iso()` helper. Removes `DeprecationWarning` noise on Python 3.12+.
- **OBS-001:** Activated the previously-declared `hn-tech-signal-mcp` logger. `_handle_error` emits a `WARNING` per upstream failure, individual HN item fetch failures are logged at `DEBUG`, and `main()` initialises `logging.basicConfig` (controlled by `LOG_LEVEL`, default `INFO`).

### Added
- `MCP_HOST` environment variable (default `127.0.0.1`).
- `MCP_BEARER_TOKEN` environment variable (required for public bind).
- `LOG_LEVEL` environment variable (default `INFO`).
- Regression tests for SEC-001, SEC-002, SEC-003, SDK-001 and OBS-001 in `tests/test_server.py` (25 unit tests total).

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
