"""Spec `2026-07-28`, gemessen statt aus SDK-Konstanten geschlossen.

`test_protocol_version.py` pinnt, welche Revisionen das SDK *nennt*. Ob dieser
Server sie auch *spricht*, sagt eine Konstante nicht — die Zusicherungen hier
gehen deshalb durch eine echte Verbindung, auf zwei Wegen:

* **In-Process** ueber `mcp.Client` mit festem `mode`: `"2026-07-28"` adoptiert
  die moderne Aera direkt, `"legacy"` faehrt den `initialize`-Handshake, `"auto"`
  probt mit `server/discover` und faellt erst dann zurueck.
* **HTTP** ueber die ASGI-App aus `streamable_http_app()`: ein einzelner POST
  ohne `initialize` und ohne `Mcp-Session-Id` — die Drahtform, die
  `2026-07-28` ausmacht. Der In-Process-Weg umgeht genau diese Schicht
  (Routing-Header, Sessionlosigkeit), er kann sie nicht belegen.

Die Negativkontrollen stehen jeweils daneben: ein POST mit der Handshake-Version
braucht weiterhin eine Session, ein falscher `Mcp-Method`-Header wird abgewiesen.
Ohne sie waere «200» auch dann gruen, wenn der Server jede Anfrage durchwinkt.
"""

from __future__ import annotations

import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
import respx
from mcp import Client
from mcp.shared.exceptions import MCPDeprecationWarning
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION

from hn_tech_signal_mcp import __version__
from hn_tech_signal_mcp import server as srv
from hn_tech_signal_mcp.server import LIST_CACHE_TTL_MS
from hn_tech_signal_mcp.server import server as mcp
from tests.fixture_data import fixture_json

MODERN = "2026-07-28"
HANDSHAKE = "2025-11-25"
EXPECTED_TOOLS = 8

SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientInfo": {"name": "test_modern_era", "version": "0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def _stub_lobsters() -> None:
    """Aufgezeichnete Lobste.rs-Antwort; der Cache wird geleert, sonst beantwortet
    ein frueherer Test den Aufruf und der Werkzeugkoerper laeuft gar nicht."""
    srv._cache.clear()
    respx.get(f"{srv.LOBSTERS_BASE_URL}/hottest.json").mock(
        return_value=httpx.Response(200, json=fixture_json("lobsters_1.json"))
    )


def test_die_gemessenen_revisionen_sind_die_des_sdk() -> None:
    """Verbindet die Messung unten mit dem Konstanten-Pin nebenan: Zieht ein
    SDK-Bump die Revisionen weiter, faellt es hier und dort zugleich — nicht
    hier still gruen, weil die Tests eine alte Zahl wiederholen."""
    assert LATEST_MODERN_VERSION == MODERN
    assert LATEST_HANDSHAKE_VERSION == HANDSHAKE


# ---------------------------------------------------------------------------
# In-Process
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expected"),
    [(MODERN, MODERN), ("auto", MODERN), ("legacy", HANDSHAKE)],
)
async def test_jede_aera_wird_ausgehandelt(mode: str, expected: str) -> None:
    """`auto` gehoert dazu: so verbindet ein Client, der nichts festlegt. Landet
    er auf dem Handshake, spricht der Server die moderne Aera nur auf
    ausdrueckliches Verlangen — also praktisch nie."""
    async with Client(mcp, mode=mode) as client:
        assert client.protocol_version == expected
        tools = await client.list_tools()
    assert len(tools.tools) == EXPECTED_TOOLS


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_der_server_nennt_seine_version(mode: str) -> None:
    """Das SDK defaultet `version` auf "". Bis zu dieser Aenderung stand genau
    das auf jeder Antwort — in der modernen Aera sogar im `_meta` jeder
    einzelnen, nicht nur einmal im Handshake.

    `auto` statt `"2026-07-28"`: der feste Modus adoptiert die Aera ohne
    `server/discover` und liest den Stempel deshalb nirgends. Dass `auto` modern
    landet, sichert `test_jede_aera_wird_ausgehandelt`; den Stempel auf dem
    Draht die HTTP-Tests unten."""
    async with Client(mcp, mode=mode) as client:
        info = client.server_info
    assert info is not None
    assert info.version == __version__
    assert info.name == "hn_tech_signal_mcp"


@pytest.mark.asyncio
@respx.mock
async def test_die_moderne_aera_nutzt_nichts_abgekuendigtes() -> None:
    """SEP-2577 kuendigt Sampling, Roots und Logging mit `2026-07-28` ab; das
    SDK meldet jeden Gebrauch als `MCPDeprecationWarning`. Ein ganzer Umlauf —
    Discover, Auflisten, Aufruf — darf keine davon ausloesen.

    Der Aufruf muss den Werkzeugkoerper erreichen: mit ungueltigen Argumenten
    endet er schon in der Validierung, und der Test bliebe gruen, was immer das
    Werkzeug selbst taete. Genau so stand er in der ersten Fassung da."""
    _stub_lobsters()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        async with Client(mcp) as client:
            assert client.protocol_version == MODERN
            await client.list_tools()
            result = await client.call_tool("lobsters_hot", {"params": {"limit": 1}})
    assert not result.is_error
    deprecated = [w for w in caught if isinstance(w.message, MCPDeprecationWarning)]
    assert not deprecated, [str(w.message) for w in deprecated]


