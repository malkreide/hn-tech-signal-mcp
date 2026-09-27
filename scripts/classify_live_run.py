#!/usr/bin/env python3
"""Was hat der geplante Live-Lauf festgestellt — clear, finding oder unknown?

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
`if: failure()` kennt zwei Antworten: rot und nicht rot. Ein Live-Lauf hat
drei, und die dritte ist die, die zaehlt:

  clear    Die Suite ist gelaufen und war gruen.
  finding  Die Suite ist gelaufen und etwas ist gefallen.
  unknown  Die Suite ist NICHT gelaufen — und niemand weiss, ob der Vertrag
           mit der Quelle noch haelt.

Ein gescheitertes `pip install`, ein Timeout, eine umbenannte Marke: alles
`unknown`, alles sieht unter `if: failure()` aus wie ein gebrochener Vertrag.
Und ein Lauf, in dem jeder Test uebersprungen wurde, sieht unter jedem
Exit-Code-Check aus wie Erfolg.

Diese Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Sie in einen
`run:`-Block zu schreiben hiesse, den einzigen Teil des Workflows, der etwas
behauptet, an die einzige Stelle zu legen, an der ihn niemand testen kann.
Deshalb steht sie hier, neben ihrem Test.

DER UEBERSPRUNGENE LAUF
-----------------------
Gemessen am 7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY`
ueberspringt die Live-Suite alle sechs Tests, und pytest endet mit 0. Ein
woechentlicher Job haette gemeldet: gruen. Geprueft haette er nichts — und ein
offenes Issue haette er zugemacht, mit einem Vergleich, den es nie gab.

`tests - skipped == 0` ist deshalb `unknown` und nicht `clear`. Ein Secret, das
niemand gesetzt hat, ist kein gruener Vertrag mit der Quelle; es ist gar keiner.

DIE QUELLE IST DAS JUNIT-XML, NICHT DER EXIT-CODE
-------------------------------------------------
Der Exit-Code von pytest sagt 0 fuer «alles gruen» und fuer «alles
uebersprungen» dasselbe. Das XML zaehlt Tests, Fehler, Fehlschlaege und
Uebersprungene getrennt, also wird es gelesen. Fehlt es, ist pytest gar nicht
bis zum Schreiben gekommen — auch das ist `unknown`, und zwar mit Grund.

WENN PYTEST NIE GESTARTET WURDE, IST DER EXIT-CODE EINE ERFINDUNG
-----------------------------------------------------------------
Bricht der Workflow ab, bevor er pytest aufruft — etwa weil ein Secret fehlt —,
dann hat er keinen Exit-Code zu melden. Wer an dieser Stelle einen erfindet,
schickt den Leser hinter einer Ursache her, die es nicht gibt: In
`swiss-ip-mcp` stand dort `--pytest-exit 127`, und diese Einordnung machte
daraus «pytest ist nicht bis zum Schreiben gekommen (Exit 127)» — 127 heisst
«command not found», also die Suche nach einem fehlenden Binary, wo in
Wahrheit nie ein Aufruf stattgefunden hatte.

Deshalb `--not-started`: Wer pytest nicht startet, sagt selbst warum, und diese
Einordnung reicht den Grund durch, statt einen zu konstruieren. Sie sieht dann
auch nicht ins XML — ein liegengebliebener Report aus einem frueheren Schritt
belegt nichts ueber einen Lauf, der nicht stattgefunden hat.

WANN DAS ERGEBNIS DEN JOB ROT MACHT
-----------------------------------
Nicht jeder dieser drei Zustaende ist sofort rot, und das ist der Unterschied
zwischen einem Melder und einer Tapete. `finding` ist sofort rot: Da wurde etwas
gemessen. `unknown` sammelt und wird erst beim dritten Lauf IN FOLGE rot
(`UNKNOWN_RUNS_UNTIL_RED`) — arXiv drosselt nach IP, GitHub-Runner teilen ihre
IPs mit aller Welt, und der Zeitplan lief vom 13. bis 15.9.2026 taeglich rot,
ohne dass an den Quellen etwas war.

Gruen heisst dabei nie «entwarnt»: Der Zustand bleibt `unknown`, und der Schritt
im Workflow, der das Drift-Issue schliesst, haengt unveraendert an `clear`. Die
Serie kommt ueber `--state-in` herein und geht ueber `--state-out` hinaus; der
Workflow hebt sie im Actions-Cache auf. Faellt sie weg, beginnt sie bei 0 — der
Job wird dann spaeter rot, nie frueher, und der Grund steht im Log.

Aufruf:
    python scripts/classify_live_run.py live-report.xml
    python scripts/classify_live_run.py live-report.xml --pytest-exit 1
    python scripts/classify_live_run.py live-report.xml --not-started "kein Secret"
    python scripts/classify_live_run.py live-report.xml \
        --state-in live-state.json --state-out live-state.json

Gibt `state`, `reason`, `red`, `streak` und `red_reason` auf stdout aus und
haengt sie an `$GITHUB_OUTPUT` an, wenn die Variable gesetzt ist. Der Exit-Code
ist immer 0: Ueber rot oder gruen entscheidet der Workflow — aber anhand von
`red`, nicht mehr anhand von `state`.
"""

