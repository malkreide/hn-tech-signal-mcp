# Contributing to hn-tech-signal-mcp

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in contributing! This server is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Getting Started

```bash
git clone https://github.com/malkreide/hn-tech-signal-mcp
cd hn-tech-signal-mcp
pip install -e ".[dev]"
```

## Running Tests

```bash
# Unit tests (no network required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live integration tests (requires network)
PYTHONPATH=src pytest tests/ -m "live"
```

## Code Style

- Python 3.11+, FastMCP, Pydantic v2
- Ruff for linting: `ruff check src/`
- All tools require Pydantic `BaseModel` input validation
- All tools must have comprehensive docstrings

## Adding a New Tool

1. Add a Pydantic input model
2. Implement the tool with `@mcp.tool(name=..., annotations={...})`
3. Add unit tests (mocked HTTP with `respx`) and at least one `@pytest.mark.live` test
4. Update `README.md`, `README.de.md`, and `CHANGELOG.md`

## Pull Requests

- One feature per PR
- All unit tests must pass
- Follow existing code conventions

## The live suite: when it runs, and who sees a red result

**Cadence:** daily at 05:17 UTC, plus on demand via *Actions → Live sources → Run
workflow*. See [`.github/workflows/live-sources.yml`](.github/workflows/live-sources.yml).

**Who sees it:** A red run opens an issue labelled `live-drift` (title: “Live-Quellencheck rot”). A second red run recognises the open issue **by its label**, not by its title, and appends to that same thread. Remove the label by hand and the next red run opens a second issue. Once the suite is green again, the issue closes itself.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about the signal sources (Hacker News, Lobsters, arXiv). Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.