@pytest.mark.asyncio
async def test_die_beworbenen_leeren_flaechen_sind_leer() -> None:
    """Befund, SDK-seitig: `MCPServer` registriert Ressourcen- und
    Prompt-Handler immer, und in der modernen Aera bewirbt `server/discover`
    dafuer `listChanged` und `subscribe`. Dieser Server hat weder das eine noch
    das andere. Wegzuschalten ist es nur ueber private Attribute — also wird
    zugesichert, was ein Client dort vorfindet: nichts, und keinen Fehler."""
    async with Client(mcp) as client:  # `auto`: nur Discover liefert Capabilities
        assert client.protocol_version == MODERN
        caps = client.server_capabilities
        resources = await client.list_resources()
        prompts = await client.list_prompts()
    assert caps.tools is not None
    assert resources.resources == []
    assert prompts.prompts == []


@pytest.mark.asyncio
@respx.mock
async def test_ein_werkzeugaufruf_laeuft_modern_durch() -> None:
    """Ein echter Aufruf mit aufgezeichneter Antwort, nicht nur das Verzeichnis:
    `tools/call` ist in `2026-07-28` die Methode, die `requestState` und
    `InputRequiredResult` kennt — hier muss sie schlicht `complete` liefern."""
    _stub_lobsters()
    async with Client(mcp, mode=MODERN) as client:
        result = await client.call_tool("lobsters_hot", {"params": {"limit": 2}})
    assert not result.is_error
    assert '"count": 2' in result.content[0].text


# ---------------------------------------------------------------------------
# HTTP: ein Request, eine Antwort
# ---------------------------------------------------------------------------


def _headers(method: str, version: str = MODERN, **extra: str) -> dict[str, str]:
    return {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": version,
        "mcp-method": method,
        **extra,
    }


def _body(req_id: int, method: str, **params: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": {**params, "_meta": META},
    }


@asynccontextmanager
async def _http() -> AsyncIterator[httpx.AsyncClient]:
    """Die ASGI-App, die `main()` fuer `MCP_TRANSPORT=streamable_http` startet.

    Der Session-Manager muss laufen, sonst beantwortet die App gar nichts;
    `run()` darf je Manager nur einmal, und `streamable_http_app()` legt bei
    jedem Aufruf einen neuen an — deshalb eine frische App je Test.
    `127.0.0.1` als Host, weil der DNS-Rebinding-Schutz fremde Hosts abweist.

    Ein Kontextmanager im Test statt eines async Fixtures: pytest-asyncio
    baut Fixtures in einer anderen Task ab, als es sie aufgebaut hat, und die
    Task-Gruppe des Session-Managers verweigert genau das.
    """
    app = mcp.streamable_http_app()
    async with mcp.session_manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as c:
            yield c


async def _post(body: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    """Ein POST, eine Antwort — je Aufruf eine eigene App."""
    async with _http() as http:
        return await http.post("/mcp", json=body, headers=headers)


@pytest.mark.asyncio
async def test_http_discover_ohne_handshake() -> None:
    resp = await _post(_body(1, "server/discover"), _headers("server/discover"))
    assert resp.status_code == 200
    assert "mcp-session-id" not in resp.headers, "2026-07-28 kennt keine Session"
    result = resp.json()["result"]
    assert MODERN in result["supportedVersions"]
    assert result["ttlMs"] == LIST_CACHE_TTL_MS
    assert result["_meta"][SERVER_INFO_KEY]["version"] == __version__


@pytest.mark.asyncio
async def test_http_tools_list_ohne_session() -> None:
    resp = await _post(_body(2, "tools/list"), _headers("tools/list"))
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert len(result["tools"]) == EXPECTED_TOOLS
    assert result["cacheScope"] == "public"
    assert result["_meta"][SERVER_INFO_KEY]["version"] == __version__


@pytest.mark.asyncio
async def test_http_tools_call_traegt_den_namen_im_header() -> None:
    """`Mcp-Name` muss dem `name` im Body entsprechen. Ein unbekanntes Werkzeug
    ist dann kein Protokollfehler, sondern ein Werkzeugfehler: `isError`."""
    resp = await _post(
        _body(3, "tools/call", name="gibt_es_nicht", arguments={}),
        _headers("tools/call", **{"mcp-name": "gibt_es_nicht"}),
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["isError"] is True


@pytest.mark.asyncio
async def test_http_falscher_methodenheader_wird_abgewiesen() -> None:
    """Negativkontrolle zu den 200ern oben: ohne sie waeren die auch gruen,
    wenn die Routing-Header gar nicht gelesen wuerden."""
    resp = await _post(_body(4, "tools/list"), _headers("server/discover"))
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == -32020  # HEADER_MISMATCH


@pytest.mark.asyncio
async def test_http_handshake_aera_braucht_weiter_eine_session() -> None:
    """Die Gegenseite: dieselbe Anfrage unter `2025-11-25` ist ohne
    `initialize` nicht zulaessig. Faellt das, ist die Sessionlosigkeit oben kein
    Merkmal der modernen Aera mehr, sondern eine Luecke im Legacy-Pfad."""
    resp = await _post(_body(5, "tools/list"), _headers("tools/list", version=HANDSHAKE))
    assert resp.status_code == 400
    assert "session" in resp.json()["error"]["message"].lower()
