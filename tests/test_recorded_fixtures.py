"""Jedes Werkzeug, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
Timeout, ein 5xx, eine leere Trefferliste —, die sich nicht auf Zuruf
aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die
Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor
annahm.

Fuenf Quellen, aber viele Abfrageformen: `hn_top_stories` holt erst eine Liste
von IDs und dann jede Story einzeln, `hn_discussion` steigt den Kommentarbaum
hinab, `tech_signal_digest` faechert ueber alle Quellen zugleich auf. Eine
Aufzeichnung je Endpunkt waere mit fuenf Dateien erfuellt und truege fast nichts.

Zugeordnet wird beim Abspielen nach der Anfrage und nicht nach der Reihenfolge:
`tech_signal_digest` startet seine Abrufe mit `asyncio.gather`. Die Reihenfolge,
in der sie zurueckkommen, ist keine Zusicherung — eine Zuordnung nach ihr waere
im gruenen Fall bloss zufaellig richtig.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

import httpx
import pytest
import respx

from hn_tech_signal_mcp import server
from tests.fixture_data import (
    fixture_json,
    fixture_text,
    provenance,
    recorded_names,
    recorder,
    schluessel_fuer,
    schluesselverzeichnis,
)

# Werkzeug → (Eingabeklasse, Eingabe). Bewusst noch einmal hingeschrieben und
# nicht aus dem Recorder-Plan abgeleitet: die Tests sollen eine eigene Aussage
# machen. Dass beide dieselben Aufrufe fahren, prueft
# `test_der_recorder_faehrt_dieselben_aufrufe`.
#
# Die Story-ID der Diskussion steht nicht hier, sondern kommt aus der
# aufgezeichneten ID-Liste — eine feste Zahl waere beim naechsten Aufzeichnen
# ein toter Verweis.
WERKZEUGE: dict[str, tuple[str, str, dict[str, Any]]] = {
    "hn_top": ("hn_top_stories", "HnTopStoriesInput", {"feed": "top", "limit": 3}),
    "hn_search": ("hn_search", "HnSearchInput", {"query": "rust", "limit": 3, "days_back": 30}),
    "arxiv_latest": ("arxiv_latest", "ArxivLatestInput", {"limit": 3}),
    "arxiv_search": (
        "arxiv_search",
        "ArxivSearchInput",
        {"query": "retrieval augmented generation", "limit": 3},
    ),
    "lobsters": ("lobsters_hot", "LobstersHotInput", {"limit": 3}),
    "digest": (
        "tech_signal_digest",
        "TechSignalDigestInput",
        {"hn_limit": 3, "arxiv_limit": 3, "lobsters_limit": 3},
    ),
}

# Die Antwort, die `api.github.com/search/repositories` aus der
# Aufnahmeumgebung gab. Sie steht hier und nicht im Fixture-Ordner: eine
# Fehlerantwort als Aufzeichnung abzulegen hiesse, sie als das auszugeben, was
# die Quelle normalerweise sagt. Der Grund steht in `NICHT_VON_HIER` im
# Recorder.
GITHUB_403 = {
    "message": (
        "This GitHub API path is not available: sessions are bound to their "
        "configured repositories."
    )
}


@pytest.fixture(autouse=True)
def _leerer_cache():
    """Ohne das beantwortet der Prozess-Cache den zweiten Aufruf ohne Anfrage.

    Der Server haelt seine Antworten in einem modulweiten `OrderedDict`. Ein
    Test, der danach `assert protokoll` schreibt, prueft dann die Reihenfolge
    der Tests statt das Werkzeug.
    """
    server._cache.clear()
    yield
    server._cache.clear()


@pytest.fixture
def quelle():
    """Beantwortet jede Anfrage aus ihrer eigenen Aufzeichnung und protokolliert mit.

    Nach der *Anfrage* zugeordnet, nicht nach der Reihenfolge: der Digest
    startet seine Abrufe nebenlaeufig. Eine Anfrage ohne Aufzeichnung faellt
    hier laut auf, statt still eine fremde Datei zu bekommen — mit der einen
    dokumentierten Ausnahme der GitHub-Suche.
    """
    protokoll: list[httpx.Request] = []
    verzeichnis = schluesselverzeichnis()

    def antwort(request: httpx.Request) -> httpx.Response:
        protokoll.append(request)
        schluessel = schluessel_fuer(request)
        name = verzeichnis.get(schluessel)
        if name is None:
            if schluessel.startswith(server.GITHUB_BASE_URL):
                return httpx.Response(403, json=GITHUB_403)
            raise AssertionError(
                f"keine Aufzeichnung fuer diese Anfrage:\n  {schluessel}\n"
                "Neu aufzeichnen mit `PYTHONPATH=src python scripts/record_fixtures.py`."
            )
        return httpx.Response(200, text=fixture_text(name))

    with respx.mock:
        respx.route().mock(side_effect=antwort)
        yield protokoll


@pytest.fixture
def aufnahmezeitpunkt(monkeypatch):
    """Haelt die Uhr auf der Sekunde an, in der `hn_search` aufgezeichnet wurde.

    `hn_search` rechnet `int(time.time()) - days_back * 86400` und schreibt das
    Ergebnis als `numericFilters` in die URL. Der Schluessel einer Aufzeichnung
    aendert sich damit **jede Sekunde** — ohne angehaltene Uhr trifft er nach
    dem Aufzeichnen nie wieder zu.

    Der Zeitpunkt steht nicht als Zahl im Test, sondern wird aus dem Schluessel
    zurueckgerechnet: `cutoff + days_back * 86400`. Beim naechsten Aufzeichnen
    zieht er von selbst mit; eine hier eingetragene Zahl waere dann still
    falsch.
    """
    _, _, eingabe = WERKZEUGE["hn_search"]
    for schluessel in schluesselverzeichnis():
        treffer = re.search(r"created_at_i%3E(\d+)", schluessel)
        if treffer:
            wann = int(treffer.group(1)) + eingabe["days_back"] * 86400
            monkeypatch.setattr(server.time, "time", lambda: float(wann))
            return wann
    raise AssertionError("keine Aufzeichnung mit Zeitfenster im Nachweis gefunden")


def _story_id_aus_der_aufzeichnung() -> int:
    """Die Story, deren Kommentare mit aufgezeichnet sind.

    Der Recorder setzt die ID zur Laufzeit auf die erste des Top-Feeds; sie hier
    noch einmal hinzuschreiben hiesse, sie beim naechsten Aufzeichnen zu
    vergessen. Am Dateinamen ablesen laesst sie sich auch nicht: der Recorder
    fasst gleiche Anfragen zusammen, und die Story lag schon unter ihrem
    `hn_top`-Namen im Ordner, als die Diskussion sie holte —
    `hn_discussion_1.json` ist deshalb bereits ein Kommentar.

    Gesucht wird darum nach der Sache selbst: eine Story, deren `kids` als
    eigene Aufzeichnungen vorliegen. Genau das macht sie zu der einen, deren
    Kommentarbaum sich hier abspielen laesst.
    """
    nach_id = {
        int(treffer.group(1)): datei
        for schluessel, datei in schluesselverzeichnis().items()
        if (treffer := re.search(r"/item/(\d+)\.json$", schluessel))
    }
    for item_id, datei in sorted(nach_id.items()):
        daten = fixture_json(datei)
        kinder = daten.get("kids") or []
        if daten.get("type") == "story" and kinder and set(kinder[:3]) <= set(nach_id):
            return item_id
    raise AssertionError("keine Story mit aufgezeichneten Kommentaren im Nachweis gefunden")


async def _fahre(name: str) -> str:
    """Ruft ein Werkzeug mit der Eingabe aus der Tabelle."""
    werkzeug, klasse, eingabe = WERKZEUGE[name]
    return await getattr(server, werkzeug)(getattr(server, klasse)(**eingabe))


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------
def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    treffer = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert treffer, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    wann = dt.date.fromisoformat(treffer.group(1))
    assert wann <= dt.datetime.now(dt.UTC).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_schluessel_zeigt_auf_eine_vorhandene_datei():
    """Der Nachweis traegt hier den Abspielbetrieb — er darf nicht ins Leere zeigen."""
    fehlend = sorted(set(schluesselverzeichnis().values()) - set(recorded_names()))
    assert not fehlend, f"im Nachweis genannt, aber nicht vorhanden: {fehlend}"


def test_keine_aufzeichnung_liegt_unbenutzt_herum():
    """Die Gegenrichtung — eine Datei, die kein Schluessel erreicht, belegt nichts."""
    ueberzaehlig = sorted(set(recorded_names()) - set(schluesselverzeichnis().values()))
    assert not ueberzaehlig, f"von keinem Schluessel erreicht: {ueberzaehlig}"


def test_der_recorder_faehrt_dieselben_aufrufe():
    """Recorder und Tests duerfen nicht auseinanderlaufen.

    Laedt `scripts/record_fixtures.py` als Modul — `main()` wird nicht gerufen,
    es geht keine Anfrage raus. Die Diskussion steht in beiden, ihre Story-ID
    kommt in beiden zur Laufzeit dazu.
    """
    im_plan = {a.name for a in recorder().PLAN}
    assert im_plan == set(WERKZEUGE) | {"hn_discussion"}, (
        "Recorder und Testtabelle nennen verschiedene Aufrufe"
    )


def test_die_gesperrte_quelle_steht_begruendet_im_recorder():
    """Ein fehlender Endpunkt ohne Begruendung liest sich als Versehen.

    `github_trending_ai` hat keine Aufzeichnung, weil die Aufnahmeumgebung die
    GitHub-Suche mit 403 abweist — nicht, weil der Pfad vergessen wurde. Die
    Begruendung gehoert in den Code und faellt hier auf, wenn sie verschwindet.
    """
    luecken = recorder().NICHT_VON_HIER
    assert "github_trending_ai" in luecken, "die Luecke ist nicht mehr begruendet"
    assert "403" in luecken["github_trending_ai"]


def test_der_nachweis_meldet_was_gekuerzt_wurde():
    """Ein Nachweis, der ueber jeder Datei «ungekuerzt» schreibt, belegt nichts.

    `_kuerze` gibt seine Zaehler nach dem Lauf zurueck und nicht als
    `return vorher, nachher, geh(daten)` — Python liest die beiden Zahlen sonst,
    *bevor* `geh` sie hochzaehlt, und meldet immer (0, 0).
    """
    modul = recorder()
    vorher, nachher, gekuerzt = modul._kuerze({"a": list(range(modul.ZEILEN * 3))})
    assert (vorher, nachher) == (modul.ZEILEN * 3, modul.ZEILEN), (
        f"_kuerze meldet {vorher}→{nachher} statt {modul.ZEILEN * 3}→{modul.ZEILEN}"
    )
    assert len(gekuerzt["a"]) == modul.ZEILEN
    assert re.search(r"- \*\*Auswahl:\*\* \d+ von \d+ Listeneintraegen", provenance()), (
        "keine einzige Datei im Nachweis ist als gekuerzt ausgewiesen"
    )


@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n.endswith(".json")))
def test_keine_aufzeichnung_ist_leer(name):
    """Eine leere Antwort sieht aus wie eine gueltige und prueft nichts."""
    daten = fixture_json(name)
    assert daten not in ([], {}, None), f"{name} ist leer — neu aufzeichnen"


def test_keine_aufzeichnung_traegt_eine_fehlerantwort():
    """Ein 403 im Ordner gaebe sich als das aus, was die Quelle normalerweise sagt.

    Die GitHub-Suche antwortet aus der Aufnahmeumgebung mit einer
    Fehlermeldung. Der Recorder legt Antworten ab HTTP 400 nicht ab; diese
    Zusicherung haelt fest, dass keine davon doch in den Ordner geraten ist.
    """
    verdacht = [
        n
        for n in recorded_names()
        if n.endswith(".json")
        and isinstance(fixture_json(n), dict)
        and {"message", "documentation_url"} <= set(fixture_json(n))
    ]
    assert not verdacht, f"sieht nach einer GitHub-Fehlerantwort aus: {verdacht}"


# --------------------------------------------------------------------------
# Die Werkzeuge, jedes an seiner eigenen Antwort
# --------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(WERKZEUGE))
async def test_jedes_werkzeug_liest_seine_aufgezeichnete_antwort(quelle, aufnahmezeitpunkt, name):
    """Der eigentliche Punkt: jede Abfrage bekommt *ihre* Antwort.

    Alle mit derselben zu bedienen hiesse, die Aufzeichnung gegen eine Abfrage
    zu halten, die sie nicht beantwortet. Der Dispatcher faellt laut, wenn eine
    Anfrage keine Aufzeichnung hat.
    """
    ergebnis = str(await _fahre(name))
    assert ergebnis.strip(), f"{name} liefert nichts"
    assert not ergebnis.startswith("["), f"{name} meldet einen Fehler: {ergebnis[:200]}"
    assert quelle, f"{name} hat gar keine Anfrage abgeschickt"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(set(WERKZEUGE) - {"arxiv_latest", "arxiv_search"}))
async def test_die_json_werkzeuge_liefern_gefuellte_listen(quelle, aufnahmezeitpunkt, name):
    """«Kommt ohne Fehler zurueck» ist als Zusicherung zu duenn.

    Eine Antwort, in der nichts steht, ist auch fehlerfrei. Geprueft wird
    deshalb, dass die aufgezeichneten Zeilen bis in die Ausgabe durchkommen.
    """
    daten = json.loads(await _fahre(name))
    if name == "digest":
        gefuellt = [k for k, v in daten["sources"].items() if v.get("count", 0) > 0]
        assert len(gefuellt) >= 3, f"nur {gefuellt} tragen Eintraege"
        return
    schluessel = next(k for k in ("stories", "hits", "papers", "repos") if k in daten)
    assert daten[schluessel], f"{name}.{schluessel} ist leer, obwohl die Aufzeichnung Zeilen hat"


@pytest.mark.asyncio
async def test_die_top_stories_holen_zu_jeder_id_eine_eigene_antwort(quelle):
    """Erst die Liste, dann jede Story — der Grund fuer die Zuordnung nach Anfrage.

    Eine Zuordnung nach Reihenfolge waere hier mit hoher Wahrscheinlichkeit
    falsch: die Abrufe laufen nebenlaeufig.
    """
    await _fahre("hn_top")
    pfade = [httpx.URL(str(r.url)).path for r in quelle]
    assert "/v0/topstories.json" in pfade, "die ID-Liste wurde gar nicht geholt"
    einzeln = [p for p in pfade if p.startswith("/v0/item/")]
    assert len(einzeln) >= 3, f"nur {len(einzeln)} Einzelabrufe — die Form hat sich geaendert"
    assert len(set(einzeln)) == len(einzeln), "dieselbe Story zweimal geholt"


@pytest.mark.asyncio
async def test_die_id_liste_steht_ungekuerzt_im_ordner():
    """Gekuerzt griffe der Server bei jedem groesseren `limit` ins Leere."""
    datei = schluesselverzeichnis()[f"{server.HN_BASE_URL}/topstories.json"]
    block = provenance().split(f"## `{datei}`", 1)[1].split("## ", 1)[0]
    assert "ungekuerzt" in block, block
    assert len(fixture_json(datei)) > 3, "die ID-Liste ist doch gekuerzt"


@pytest.mark.asyncio
async def test_die_diskussion_steigt_den_kommentarbaum_hinab(quelle):
    """Ein Kommentar ist eine eigene Anfrage — und `kids` fuehrt zur naechsten."""
    modell = server.HnDiscussionInput(story_id=_story_id_aus_der_aufzeichnung(), max_depth=1)
    daten = json.loads(await server.hn_discussion(modell))
    assert daten.get("comments"), "keine Kommentare in der Ausgabe"
    assert len(quelle) >= 2, f"nur {len(quelle)} Anfrage(n) — Story plus Kommentare erwartet"


def test_arxiv_wird_als_atom_feed_aufgezeichnet():
    """Nicht jede Quelle antwortet mit JSON — arXiv liefert einen Atom-Feed.

    Ein Loader, der ueberall JSON erwartet, faellt dort ueber die erste Zeile;
    die Endung sagt es vorher.
    """
    feeds = [n for n in recorded_names() if n.endswith(".xml")]
    assert feeds, "keine Nicht-JSON-Aufzeichnung — die Form hat sich geaendert"
    text = fixture_text(feeds[0])
    assert "<feed" in text and "<entry>" in text, text[:200]


# --------------------------------------------------------------------------
# Die Gegenrichtung
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_der_digest_haelt_den_ausfall_einer_quelle_aus(quelle):
    """Eine Quelle faellt aus, die anderen drei kommen trotzdem an.

    Die GitHub-Suche antwortet aus dieser Umgebung mit 403 — der Digest muss
    das als *unbekannt* ausweisen und nicht als null Treffer, und die anderen
    Quellen nicht mitreissen.
    """
    daten = json.loads(await _fahre("digest"))
    assert "github" in daten["degraded_sources"], daten["degraded_sources"]
    assert daten["sources"]["github"].get("error"), "der Ausfall steht ohne Grund da"
    for quellname in ("hn", "arxiv", "lobsters"):
        assert daten["sources"][quellname]["count"] > 0, (
            f"{quellname} wurde vom GitHub-Ausfall mitgerissen"
        )


@pytest.mark.asyncio
@respx.mock
async def test_eine_leere_trefferliste_bleibt_eine_leere_trefferliste():
    """`hits: []` ist eine Aussage der Quelle: dazu gibt es nichts.

    Das darf nicht als Fehler herauskommen — sonst kann das Modell einen echten
    Negativtreffer nicht von einem Ausfall unterscheiden.
    """
    respx.route().mock(return_value=httpx.Response(200, json={"hits": []}))
    ergebnis = await _fahre("hn_search")
    daten = json.loads(ergebnis)
    assert daten["hits"] == []
    assert daten["count"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_ein_abbruch_bleibt_ein_fehler(monkeypatch):
    """Und die andere Haelfte: ein Ausfall darf nicht als leeres Ergebnis erscheinen."""
    monkeypatch.setattr(server, "RETRY_BASE_DELAY", 0)
    respx.route().mock(side_effect=httpx.ConnectError("weg"))
    ergebnis = await _fahre("hn_search")
    assert ergebnis.startswith("["), ergebnis[:200]
    assert "Error" in ergebnis, ergebnis[:200]
