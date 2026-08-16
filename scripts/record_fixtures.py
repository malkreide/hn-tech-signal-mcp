#!/usr/bin/env python3
"""Zeichnet je eine echte Antwort pro Abfrage auf.

Warum nicht von Hand geschrieben: eine handgeschriebene Erfolgs-Antwort stimmt
mit dem ueberein, was ihr Autor annahm, und kann die Quelle deshalb nicht
widerlegen. Aufgezeichnet wird darum an demselben Ort, an dem der Server die
Antwort entgegennimmt — ueber einen httpx-Response-Hook auf dem geteilten
Client aus `server._get_client()`. Damit tragen Aufzeichnung und Betrieb
denselben User-Agent, dasselbe Timeout und dieselben Pool-Grenzen.

Fuenf Quellen, aber viele Abfrageformen: `hn_top_stories` holt erst eine
Liste von IDs und dann jede Story einzeln, `hn_discussion` steigt den
Kommentarbaum hinab, `tech_signal_digest` faechert ueber alle Quellen zugleich
auf. Die Portfolio-Regel «eine Antwort je externem Endpunkt» waere mit fuenf
Dateien erfuellt und truege fast nichts.

Zugeordnet wird beim Abspielen nach der Anfrage und nicht nach der Reihenfolge:
`tech_signal_digest` startet seine Abrufe mit `asyncio.gather`, und die
Reihenfolge, in der sie zurueckkommen, ist keine Zusicherung.

## Aufruf

    PYTHONPATH=src python scripts/record_fixtures.py

Schreibt nach `tests/fixtures/` und erzeugt `tests/fixtures/PROVENANCE.md` neu.
Dateien, die kein Plan-Eintrag mehr erzeugt, werden geloescht — sonst waechst
der Ordner und der Nachweis bleibt zurueck.

`GITHUB_TOKEN` wird, wenn gesetzt, vom Server als `Authorization`-Header
mitgeschickt. Aufgezeichnet wird nur die *Antwort*; der Header steht in keiner
Datei und in keinem Schluessel.

Weist die Umgebung einen Pfad ab, bevor die Quelle ihn sieht (siehe `GESPERRT`),
wird dieser eine Aufruf uebersprungen und der Grund gemeldet — der Lauf bricht
nicht ab. So bleibt der Aufruf im Plan stehen, und eine Umgebung ohne die Sperre
zeichnet ihn ohne Zutun mit auf.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from hn_tech_signal_mcp import server  # noqa: E402

FIXTURES = WURZEL / "tests" / "fixtures"

VERSUCHE = 4

# Der Backoff-Schlaf unter eigenem Namen. Ein Test, der `asyncio.sleep` selbst
# patcht, greift ins fremde Modul und entschaerft die Mechanik im ganzen
# Prozess; ueber den Alias trifft er genau diese Schleife.
_sleep = asyncio.sleep

# Wie viele Eintraege einer Trefferliste bleiben. Die Form einer Zeile belegen
# drei genauso gut wie hundert; die Zahl steht je Datei im Nachweis.
ZEILEN = 3


@dataclass(frozen=True)
class Aufruf:
    """Ein Werkzeugaufruf, der Anfragen ausloesen soll."""

    name: str
    werkzeug: str
    klasse: str
    eingabe: dict[str, Any]
    # Kuerzen ist nur dort harmlos, wo der Server die Liste ganz liest. Sucht
    # er *in* ihr — oder holt er zu jedem Eintrag eine weitere Antwort —, dann
    # schneidet ein Schnitt womoeglich genau die Zeile weg, die er braucht.
    kuerzen: bool = True
    notiz: str = ""


# Die Eingaben sind bewusst klein gehalten: `limit=3` statt der Standard-10.
# Jede Story, jeder Kommentar ist eine eigene Anfrage und damit eine eigene
# Datei — bei den Standardwerten waere der Ordner ein Archiv statt eines
# Belegs. Die Form einer Antwort belegen drei Abrufe so gut wie dreissig.
PLAN: list[Aufruf] = [
    Aufruf(
        "hn_top",
        "hn_top_stories",
        "HnTopStoriesInput",
        {"feed": "top", "limit": 3},
        # Die ID-Liste darf nicht gekuerzt werden: der Server holt zu den
        # ersten `limit` IDs je eine Story. Ein Schnitt auf drei Eintraege
        # waere hier zufaellig richtig und beim naechsten `limit` falsch.
        kuerzen=False,
        notiz="Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.",
    ),
    Aufruf(
        "hn_search",
        "hn_search",
        "HnSearchInput",
        {"query": "rust", "limit": 3, "days_back": 30},
    ),
    Aufruf(
        "hn_discussion",
        "hn_discussion",
        "HnDiscussionInput",
        # Die Story-ID setzt `main()` zur Laufzeit — eine feste ID waere in
        # ein paar Wochen ein toter Verweis.
        {"story_id": 0, "max_depth": 1},
        kuerzen=False,
        notiz="Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.",
    ),
    Aufruf("arxiv_latest", "arxiv_latest", "ArxivLatestInput", {"limit": 3}),
    Aufruf(
        "arxiv_search",
        "arxiv_search",
        "ArxivSearchInput",
        {"query": "retrieval augmented generation", "limit": 3},
    ),
    Aufruf("lobsters", "lobsters_hot", "LobstersHotInput", {"limit": 3}),
    Aufruf(
        "github",
        "github_trending_ai",
        "GithubTrendingAiInput",
        {"topic": "llm", "limit": 3, "min_stars": 100},
        notiz="Steht im Plan, damit eine Umgebung ohne Pfad-Sperre ihn ohne Zutun mitnimmt.",
    ),
    Aufruf(
        "digest",
        "tech_signal_digest",
        "TechSignalDigestInput",
        {"hn_limit": 3, "arxiv_limit": 3, "lobsters_limit": 3},
        kuerzen=False,
        notiz="Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.",
    ),
]


#: Die Signatur, an der eine gesperrte Antwort erkennbar ist. Sie stammt nicht
#: von GitHub: der Rumpf traegt keinen `Server`-Header und keine
#: `x-github-request-id`, und die `documentation_url` zeigt auf
#: docs.anthropic.com. Die Anfrage hat GitHub also nie erreicht.
GESPERRT = "sessions are bound to their configured repositories"

# Was sich aus mancher Umgebung nicht aufzeichnen laesst, und warum. Die
# Begruendung gehoert in den Code und nicht bloss in eine Commit-Nachricht:
# sonst liest der naechste Blick den fehlenden Eintrag als Versehen.
NICHT_VON_HIER = {
    "github_trending_ai": (
        "api.github.com/search/repositories antwortet in manchen Umgebungen mit "
        "HTTP 403 «sessions are bound to their configured repositories». Gesperrt "
        "ist der *Pfad*, nicht der Host und nicht die Authentisierung: dieselbe "
        "403 kommt mit und ohne Token, ohne `Server`-Header und ohne "
        "`x-github-request-id` — die Anfrage erreicht GitHub nie. Ein eigenes "
        "GITHUB_TOKEN aendert daran nichts; noetig ist eine Umgebung ohne diese "
        "Pfad-Beschraenkung, denn eine account-weite Suche laesst sich nicht als "
        "`repos/{owner}/{repo}/...` ausdruecken. Dort zeichnet derselbe Lauf sie "
        "ohne Zutun mit auf. Bis dahin bleibt der Pfad bei handgeschriebenen "
        "Stubs, und `test_der_digest_haelt_den_ausfall_einer_quelle_aus` prueft, "
        "dass der Digest ohne diese Quelle weiterlaeuft statt umzufallen."
    ),
}


def schluessel_fuer(request: httpx.Request) -> str:
    """Woran eine Anfrage beim Abspielen wiedererkannt wird.

    Die Abfrage steht bei allen fuenf Quellen im Query-String, nicht im Rumpf;
    die volle URL genuegt deshalb. Der Hostname bleibt drin: `hn_discussion`
    und `hn_top_stories` fragen denselben Pfad `/item/<id>.json` mit
    verschiedenen IDs, und `tech_signal_digest` mischt alle Quellen.
    """
    return str(request.url)


def _endung(text: str) -> str:
    """`.json`, wenn die Antwort JSON ist — sonst `.xml`.

    arXiv antwortet mit einem Atom-Feed. Ein Loader, der ueberall JSON
    erwartet, faellt dort ueber die erste Zeile; die Endung sagt es vorher.
    """
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return ".xml"
    return ".json"


@dataclass
class Antwort:
    """Eine gesehene Antwort samt der Anfrage, die sie ausgeloest hat."""

    schluessel: str
    text: str
    werkzeuge: list[str] = field(default_factory=list)
    darf_kuerzen: bool = True
    notiz: str = ""
    dateiname: str = ""
    original_bytes: int = 0
    gekuerzt_von: int = 0
    behalten: int = 0
    sha256: str = ""
    bytes: int = 0


class PfadGesperrtError(RuntimeError):
    """Die Umgebung hat den Pfad abgewiesen, bevor die Quelle ihn sah.

    Kein Retry-Grund und kein Abbruchgrund: der naechste Versuch bekommt
    dieselbe Antwort, und die uebrigen Aufrufe des Plans haben damit nichts zu
    tun. Der Lauf ueberspringt diesen einen Aufruf und sagt, warum.
    """


def _hook_fuer(
    gesehen: list[Antwort], gesperrt: list[str]
) -> Callable[[httpx.Response], Awaitable[None]]:
    """Baut den Response-Hook fuer einen Versuch.

    Eigene Funktion, damit die Listen als Argumente gebunden sind und nicht als
    Schleifenvariablen aus dem umgebenden Namensraum (ruff B023).
    """

    async def hook(response: httpx.Response) -> None:
        await response.aread()
        if response.status_code >= 400:
            # Eine Fehlerantwort als Fixture abzulegen hiesse, sie als das
            # auszugeben, was die Quelle normalerweise sagt. Der Digest laeuft
            # ueber eine Quelle, die aus dieser Umgebung 403 gibt (siehe
            # NICHT_VON_HIER) — die Antwort gehoert nicht in den Ordner.
            if GESPERRT in response.text:
                gesperrt.append(str(response.request.url))
            print(
                f"– nicht aufgezeichnet (HTTP {response.status_code}): {response.request.url}",
                file=sys.stderr,
            )
            return
        gesehen.append(Antwort(schluessel=schluessel_fuer(response.request), text=response.text))

    return hook


async def _fahre(a: Aufruf, client: httpx.AsyncClient) -> list[Antwort]:
    """Ruft ein Werkzeug und gibt die dabei gesehenen Antworten zurueck."""
    fn = getattr(server, a.werkzeug)
    modell = getattr(server, a.klasse)(**a.eingabe)
    letzter: Exception | None = None

    for versuch in range(VERSUCHE):
        if versuch:
            await _sleep(2**versuch)
        gesehen: list[Antwort] = []
        gesperrt: list[str] = []
        hook = _hook_fuer(gesehen, gesperrt)
        client.event_hooks.setdefault("response", []).append(hook)
        try:
            ergebnis = await fn(modell)
        except Exception as e:  # noqa: BLE001 — jeder Fehler ist hier ein Retry-Grund
            letzter = e
            continue
        finally:
            client.event_hooks["response"].remove(hook)

        # Vor der Fehlerpruefung: das Werkzeug meldet eine abgewiesene Anfrage
        # als gewoehnlichen Fehler, und der sieht aus wie ein Retry-Grund. Vier
        # Versuche mit Backoff aendern daran nichts, und der `raise` am Ende
        # riss den ganzen Lauf mit — samt der Aufrufe, die noch ausstanden.
        if gesperrt and not gesehen:
            raise PfadGesperrtError(f"{a.werkzeug}: {gesperrt[0]}")
        text = str(ergebnis)
        if "Error" in text[:200] or "Fehler" in text[:200]:
            letzter = RuntimeError(f"{a.werkzeug} meldet: {text[:200]}")
            continue
        if not gesehen:
            letzter = RuntimeError(f"{a.werkzeug} hat keine Anfrage abgeschickt")
            continue
        for antwort in gesehen:
            antwort.werkzeuge.append(a.werkzeug)
            antwort.darf_kuerzen = a.kuerzen
            antwort.notiz = a.notiz
        return gesehen

    raise RuntimeError(f"{a.name} nach {VERSUCHE} Versuchen nicht aufgezeichnet: {letzter}")


def _kuerze(daten: Any) -> tuple[int, int, Any]:
    """Kuerzt jede Liste im Baum auf `ZEILEN`; gibt (vorher, nachher, Daten).

    Nur die Zahl der Eintraege, nie ein Feld. Zaehlfelder daneben bleiben
    stehen: die Quelle meint damit die Gesamtzahl und nicht die Zahl der
    gelieferten Zeilen, und genau die liest der Server aus.
    """
    vorher = nachher = 0

    def geh(knoten: Any) -> Any:
        nonlocal vorher, nachher
        if isinstance(knoten, dict):
            return {k: geh(v) for k, v in knoten.items()}
        if isinstance(knoten, list):
            vorher += len(knoten)
            gekuerzt = knoten[:ZEILEN]
            nachher += len(gekuerzt)
            return [geh(v) for v in gekuerzt]
        return knoten

    # Erst laufen lassen, dann die Zaehler lesen. `return vorher, nachher,
    # geh(daten)` wertet von links nach rechts aus und lieferte deshalb immer
    # (0, 0) — der Nachweis schriebe «ungekuerzt» ueber jede gekuerzte Datei.
    ergebnis = geh(daten)
    return vorher, nachher, ergebnis


async def _erste_story_id(client: httpx.AsyncClient) -> int:
    """Nimmt die erste ID des Top-Feeds fuer den Diskussions-Abruf.

    Eine fest eingetragene ID waere in ein paar Wochen ein toter Verweis, und
    die Aufzeichnung schwiege darueber.
    """
    r = await client.get(f"{server.HN_BASE_URL}/topstories.json")
    r.raise_for_status()
    ids = r.json()
    if not ids:
        raise RuntimeError("der HN-Top-Feed ist leer")
    return int(ids[0])


async def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(UTC).date().isoformat()
    nach_schluessel: dict[str, Antwort] = {}
    zaehler: dict[str, int] = {}

    client = server._get_client()
    try:
        story_id = await _erste_story_id(client)
        print(f"Story fuer die Diskussion: {story_id}", file=sys.stderr)
        aufrufe = [
            a
            if a.name != "hn_discussion"
            else Aufruf(
                a.name,
                a.werkzeug,
                a.klasse,
                {**a.eingabe, "story_id": story_id},
                a.kuerzen,
                a.notiz,
            )
            for a in PLAN
        ]
        for a in aufrufe:
            print(f"… {a.werkzeug} ({a.name})", file=sys.stderr)
            try:
                antworten = await _fahre(a, client)
            except PfadGesperrtError as e:
                # Uebersprungen, nicht verschwiegen: der Grund steht im Code,
                # und der Lauf sagt ihn noch einmal an der Stelle, an der er
                # greift. Eine Umgebung ohne die Sperre nimmt den Aufruf ohne
                # Zutun mit — deshalb steht er im Plan und nicht daneben.
                print(f"– uebersprungen ({e})", file=sys.stderr)
                print(f"  {NICHT_VON_HIER.get(a.werkzeug, 'ohne Begruendung')}", file=sys.stderr)
                continue
            for antwort in antworten:
                if antwort.schluessel in nach_schluessel:
                    vorhanden = nach_schluessel[antwort.schluessel]
                    if a.werkzeug not in vorhanden.werkzeuge:
                        vorhanden.werkzeuge.append(a.werkzeug)
                    continue
                zaehler[a.name] = zaehler.get(a.name, 0) + 1
                antwort.dateiname = f"{a.name}_{zaehler[a.name]}{_endung(antwort.text)}"
                nach_schluessel[antwort.schluessel] = antwort
    finally:
        await server._aclose_shared_client()

    for antwort in nach_schluessel.values():
        antwort.original_bytes = len(antwort.text.encode("utf-8"))
        try:
            daten = json.loads(antwort.text)
        except json.JSONDecodeError:
            # arXiv antwortet mit einem Atom-Feed — unveraendert ablegen.
            (FIXTURES / antwort.dateiname).write_text(antwort.text, encoding="utf-8")
            roh = (FIXTURES / antwort.dateiname).read_bytes()
            antwort.sha256 = hashlib.sha256(roh).hexdigest()
            antwort.bytes = len(roh)
            continue
        if antwort.darf_kuerzen:
            antwort.gekuerzt_von, antwort.behalten, daten = _kuerze(daten)
        # Neu eingerueckt geschrieben: eine Zeile JSON waere kleiner, aber im
        # Diff nicht lesbar, und ein Fixture will gelesen werden.
        (FIXTURES / antwort.dateiname).write_text(
            json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        roh = (FIXTURES / antwort.dateiname).read_bytes()
        antwort.sha256 = hashlib.sha256(roh).hexdigest()
        antwort.bytes = len(roh)

    antworten = sorted(nach_schluessel.values(), key=lambda x: x.dateiname)
    _schreibe_provenance(antworten, heute)

    # Aufraeumen: was kein Plan-Eintrag mehr erzeugt, hat auch keinen Nachweis.
    geschrieben = {a.dateiname for a in antworten} | {"PROVENANCE.md"}
    for pfad in sorted(FIXTURES.iterdir()):
        if pfad.name not in geschrieben:
            print(f"– entferne veraltet: {pfad.name}", file=sys.stderr)
            pfad.unlink()

    print(f"{len(antworten)} Aufzeichnungen in {FIXTURES}", file=sys.stderr)
    return 0


def _schreibe_provenance(antworten: list[Antwort], heute: str) -> None:
    zeilen = [
        "# Herkunft der Fixtures",
        "",
        f"Aufgezeichnet am **{heute}** mit `PYTHONPATH=src python scripts/record_fixtures.py`.",
        "",
        "Eine Antwort je **Abfrage**, nicht je Endpunkt: `hn_top_stories` holt erst",
        "eine Liste von IDs und dann jede Story einzeln, `hn_discussion` steigt den",
        "Kommentarbaum hinab, `tech_signal_digest` faechert ueber alle Quellen zugleich",
        "auf. Fuenf Dateien wuerden die Portfolio-Regel erfuellen und fast nichts belegen.",
        "",
        "Der **Schluessel** unten ist, woran der Test eine Anfrage wiedererkennt: die",
        "volle URL. Zugeordnet wird nach der Anfrage und nicht nach der Reihenfolge —",
        "`tech_signal_digest` startet seine Abrufe mit `asyncio.gather`, und die",
        "Reihenfolge, in der sie zurueckkommen, ist keine Zusicherung.",
        "",
        "Die Antworten stammen aus dem geteilten Client von `server._get_client()`",
        "(gleicher User-Agent, gleiches Timeout, gleiche Pool-Grenzen wie im Betrieb),",
        "abgegriffen ueber einen httpx-Response-Hook. Ausgeloest hat sie jeweils das",
        "Werkzeug selbst — so belegt die Aufzeichnung auch, dass das Werkzeug genau",
        "diese Anfrage schickt.",
        "",
        "## Auswahl",
        "",
        "Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der",
        "Listeneintraege. Kein Feld eines behaltenen Eintrags ist angetastet, und",
        "Zaehlfelder daneben stehen wie geliefert.",
        "",
        "Wo der Server zu jedem Eintrag einer Liste eine weitere Antwort holt — die",
        "ID-Listen von HackerNews —, wird nicht gekuerzt: ein Schnitt waere fuer das",
        "aufgezeichnete `limit` zufaellig richtig und fuer jedes andere falsch.",
        "",
        "Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.",
        "Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.",
        "",
    ]
    for a in antworten:
        zeilen += [
            f"## `{a.dateiname}`",
            "",
            f"- **Werkzeuge:** {', '.join(f'`{w}`' for w in sorted(a.werkzeuge))}",
            f"- **Schluessel:** `{a.schluessel}`",
        ]
        if a.notiz:
            zeilen.append(f"- **Notiz:** {a.notiz}")
        if a.gekuerzt_von > a.behalten:
            zeilen.append(
                f"- **Auswahl:** {a.behalten} von {a.gekuerzt_von} Listeneintraegen — "
                f"jede Liste im Baum auf die ersten {ZEILEN} gekuerzt, "
                f"aus {a.original_bytes} Bytes Rohantwort"
            )
        elif not a.darf_kuerzen:
            zeilen.append(
                "- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste "
                "weitere Antworten, ein Schnitt liesse ihn ins Leere greifen"
            )
        else:
            zeilen.append("- **Auswahl:** ungekuerzt")
        zeilen += [
            f"- **Groesse:** {a.bytes} Bytes",
            f"- **SHA-256:** `{a.sha256}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(zeilen), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
