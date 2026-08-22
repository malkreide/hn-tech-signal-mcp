# Changelog

All notable changes to `hn-tech-signal-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Frischehinweise auf den auflistenden Methoden** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides auf
  «sofort veraltet, nie geteilt» — wer nichts übergibt, lässt jeden Client bei
  jeder Verbindung neu auflisten. `resources/read` und `prompts/get` bleiben
  ohne Hinweis: das wäre eine Zusicherung über den Inhalt statt über das
  Verzeichnis.

### Added

- **Die Pruefsummen im Fixture-Nachweis waren Zierde.** `PROVENANCE.md` fuehrt
  je Datei einen SHA-256 — um genau einen Fall zu fangen: eine Aufzeichnung,
  die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort ist
  wieder eine erfundene, und von aussen ist ihr das nicht anzusehen.
  Nachgerechnet hat sie kein Test. `test_die_pruefsumme_im_nachweis_stimmt`
  tut es jetzt, ueber die Bytes auf der Platte statt ueber den Loader — genau
  die hat der Recorder gehasht.

- **Recorded fixtures instead of hand-written success responses.**
  `tests/fixtures/` now holds 46 real responses, recorded with
  `scripts/record_fixtures.py` at the seam where the server receives them — an
  httpx response hook on the shared client from `server._get_client()`, so the
  recording carries the same User-Agent, timeout and pool limits as production.
  Origin, key, selection rule, size and SHA-256 are listed per file in
  `tests/fixtures/PROVENANCE.md`; loaded through `tests/fixture_data.py`, driven
  in `tests/test_recorded_fixtures.py` (67 new tests, coverage 80% → 88%).

  One recording per **query**, not per endpoint: `hn_top_stories` fetches an ID
  list and then each story on its own, `hn_discussion` walks the comment tree,
  `tech_signal_digest` fans out over every source at once with `asyncio.gather`.
  Replay therefore dispatches by request and never by order — an order-based
  dispatcher would be right only by accident here.

  The hand-written respx stubs in `tests/test_server.py` stay: they cover the
  error paths — timeout, 5xx, empty result list — which cannot be recorded on
  demand and are fine as inventions.

  Two things this surfaced, both recorded in `CLAUDE.md`: `hn_search` writes a
  live `int(time.time())` into its URL, so a recording's key changes every
  second (the tests stop the clock at the recording moment and derive it back
  out of the key); and the recorder folds identical requests together, so
  `hn_discussion_1.json` is already a comment — the story sits under its
  `hn_top` name.

- **`ruff check` / `ruff format --check` now also cover `scripts`.** The
  directory did not exist before the recorder; an unchecked directory only
  becomes visible once something is in it.

### Known gap

- **`github_trending_ai` has no recorded response.**
  `api.github.com/search/repositories` answers HTTP 403 from the recording
  environment — `sessions are bound to their configured repositories`. What is
  blocked is the **path**, not the host and not the authentication: the same 403
  comes back with and without a token, carries no `Server` header and no
  `x-github-request-id`, and its `documentation_url` points at
  `docs.anthropic.com` — the request never reaches GitHub. A `GITHUB_TOKEN`
  therefore changes nothing; what it takes is an environment without that path
  restriction, since an account-wide search cannot be expressed as
  `repos/{owner}/{repo}/…`. Recording an error response as a fixture would pass
  it off as what the source normally says, so the path keeps its hand-written
  stubs. The reason is stated as `NICHT_VON_HIER` in the recorder and held in
  place by `test_die_gesperrte_quelle_steht_begruendet_im_recorder`;
  `test_der_digest_haelt_den_ausfall_einer_quelle_aus` checks that the digest
  reports the source as degraded and still delivers the other three.

### Fixed

- **The recorder no longer carried the blocked call at all, so an environment
  with access would not have recorded it either.** `github_trending_ai` had been
  dropped from `PLAN` along with its recording — the gap stayed documented while
  the thing that would close it was gone, and `NICHT_VON_HIER`'s promise that
  "the same run records it there without further ado" was true of no run at all.
  The call is back in the plan, and
  `test_der_recorder_faehrt_die_gesperrte_quelle_trotzdem_an` holds it there;
  `test_jeder_aufruf_ohne_aufzeichnung_ist_als_gesperrt_begruendet` catches the
  next call that ends up without a recording and without a reason.

  Putting it back needed the skip that was missing: the tool reports a rejected
  request as an ordinary error string, which the recorder read as a reason to
  retry — four attempts, 2 + 4 + 8 seconds of backoff, and then a `raise` that
  took the rest of the plan with it. A response carrying the `GESPERRT`
  signature, with nothing usable recorded alongside it, now raises
  `PfadGesperrtError`; the run skips that one call, prints the documented reason
  and carries on. The distinction is narrow on purpose — a 403 *without* that
  signature still goes through the full backoff, because a source that closes
  once must not end up permanently unrecorded.

  The backoff sleep now hangs on the module alias `_sleep`. Patching
  `asyncio.sleep` itself reaches into the foreign module and defuses the
  mechanism process-wide, so a test doing that could not refute the assurance it
  claims to check. With the alias it can: removing the skip makes the run really
  wait, and the suite goes from 1.5 s to 15 s.

- **`tech_signal_digest` was broken for every caller, and had been for a
  while.** It asked GitHub for
  `topic:llm OR topic:ai-agents OR topic:mcp stars:>=100`; GitHub answers that
  form with **HTTP 422**, while the single-topic form used by
  `github_trending_ai` is accepted. The digest now runs one search per topic
  and merges the hits, collapsing duplicates on `full_name`. Topics that fail
  are named in `incomplete_topics` rather than quietly shortening the list —
  a repo count says nothing about how many topics were actually asked.
- **One dead source took the other three with it.** A single raise inside the
  `asyncio.gather` turned the whole digest into an error string, so a GitHub
  outage also cost the caller HackerNews, arXiv and Lobste.rs. Sources are now
  collected independently: a source that cannot be reached appears with
  `count: 0` and an `error`, and its key is listed in the new
  `degraded_sources`. Only a total outage still returns a plain error string.
  A degraded digest is not cached — it would outlive the outage it describes.

  Both defects were found by the scheduled live run the day it was added, not
  by the unit tests, which were green throughout. `ci.yml` deselects the live
  tests with `-m "not live"`, so nothing exercised the digest's real query
  until `live-sources.yml` started running on a schedule.

- **The retry had six defects, all inherited from the shared template.** This
  server copied its retry from `reference/retry_backoff.py` in
  [mcp-data-source-probe-skill](https://github.com/malkreide/mcp-data-source-probe-skill),
  and the template shipped these until 2026-08-07. A sweep across eleven
  servers found that none read `Retry-After` and none jittered — one template,
  eleven copies, not eleven independent omissions.
  1. **No jitter.** The ladder was deterministic, so every client that hit the
     same outage retried in lockstep and the load returned as a wave exactly
     when the source recovered — the retry storm extending the outage it was
     meant to bridge. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap now binds *after* the jitter.
     `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
     and a jitter; only the second is bounded — 20s times 1.5 is 30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call,
     and an attempt count never says so. Now 25s for the whole call, anchored
     on the MCP SDK's `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.timeout` wall-clock
     deadline rather than an httpx timeout: httpx bounds each *operation*, and
     its read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring.
  6. **Point six did not apply here.** `_request_with_retry` already ended in
     `raise last_error` rather than wrapping — the caller keeps the exception
     type and `.response`. The debug line did interpolate the exception alone,
     though, and `httpx.ConnectTimeout`, `ReadTimeout` and `ConnectError` carry
     an **empty** `str()`; it now names the type too. A new
     `UpstreamUnavailableError` covers the one case with no original exception:
     the budget spent before a request went out.

  **The jitter matters more here than elsewhere.** A single tool call fans out
  to as many as `HN_MAX_CONCURRENCY = 12` concurrent item requests. Without
  jitter, a rate-limited burst retried in lockstep and arrived back as one wave
  — the shape the upstream sees as a second burst.

  New `tests/test_retry_policy.py`: `Retry-After` in both forms plus the
  refusal cases, the jitter spread, that the cap binds after jittering, and the
  one-sided `Retry-After` jitter.

## [0.4.1] — 2026-08-02

Follows `0.4.0` by twelve minutes. The `v0.4.0` tag was cut from `main` before
the fix below landed, so the published `0.4.0` artefact reports a version it is
not — harmless to callers, but wrong in every request it makes. Everything the
`0.4.0` section describes applies here unchanged; this release adds only the
fix below.

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