from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
UNKNOWN = "unknown"

# Das Wort, mit dem ein Live-Test sagt: Die Quelle hat gar nicht geantwortet.
# Gesetzt wird es in `tests/test_server.py` (`_live_json`), gelesen hier —
# `test_marker_stimmt_mit_der_testsuite_ueberein` haelt die beiden Seiten
# zusammen, damit ein Umbenennen auf einer Seite nicht still die Einordnung
# aushebelt.
UNREACHABLE_MARKER = "QUELLE-HAT-NICHT-GEANTWORTET"

# Ab wie vielen `unknown`-Laeufen IN FOLGE der Job rot wird.
#
# Vorher wurde jedes `unknown` sofort rot. Das war inhaltlich richtig und
# praktisch schaedlich: arXiv drosselt nach IP, GitHub-Runner teilen ihre IPs
# mit aller Welt, und der Zeitplan lief drei Tage in Folge rot (13.–15.9.2026),
# ohne dass an den Quellen etwas war. Ein Haken, der taeglich rot steht, wird
# zur Tapete — und mit ihm der naechste, der etwas bedeutet. Das ist dieselbe
# Erosion, die in Teil 2 schon einmal drei rote Tage auf `main` gekostet hat.
#
# Drei ist kein Messwert, sondern eine Wahl: Eine einzelne Drosselung soll
# niemanden wecken, ein Ausfall, der drei Laeufe ueberlebt, schon. Gezaehlt
# werden LAEUFE, nicht Kalendertage — beim taeglichen Zeitplan ist das dasselbe,
# ein zusaetzliches `workflow_dispatch` zaehlt aber mit.
UNKNOWN_RUNS_UNTIL_RED = 3


def _unreachable_failures(suites: list[ET.Element]) -> int:
    """Wie viele `<failure>` tragen das Wort fuer «Quelle hat nicht geantwortet».

    Gezaehlt wird der Marker, nicht das Wort «Timeout». Der Unterschied ist
    der ganze Punkt: Wer hier nach Fehlertexten suchte, wuerde eine echte
    Drift-Zusicherung ueber ein Feld, das zufaellig `timeout` heisst, in ein
    `unknown` verwandeln und damit genau den Befund verschlucken, fuer den
    dieser Melder da ist. Den Marker setzt nur `_live_json`, und nur dann,
    wenn der Server selbst gemeldet hat, dass die Quelle stumm blieb.

    Gelesen werden Attribut UND Text: pytest schreibt die Meldung in beide,
    kuerzt das Attribut aber bei langen Texten.
    """
    count = 0
    for suite in suites:
        for failure in suite.iter("failure"):
            haystack = f"{failure.get('message') or ''}\n{failure.text or ''}"
            if UNREACHABLE_MARKER in haystack:
                count += 1
    return count


