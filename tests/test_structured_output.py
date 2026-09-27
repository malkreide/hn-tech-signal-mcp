"""Strukturierte Ausgabe: `outputSchema`, `structuredContent`, `isError`.

Vorher leitete das SDK aus `-> str` ein Schema `{"result": string}` ab. Jedes
Werkzeug versprach damit ein Objekt mit einem Textfeld, in dem der eigentliche
JSON-Text steckte, und jeder Fehler kam mit `isError: false` an.

Die Zusicherungen hier:

* jedes Werkzeug meldet sein eigenes Modell als `outputSchema`, geschlossen
  (`additionalProperties: false`);
* ein Erfolg traegt dasselbe Objekt als Text UND als `structuredContent`;
* ein Fehler traegt `isError: true`, keinen `structuredContent` und im Text
  genau den Envelope, den `_handle_error` baut — daran haengen Live-Tests und
  `scripts/classify_live_run.py`;
* ein teilweise ausgefallener Digest ist KEIN Fehler, ein ganz ausgefallener
  schon.

Die aufgezeichneten Antworten laufen in `test_recorded_fixtures.py` durch
denselben Pfad; hier stehen die Faelle, die sich nicht aufzeichnen lassen.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from mcp import Client

from hn_tech_signal_mcp import outputs
from hn_tech_signal_mcp import server as srv
from hn_tech_signal_mcp.server import _as_call_result
from hn_tech_signal_mcp.server import server as mcp

MODELLE: dict[str, type] = {
    "hn_top_stories": outputs.HnTopStoriesOutput,
    "hn_search": outputs.HnSearchOutput,
    "hn_discussion": outputs.HnDiscussionOutput,
    "arxiv_latest": outputs.ArxivLatestOutput,
    "arxiv_search": outputs.ArxivSearchOutput,
    "lobsters_hot": outputs.LobstersHotOutput,
    "github_trending_ai": outputs.GithubTrendingOutput,
    "tech_signal_digest": outputs.TechSignalDigestOutput,
}

GITHUB_SEARCH = f"{srv.GITHUB_BASE_URL}/search/repositories"


@pytest.fixture(autouse=True)
def _leerer_cache():
    """Ein Treffer im Prozess-Cache beantwortet den Aufruf ohne Anfrage — der
    Stub fuer den Fehlerfall liefe dann nie."""
    srv._cache.clear()
    yield
    srv._cache.clear()


async def _rufe(werkzeug: str, **eingabe: Any) -> Any:
    async with Client(mcp) as client:
        return await client.call_tool(werkzeug, {"params": eingabe})


# ---------------------------------------------------------------------------
# Das Verzeichnis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jedes_werkzeug_meldet_sein_eigenes_schema() -> None:
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}

    assert set(tools) == set(MODELLE), "Werkzeug ohne Modell oder Modell ohne Werkzeug"
    for name, modell in MODELLE.items():
        schema = tools[name].output_schema
        assert schema is not None, f"{name} meldet kein outputSchema"
        assert set(schema["properties"]) != {"result"}, f"{name} meldet noch den Text-Wrapper"
        assert set(schema["properties"]) == set(modell.model_fields), name
        assert schema.get("additionalProperties") is False, f"{name}: Schema ist offen"


@pytest.mark.asyncio
async def test_die_annotationen_ueberleben_den_adapter() -> None:
    """`_tool` reicht die Annotationen als Dict an `ToolAnnotations` weiter; ein
    falscher Schluessel faende sich dort nicht als Fehler, sondern als `None`."""
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    for tool in tools:
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint is True, tool.name
        assert tool.annotations.open_world_hint is True, tool.name
        assert tool.annotations.title, tool.name
        assert tool.description and "Args:" in tool.description, tool.name


def test_die_modulfunktion_bleibt_die_textfunktion() -> None:
    """Der Adapter geht an das SDK, nicht ins Modul. Wer `server.lobsters_hot`
    direkt ruft — Tests, Live-Tests, der Recorder —, bekommt weiter den Text."""
    import inspect

    assert inspect.signature(srv.lobsters_hot).return_annotation in (str, "str")


# ---------------------------------------------------------------------------
# Erfolg
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_github_mit_nullwerten_besteht_das_schema() -> None:
    """GitHub schickt `description` und `language` als `null`, wo nichts
    eingetragen ist — haeufig. `r.get("description", "")` faengt nur den
    fehlenden Schluessel ab, nicht den leeren Wert. Mit strengem `str` im
    Modell waere jedes solche Repo ein gescheiterter Aufruf.

    (GitHub laesst sich aus der Aufnahmeumgebung nicht aufzeichnen, siehe
    `NICHT_VON_HIER` im Recorder — daher hier ein Stub.)"""
    repo = {
        "full_name": "owner/repo",
        "description": None,
        "stargazers_count": 1234,
        "forks_count": 5,
        "language": None,
        "topics": [],
        "updated_at": "2026-09-01T00:00:00Z",
        "html_url": "https://github.com/owner/repo",
    }
    respx.get(GITHUB_SEARCH).mock(
        return_value=httpx.Response(200, json={"total_count": 1, "items": [repo]})
    )
    result = await _rufe("github_trending_ai", topic="llm", limit=1)

    assert not result.is_error, result.content[0].text
    assert result.structured_content["repos"][0]["description"] is None


# ---------------------------------------------------------------------------
# Fehler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_ein_quellenfehler_ist_iserror_mit_unveraendertem_envelope() -> None:
    """404 statt 5xx: der scheitert sofort, ohne Backoff. Der Text muss Wort
    fuer Wort der Envelope aus `_handle_error` sein — die Live-Einordnung
    verankert ihre Pruefung am Zeilenanfang."""
    respx.get(f"{srv.LOBSTERS_BASE_URL}/hottest.json").mock(return_value=httpx.Response(404))
    result = await _rufe("lobsters_hot", limit=1)

    assert result.is_error is True
    assert result.structured_content is None
    assert result.content[0].text == "[Lobste.rs] Error: HTTP 404"


@pytest.mark.asyncio
@respx.mock
async def test_eine_unbekannte_story_ist_iserror() -> None:
    """Die HN-API beantwortet eine unbekannte ID mit 200 und `null`. Der
    Hinweis darauf ist Text, kein Objekt — und damit fuer das Modell ein
    Fehler, den es mit einer anderen ID beheben kann, kein leeres Ergebnis."""
    respx.get(f"{srv.HN_BASE_URL}/item/1.json").mock(return_value=httpx.Response(200, json=None))
    result = await _rufe("hn_discussion", story_id=1)

    assert result.is_error is True
    assert result.content[0].text.startswith("[HackerNews] No item found with ID 1.")


@pytest.mark.asyncio
@respx.mock
async def test_ein_teilweise_ausgefallener_digest_ist_kein_fehler() -> None:
    """Drei Quellen stumm, eine antwortet: das ist ein duenner Digest, kein
    Fehler. Der Ausfall steht IM Objekt — `degraded_sources` und je Quelle
    `error` —, und genau das muss das Schema tragen."""
    respx.route(host="lobste.rs").mock(return_value=httpx.Response(200, json=[{"title": "x"}]))
    respx.route().mock(return_value=httpx.Response(404))
    result = await _rufe("tech_signal_digest")

    assert result.is_error is not True, result.content[0].text[:300]
    daten = result.structured_content
    assert set(daten["degraded_sources"]) == {"hn", "arxiv", "github"}
    assert daten["sources"]["arxiv"]["error"].startswith("[digest.arxiv] Error:")
    assert daten["sources"]["lobsters"]["count"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_ein_ganz_ausgefallener_digest_ist_ein_fehler() -> None:
    respx.route().mock(return_value=httpx.Response(404))
    result = await _rufe("tech_signal_digest")

    assert result.is_error is True
    assert result.structured_content is None
    assert result.content[0].text.startswith("[digest.")


# ---------------------------------------------------------------------------
# Die Unterscheidung selbst
# ---------------------------------------------------------------------------


def test_ein_objekt_ist_ein_erfolg() -> None:
    result = _as_call_result('{"count": 0}')
    assert result.is_error is not True
    assert result.structured_content == {"count": 0}
    assert result.content[0].text == '{"count": 0}'


@pytest.mark.parametrize(
    "text",
    [
        "[arXiv] Error: Request timed out. Try again in a moment.",
        "Error: HTTP 500",
        "[HackerNews] Item 5 is a comment, not a story.",
        # Gueltiges JSON, aber kein Objekt: `structuredContent` MUSS nach Spec
        # ein Objekt sein. Kein Werkzeug liefert so etwas — faengt es eines
        # Tages an, soll es auffallen statt still als Erfolg durchzugehen.
        "[1, 2]",
        "null",
        "",
    ],
)
def test_alles_andere_ist_ein_fehler(text: str) -> None:
    result = _as_call_result(text)
    assert result.is_error is True
    assert result.structured_content is None
    assert result.content[0].text == text


def test_ein_schemaverstoss_nennt_felder_aber_keine_werte() -> None:
    """Passt eine Antwort nicht zum Modell, ist das ein Defekt dieses Servers —
    und kein Ausfall der Quelle. Der Text sagt das, damit das Modell nicht auf
    Wiederholung setzt, und er nennt die Felder, nicht die Werte: die stammen
    von der Quelle und gehoeren nicht in eine Fehlermeldung."""
    text = '{"topic": "llm", "sort": "stars", "fetched_at": "x", "total_found": 1, ' + (
        '"count": 1, "repos": [{"name": "GEHEIMER-WERT", "unerwartet": 1}]}'
    )
    result = _as_call_result(text, outputs.GithubTrendingOutput)

    assert result.is_error is True
    assert result.structured_content is None
    meldung = result.content[0].text
    assert "repos.0.unerwartet" in meldung
    assert "GEHEIMER-WERT" not in meldung
    assert "not a source outage" in meldung
    # Kein Envelope aus `_handle_error`: die Live-Einordnung darf das nicht
    # als stumme Quelle buchen.
    assert not meldung.startswith("[")


def test_ohne_modell_wird_nicht_vorgeprueft() -> None:
    """Gegenstueck: dieselbe Antwort ohne Modell geht durch. Sonst waere oben
    nicht die Vorpruefung gemessen, sondern irgendein anderer Pfad."""
    result = _as_call_result('{"repos": [{"unerwartet": 1}]}')
    assert result.is_error is not True


@pytest.mark.asyncio
@respx.mock
async def test_der_adapter_prueft_vor_statt_dem_sdk_das_wort_zu_lassen(monkeypatch) -> None:
    """Die Vorpruefung durch den echten Pfad: ein Werkzeug, das ein Feld mit
    falschem Typ baut. Reicht `_tool` das Modell nicht an `_as_call_result`
    weiter, faengt erst das SDK den Verstoss — mit seiner eigenen Meldung, und
    dieser Test faellt."""
    monkeypatch.setattr(srv, "_now_iso", lambda: 5)
    respx.get(f"{srv.LOBSTERS_BASE_URL}/hottest.json").mock(
        return_value=httpx.Response(200, json=[{"title": "x"}])
    )
    result = await _rufe("lobsters_hot", limit=1)

    assert result.is_error is True
    assert "(fields: fetched_at)" in result.content[0].text
