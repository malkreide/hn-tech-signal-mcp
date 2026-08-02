# Changelog

All notable changes to `hn-tech-signal-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] — 2026-08-02

Ships everything `0.4.0` described. **`0.4.0` was tagged but never published:**
the tag exists on GitHub, no release was ever cut from it, so the release
workflow — which fires on `release: published` — never ran, and PyPI's latest
stayed at the broken `0.3.0`. Rather than move an existing tag, the contents go
out under `0.4.1` together with the fix below. Everything in the `0.4.0` section
is part of this release; read the two together.

### Fixed

- **The `User-Agent` header reported `0.3.0` on every outbound request.** It was
  a string literal in `_BASE_HEADERS`, so the 0.4.0 bump left it behind and HN,
  arXiv, Lobste.rs and GitHub all saw a client version that no longer existed.
  It is now interpolated from `__version__`, which makes `__init__.py` the only
  place a version is written — the same invariant the version tests already
  guard for `pyproject.toml` and `server.json`.
- `test_user_agent_tracks_the_package_version` fails both on a mismatch and on
  the literal coming back, and `test_user_agent_reaches_every_outbound_request`
  pins the header to all four hosts. Nothing asserted on the header before, so
  the drift was invisible to CI.

## [0.4.0] — 2026-08-02

This release exists so that a repair reaches the people running the server:
**the published `0.3.0` cannot be installed any more.** It declares `mcp` with
no upper bound, and `mcp` 2.0.0 removed `mcp.server.fastmcp` — so a fresh
`pip install hn-tech-signal-mcp` resolves to 2.0.0 and the console script dies
on startup with `ModuleNotFoundError`. Measured against the real artefact in an
empty venv, cold and warm interpreter alike.

The `v0.3.0` tag predates the 2.x migration: the fix has been on `main` ever
since and was never released, while `main` kept the same version number as the
broken artefact — so nothing contradicted it.

### Changed (breaking)

- **Migrated to the `mcp` Python SDK 2.x.** The server API moved from
  `mcp.server.fastmcp` to `mcp.server.mcpserver` with no compatibility shim,
  and the dependency is now `mcp>=2.0.0,<3`. The tool surface is unchanged —
  what breaks is embedding this server's Python API and the dependency floor.
  Anyone who must stay on `mcp` 1.x should stay on 0.3.0, and pin an upper
  bound themselves, because the published 0.3.0 has none.

### Fixed

- **The MCP Registry publish for `v0.3.0` failed with HTTP 422.** `server.json`'s `description` was 109 characters; the registry caps it at 100. Shortened to 85. PyPI was unaffected — `0.3.0` published successfully, only the registry step of the release workflow failed.
- `test_server_json_description_within_registry_limit` now fails in CI on a description over 100 characters, and `test_server_json_points_at_this_package` checks the registry entry still references this package. The 422 otherwise surfaces at the very last step of a release, after PyPI has already been published and can no longer be taken back.

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
- CI coverage floor raised from 45 % to 65 % (actual: 72 %) now that the HackerNews paths have respx fixtures.
- **`src/hn_tech_signal_mcp/__init__.py` is now the single source of the version.** `[project]` declares `dynamic = ["version"]` and no longer carries a static `version`, so the `[tool.hatch.version]` path it has always named is finally the one hatchling reads. Bumping a release now means editing one file. `test_version_has_exactly_one_source` fails if a static `version` is ever put back — guarding the configuration rather than comparing two values, because two values only disagree after the damage is done.

### Fixed
- **The `job` feed would have returned nothing.** `_fetch_hn_stories` filtered on `type == "story"`, but `jobstories.json` yields items of `type: "job"` — they were dropped silently. Both types are now accepted.
- `version` in `pyproject.toml` (`0.2.4`) disagreed with `__init__.py` (`0.2.1`), so `__version__` under-reported the installed version to anything introspecting the package — and `test_version` asserted the stale value, locking the discrepancy in. Both are now `0.3.0`, and `test_version_matches_pyproject` fails on any future drift.
- The `User-Agent` header was pinned at `hn-tech-signal-mcp/0.1.0` regardless of the actual release.
- **`lobsters_hot` was broken against the current Lobste.rs API** (found while verifying the release, unrelated to the HackerNews work). Lobste.rs changed `submitter_user` from an object to a bare username string, so `.get("username")` raised `AttributeError` and every call returned an error string. `_lobsters_submitter` now accepts both shapes.

### Known findings (live probe, 2026-07-28)
- **The HN API answers unknown item IDs with HTTP 200 and a body of `null`, not a 404.** Any code path that fetches an item by ID has to test for the null body — an HTTP-level error check will report success on a nonexistent item. `hn_discussion` turns this into an explicit message.
- `HEAD` on the Firebase API returns **405 Method Not Allowed**; it only serves GET. Not usable as a health check.
- No rate-limit headers, and `Cache-Control: no-cache` on every response — caching is entirely the client's responsibility.
- Feed sizes differ by an order of magnitude: `top`/`new` hold 500 IDs, `best`/`show` 200, `ask` and `job` roughly 30. A uniform `limit` therefore behaves differently per feed.
- Job items carry no `descendants` key, Ask HN items carry no `url` key. Absent, not null — `.get(key, default)` is not enough on its own where the key can also be present and null.

### Known findings (packaging)
- **`[tool.hatch.version]` was inert, and is now authoritative.** It named `src/hn_tech_signal_mcp/__init__.py` as the version source, but `[project]` also declared a static `version` and no `dynamic = ["version"]` — so hatchling read the static field and never consulted the file. Verified by building with `pyproject.toml` at `9.9.9` and `__init__.py` at `1.1.1`: the wheel came out `hn_tech_signal_mcp-9.9.9`. This is why PyPI holds `0.2.4` even though `__init__.py` said `0.2.1` at the time — two version fields, one of them decorative, and nothing failing to point that out. Resolved in this release (see *Changed*).

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