def classify(
    report: Path,
    pytest_exit: int | None = None,
    not_started: str | None = None,
) -> tuple[str, str]:
    """(state, reason) aus einem JUnit-XML und optional dem pytest-Exit-Code.

    `not_started` schlaegt alles andere: Wurde pytest nie aufgerufen, sagt
    weder der Report noch ein Exit-Code etwas ueber den Lauf.
    """
    if not_started:
        return UNKNOWN, not_started
    if not report.is_file():
        return (
            UNKNOWN,
            f"kein Report unter {report} — pytest ist nicht bis zum Schreiben "
            "gekommen" + (f" (Exit {pytest_exit})" if pytest_exit is not None else ""),
        )
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        return UNKNOWN, f"{report} ist nicht lesbar: {exc}"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return UNKNOWN, f"{report} enthaelt keine testsuite"

    def total(attr: str) -> int:
        return sum(int(s.get(attr) or 0) for s in suites)

    tests, failures, errors, skipped = (
        total("tests"),
        total("failures"),
        total("errors"),
        total("skipped"),
    )

    if failures or errors:
        # Eine Quelle, die nicht geantwortet hat, sagt nichts ueber ihr Schema.
        # Sie als `finding` zu buchen heisst, Drift zu behaupten, die niemand
        # gesehen hat — am 13.9.2026 genau so passiert: arXiv liess die Anfrage
        # 16 bis 46 Sekunden stehen und antwortete dann mit `429 Rate
        # exceeded.`, das Zeitbudget des Servers lief vorher ab, und der Lauf
        # eroeffnete Issue #68 ueber ein Schema, das unveraendert war.
        #
        # `unknown` laesst den Drift-Thread in Ruhe: weder aufmachen noch
        # zumachen. Ein Melder, der bei jeder Netzstoerung Drift ruft, wird
        # abgeschaltet und schuetzt danach vor gar nichts.
        #
        # Rot wird der Job davon nicht mehr sofort — siehe `entscheide_rot`:
        # erst der dritte `unknown`-Lauf in Folge. Hier stand lange «macht den
        # Job trotzdem rot», und das war nach der Aenderung genau falsch.
        unreachable = _unreachable_failures(suites)
        if errors == 0 and failures and unreachable == failures:
            return (
                UNKNOWN,
                f"alle {failures} Fehlschlag/Fehlschlaege von {tests} Test(s) sind "
                "Quellen, die nicht geantwortet haben — ueber ihr Schema sagt "
                "dieser Lauf nichts",
            )
        return (
            FINDING,
            f"{failures} Fehlschlag/Fehlschlaege und {errors} Fehler von {tests} Test(s)",
        )
    if tests == 0:
        return (
            UNKNOWN,
            "null Tests eingesammelt — die Marke oder die Dateien haben sich "
            "bewegt, und ein Erfolg ohne Test ist kein Erfolg",
        )
    if tests - skipped == 0:
        return (
            UNKNOWN,
            f"alle {tests} Test(s) uebersprungen — meist ein fehlendes Secret oder "
            "eine nicht erfuellte Vorbedingung. Geprueft wurde nichts",
        )
    return CLEAR, f"{tests - skipped} von {tests} Test(s) ausgefuehrt, alle gruen"


def vorherige_serie(state_in: Path | None) -> tuple[int, str | None]:
    """(Serie, Vorbehalt) aus dem Zustand des vorigen Laufs.

    Faellt der Zustand weg — erster Lauf, Cache verdraengt, Datei kaputt —, ist
    die Serie 0 und der Vorbehalt benennt es. Das ist die MILDE Richtung: Der
    Job wird dann spaeter rot als beabsichtigt, nie frueher. Genau deshalb muss
    es im Log stehen und nicht stillschweigend passieren, sonst haelt der
    naechste Blick eine verlorene Serie fuer eine erholte Quelle.
    """
    if state_in is None:
        return 0, None
    if not state_in.is_file():
        return 0, f"kein Vorzustand unter {state_in} — Serie beginnt bei 0"
    try:
        daten = json.loads(state_in.read_text(encoding="utf-8"))
        serie = int(daten["unknown_streak"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return 0, f"Vorzustand {state_in} ist nicht lesbar ({exc}) — Serie beginnt bei 0"
    if serie < 0:
        return 0, f"Vorzustand {state_in} nennt eine negative Serie ({serie}) — auf 0 gesetzt"
    return serie, None


def entscheide_rot(
    state: str,
    vorserie: int,
    grenze: int = UNKNOWN_RUNS_UNTIL_RED,
) -> tuple[bool, int, str]:
    """(rot, neue Serie, Begruendung) — wann macht ein Ergebnis den Job rot.

    `finding` ist sofort rot: Da wurde etwas gemessen. `clear` ist gruen. Nur
    `unknown` sammelt, und beide anderen setzen die Serie zurueck — auch
    `finding`, denn ein Lauf, der einen Befund hatte, hat die Quellen ja
    erreicht.

    Ein gruenes `unknown` ist ausdruecklich KEINE Entwarnung: Der Zustand
    bleibt `unknown`, und der Schritt, der das Drift-Issue schliesst, haengt
    unveraendert an `clear`. Gruen heisst hier «noch nicht laut», nicht «die
    Quellen antworten wieder» — der Unterschied ist der ganze Grund, warum es
    drei Zustaende gibt und nicht zwei.
    """
    if state == CLEAR:
        return False, 0, "gruen"
    if state == FINDING:
        return True, 0, "Befund — sofort rot"
    serie = vorserie + 1
    if serie >= grenze:
        return (
            True,
            serie,
            f"{serie}. Lauf in Folge ohne Messung (Grenze {grenze}) — jetzt rot",
        )
    return (
        False,
        serie,
        f"{serie}. Lauf in Folge ohne Messung (rot ab {grenze}) — noch nicht rot, "
        "aber auch keine Entwarnung",
    )


def schreibe_zustand(state_out: Path | None, state: str, serie: int, seit: str | None) -> None:
    """Den Zustand fuer den naechsten Lauf ablegen. Fehler brechen nichts ab.

    Ein nicht schreibbarer Pfad darf den Melder nicht umbringen: Das Ergebnis
    dieses Laufs steht schon fest, verloren geht nur die Serie — wieder die
    milde Richtung, und sie steht im Log.
    """
    if state_out is None:
        return
    try:
        state_out.parent.mkdir(parents=True, exist_ok=True)
        state_out.write_text(
            json.dumps(
                {
                    "unknown_streak": serie,
                    "last_state": state,
                    "unknown_since": seit,
                    "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"warnung: Zustand nicht geschrieben ({exc}) — die Serie beginnt neu")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_live_run")
    ap.add_argument("report", type=Path, help="Pfad zum JUnit-XML von pytest")
    ap.add_argument("--pytest-exit", type=int, default=None)
    ap.add_argument(
        "--not-started",
        default=None,
        help="Grund, warum pytest gar nicht erst aufgerufen wurde. Setzt `unknown`.",
    )
    ap.add_argument(
        "--state-in",
        type=Path,
        default=None,
        help="Zustand des vorigen Laufs. Fehlt er, beginnt die Serie bei 0.",
    )
    ap.add_argument(
        "--state-out",
        type=Path,
        default=None,
        help="Wohin der Zustand fuer den naechsten Lauf geschrieben wird.",
    )
    ap.add_argument(
        "--unknown-runs-until-red",
        type=int,
        default=UNKNOWN_RUNS_UNTIL_RED,
        help=f"Ab wie vielen `unknown`-Laeufen in Folge rot (Vorgabe {UNKNOWN_RUNS_UNTIL_RED}).",
    )
    args = ap.parse_args(argv)

    state, reason = classify(args.report, args.pytest_exit, args.not_started)

    vorserie, vorbehalt = vorherige_serie(args.state_in)
    rot, serie, rot_grund = entscheide_rot(state, vorserie, args.unknown_runs_until_red)
    if vorbehalt:
        rot_grund = f"{rot_grund} ({vorbehalt})"

    vorher_seit = None
    if args.state_in is not None and args.state_in.is_file():
        try:
            vorher_seit = json.loads(args.state_in.read_text(encoding="utf-8")).get("unknown_since")
        except (OSError, ValueError):
            vorher_seit = None
    heute = datetime.now(timezone.utc).date().isoformat()
    seit = (vorher_seit or heute) if serie else None
    schreibe_zustand(args.state_out, state, serie, seit)

    print(f"state={state}")
    print(f"reason={reason}")
    print(f"red={'true' if rot else 'false'}")
    print(f"streak={serie}")
    print(f"red_reason={rot_grund}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus, bevor der Grund in `$GITHUB_OUTPUT` geht: Die
        # `key=value`-Form endet an der ersten neuen Zeile, und was danach
        # steht, liest der Runner als naechstes Output. Ein Grund aus einer
        # Parser-Meldung oder aus `--not-started` koennte so ein `state=clear`
        # nachschieben und den roten Lauf gruen faerben.
        flat = " ".join(reason.split())
        flach_rot = " ".join(rot_grund.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
            fh.write(f"red={'true' if rot else 'false'}\n")
            fh.write(f"streak={serie}\n")
            fh.write(f"red_reason={flach_rot}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
