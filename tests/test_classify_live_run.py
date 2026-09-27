#!/usr/bin/env python3
"""Tests fuer scripts/classify_live_run.py — die drei Antworten eines Live-Laufs.

Die Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Genau deshalb
steht sie in einem Skript und nicht in einem `run:`-Block: So kann jemand sie
gegen die Faelle halten, aus denen sie entstanden ist.

Der wichtigste Fall ist `test_alle_uebersprungen_ist_nicht_gruen`. Gemessen am
7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY` ueberspringt die
Live-Suite alle sechs Tests und pytest endet mit 0. Ein Job, der das als gruen
bucht, schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

Nur Standardbibliothek, kein Netz.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import classify_live_run as clr  # noqa: E402


def write(tmp: Path, xml: str) -> Path:
    path = tmp / "live-report.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def suite(tests: int, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}"></testsuite></testsuites>'
    )


def cli(*extra: str) -> tuple[str, str]:
    """Ruft `main` mit gesetztem $GITHUB_OUTPUT und liest zurueck, was ankam."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gh-output"
        out.write_text("", encoding="utf-8")
        os.environ["GITHUB_OUTPUT"] = str(out)
        try:
            clr.main([str(Path(tmp) / "live-report.xml"), *extra])
        finally:
            del os.environ["GITHUB_OUTPUT"]
        written = out.read_text(encoding="utf-8")
    werte = dict(line.split("=", 1) for line in written.splitlines() if line)
    return werte["state"], werte["reason"]


class ClassifyTest(unittest.TestCase):
    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_alles_gruen_ist_clear(self):
        state, reason = self._state(suite(tests=3))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("3 von 3", reason)

    def test_ein_fehlschlag_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_ein_fehler_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, errors=1))
        self.assertEqual(state, clr.FINDING)

    def test_alle_uebersprungen_ist_nicht_gruen(self):
        """swiss-transport-mcp ohne TRANSPORT_API_KEY: 6 von 6 uebersprungen."""
        state, reason = self._state(suite(tests=6, skipped=6))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("uebersprungen", reason)

    def test_teilweise_uebersprungen_ist_gruen(self):
        """Ein einzelner Skip ist eine Entscheidung im Test, kein Ausfall."""
        state, reason = self._state(suite(tests=6, skipped=5))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("1 von 6", reason)

    def test_null_tests_ist_kein_erfolg(self):
        """Die Marke umbenannt, die Dateien verschoben — pytest meldet trotzdem 0."""
        state, reason = self._state(suite(tests=0))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("null Tests", reason)

    def test_ein_fehlschlag_schlaegt_uebersprungene(self):
        state, _ = self._state(suite(tests=6, skipped=5, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_mehrere_testsuites_werden_summiert(self):
        xml = (
            "<testsuites>"
            '<testsuite tests="2" failures="0" errors="0" skipped="2"/>'
            '<testsuite tests="3" failures="0" errors="0" skipped="0"/>'
            "</testsuites>"
        )
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)

    def test_eine_einzelne_testsuite_ohne_huelle(self):
        xml = '<testsuite tests="2" failures="0" errors="0" skipped="0"/>'
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)


class MissingReportTest(unittest.TestCase):
    """Kein Report heisst: pytest kam nicht bis zum Schreiben. Nie clear."""

    def test_fehlender_report_ist_unknown(self):
        state, reason = clr.classify(Path("/nonexistent/live-report.xml"), pytest_exit=4)
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("Exit 4", reason)

    def test_kaputtes_xml_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<testsuite tests=")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)

    def test_xml_ohne_testsuite_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<irgendwas/>")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)


class NotStartedTest(unittest.TestCase):
    """pytest nie aufgerufen: Der Grund kommt vom Aufrufer, nicht vom Exit-Code.

    Beobachtet am 24.8.2026 in `swiss-ip-mcp`: Ohne Zugangsdaten meldete der
    Workflow `--pytest-exit 127`, und daraus wurde «pytest ist nicht bis zum
    Schreiben gekommen (Exit 127)». 127 heisst «command not found» — der Satz
    behauptete einen gescheiterten pytest-Aufruf, den es nie gab.
    """

    def test_grund_wird_woertlich_durchgereicht(self):
        state, reason = clr.classify(
            Path("/nonexistent/live-report.xml"),
            not_started="Secret ist nicht gesetzt",
        )
        self.assertEqual(state, clr.UNKNOWN)
        self.assertEqual(reason, "Secret ist nicht gesetzt")

    def test_kein_erfundener_pytest_lauf_in_der_begruendung(self):
        _, reason = clr.classify(
            Path("/nonexistent/live-report.xml"),
            not_started="Secret ist nicht gesetzt",
        )
        self.assertNotIn("pytest ist nicht bis zum Schreiben gekommen", reason)
        self.assertNotIn("Exit", reason)

    def test_ein_liegengebliebener_report_belegt_nichts(self):
        """Gruenes XML aus einem frueheren Schritt macht einen Nicht-Lauf nicht gruen."""
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=3))
            state, reason = clr.classify(report, not_started="gar nicht gestartet")
        self.assertEqual(state, clr.UNKNOWN)
        self.assertEqual(reason, "gar nicht gestartet")

    def test_leerer_grund_ist_kein_grund(self):
        """Der Workflow reicht `--not-started` nur gesetzt durch; leer heisst: pytest lief."""
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=3))
            state, _ = clr.classify(report, not_started="")
        self.assertEqual(state, clr.CLEAR)

    def test_ueber_die_kommandozeile(self):
        state, reason = cli("--not-started", "kein Secret")
        self.assertEqual(state, "unknown")
        self.assertEqual(reason, "kein Secret")


class GithubOutputTest(unittest.TestCase):
    """Der Workflow liest state und reason ueber $GITHUB_OUTPUT."""

    def test_beide_werte_werden_angehaengt(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=2))
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                rc = clr.main([str(report)])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            written = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("state=clear", written)
        self.assertIn("reason=", written)

    def test_ein_mehrzeiliger_grund_schiebt_kein_zweites_output_nach(self):
        """`key=value` endet an der ersten neuen Zeile — was danach steht, ist Output."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                clr.main(
                    [
                        str(Path(tmp) / "live-report.xml"),
                        "--not-started",
                        "kein Secret\nstate=clear",
                    ]
                )
            finally:
                del os.environ["GITHUB_OUTPUT"]
            zeilen = [z for z in out.read_text(encoding="utf-8").splitlines() if z]
        self.assertEqual([z for z in zeilen if z.startswith("state=")], ["state=unknown"])
        # Die Schluesselmenge, nicht die Zeilenzahl: Hier stand `len(zeilen) == 2`,
        # und die Zahl wurde falsch, als `red`, `streak` und `red_reason`
        # dazukamen — obwohl die Zusicherung, um die es geht, unveraendert galt.
        # Die Menge ist ausserdem strenger: Sie faengt eine eingeschmuggelte
        # Zeile UND einen weggefallenen Schluessel.
        self.assertEqual(
            sorted(z.split("=", 1)[0] for z in zeilen),
            ["reason", "red", "red_reason", "state", "streak"],
        )


if __name__ == "__main__":
    unittest.main()


def suite_mit_fehlschlaegen(*meldungen: str, errors: int = 0, tests: int = 12) -> str:
    """Ein Report mit je einem `<testcase>` pro Meldung.

    Anders als `suite()` traegt dieser die Fehlertexte mit — ohne sie kann die
    Einordnung «nicht geantwortet» gar nicht von «anders geantwortet»
    trennen, und ein Test daraufhin nichts beweisen.
    """
    faelle = "".join(
        f'<testcase name="test_{i}"><failure message="{m}">{m}</failure></testcase>'
        for i, m in enumerate(meldungen)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" '
        f'failures="{len(meldungen)}" errors="{errors}" skipped="0">'
        f"{faelle}</testsuite></testsuites>"
    )


class StummeQuelleTest(unittest.TestCase):
    """Eine Quelle, die nicht geantwortet hat, ist kein Drift-Befund.

    Gemessen am 13.9.2026: arXiv liess die Anfrage 16 bis 46 Sekunden stehen
    und antwortete dann mit `429 Rate exceeded.`; das Zeitbudget des Servers
    lief vorher ab. Der Lauf eroeffnete Issue #68 mit der Behauptung, das
    Schema habe sich geaendert. Geaendert hatte sich nichts — eine parallele
    Abfrage derselben URL lieferte einen unveraenderten Atom-Feed.
    """

    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_nur_stumme_quellen_sind_unknown(self):
        state, reason = self._state(
            suite_mit_fehlschlaegen(
                f"{clr.UNREACHABLE_MARKER}: arXiv — [arXiv] Error: Request timed out.",
                f"{clr.UNREACHABLE_MARKER}: arXiv — [arXiv] Error: Rate limit exceeded.",
            )
        )
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("nicht geantwortet", reason)

    def test_eine_einzige_stumme_quelle_genuegt(self):
        """Keine Mehrheitsschwelle — ein Fehlschlag, und der ist stumm.

        Das `assertNotEqual(CLEAR)` steht dabei, weil es die teure Richtung
        benennt: Nicht das verschwiegene Drift ist die Gefahr, sondern ein
        `clear`, das ein offenes Issue zumacht und behauptet, die Quellen
        antworteten wieder wie erwartet. Allein taugt es als Zusicherung
        nichts — `finding` ist auch nicht `clear` —, deshalb steht das
        `assertEqual(UNKNOWN)` davor und traegt den Test.
        """
        state, _ = self._state(
            suite_mit_fehlschlaegen(f"{clr.UNREACHABLE_MARKER}: arXiv — timeout")
        )
        self.assertEqual(state, clr.UNKNOWN)
        self.assertNotEqual(state, clr.CLEAR)

    def test_echter_drift_bleibt_ein_befund(self):
        """Die Gegenprobe: ohne Marker aendert sich nichts am alten Verhalten."""
        state, _ = self._state(
            suite_mit_fehlschlaegen("assert 0 > 0 — by_category hat keinen Schluessel cs.AI")
        )
        self.assertEqual(state, clr.FINDING)

    def test_gemischt_ist_ein_befund(self):
        """Eine stumme UND eine gedriftete Quelle: Drift wurde gesehen.

        Nur ein Lauf, in dem AUSSCHLIESSLICH niemand geantwortet hat, sagt
        nichts. Sobald eine Zusicherung ueber echte Daten faellt, gehoert das
        gemeldet — sonst deckt ein gleichzeitiger Netzausfall den Befund zu.
        """
        state, _ = self._state(
            suite_mit_fehlschlaegen(
                f"{clr.UNREACHABLE_MARKER}: arXiv — timeout",
                "assert 0 > 0 — Lobste.rs liefert keine Titel mehr",
            )
        )
        self.assertEqual(state, clr.FINDING)

    def test_fehler_neben_stummen_quellen_bleiben_ein_befund(self):
        """Ein `error` ist kein Fehlschlag und wird nicht mitverschluckt."""
        state, _ = self._state(
            suite_mit_fehlschlaegen(f"{clr.UNREACHABLE_MARKER}: arXiv — timeout", errors=1)
        )
        self.assertEqual(state, clr.FINDING)

    def test_marker_stimmt_mit_der_testsuite_ueberein(self):
        """Beide Seiten des Vertrags, sonst haelt er nur zufaellig.

        Die Einordnung liest ein Wort, das `tests/test_server.py` schreibt. Wer
        eines von beiden umbenennt, bekaeme ohne diesen Test eine still
        wirkungslose Einordnung: Jeder stumme Lauf waere wieder ein
        Drift-Befund, und nichts waere rot ausser dem Melder selbst.
        """
        quelle = (Path(__file__).parent / "test_server.py").read_text(encoding="utf-8")
        self.assertIn(f'QUELLE_STUMM = "{clr.UNREACHABLE_MARKER}"', quelle)


def stumme_suite(anzahl: int = 1, tests: int = 12) -> str:
    """Ein Report, dessen Fehlschlaege alle den Stumm-Marker tragen."""
    faelle = "".join(
        f'<testcase name="test_{i}">'
        f'<failure message="{clr.UNREACHABLE_MARKER}: arXiv">'
        f"{clr.UNREACHABLE_MARKER}: arXiv</failure></testcase>"
        for i in range(anzahl)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{anzahl}" '
        f'errors="0" skipped="0">{faelle}</testsuite></testsuites>'
    )


class SerieTest(unittest.TestCase):
    """`unknown` wird erst nach drei Laeufen in Folge rot.

    Vorher war jedes `unknown` sofort rot. Inhaltlich richtig, praktisch
    schaedlich: arXiv drosselt nach IP, GitHub-Runner teilen ihre IPs mit aller
    Welt, und der Zeitplan lief vom 13. bis 15.9.2026 taeglich rot, ohne dass an
    den Quellen etwas war. Ein Haken, der jeden Tag rot steht, wird zur Tapete —
    und mit ihm der naechste, der etwas bedeutet.
    """

    def _lauf(self, xml: str, zustand: Path) -> dict[str, str]:
        """Einen Lauf fahren und die Ausgaben lesen. `zustand` wird mitgefuehrt."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                clr.main(
                    [
                        str(write(Path(tmp), xml)),
                        "--state-in",
                        str(zustand),
                        "--state-out",
                        str(zustand),
                    ]
                )
            finally:
                del os.environ["GITHUB_OUTPUT"]
            return dict(
                line.split("=", 1) for line in out.read_text(encoding="utf-8").splitlines() if line
            )

    def test_erst_der_dritte_unknown_lauf_ist_rot(self):
        with tempfile.TemporaryDirectory() as heim:
            zustand = Path(heim) / "live-state.json"
            ergebnisse = [self._lauf(stumme_suite(), zustand) for _ in range(4)]

        self.assertEqual([e["state"] for e in ergebnisse], [clr.UNKNOWN] * 4)
        self.assertEqual([e["streak"] for e in ergebnisse], ["1", "2", "3", "4"])
        self.assertEqual(
            [e["red"] for e in ergebnisse],
            ["false", "false", "true", "true"],
            "rot muss beim dritten Lauf einsetzen und danach bleiben",
        )

    def test_ein_befund_ist_sofort_rot(self):
        """`finding` wartet auf nichts — da wurde etwas gemessen."""
        with tempfile.TemporaryDirectory() as heim:
            zustand = Path(heim) / "live-state.json"
            e = self._lauf(suite(tests=12, failures=1), zustand)
        self.assertEqual(e["state"], clr.FINDING)
        self.assertEqual(e["red"], "true")
        self.assertEqual(e["streak"], "0")

    def test_ein_gruener_lauf_setzt_die_serie_zurueck(self):
        """«In Folge» heisst in Folge: Ein `clear` dazwischen bricht sie.

        Ohne das waere die Grenze eine Gesamtzahl ueber die Lebenszeit des
        Repos und der Melder wuerde irgendwann dauerhaft rot stehen, ohne dass
        aktuell etwas waere.
        """
        with tempfile.TemporaryDirectory() as heim:
            zustand = Path(heim) / "live-state.json"
            self._lauf(stumme_suite(), zustand)
            self._lauf(stumme_suite(), zustand)
            gruen = self._lauf(suite(tests=12), zustand)
            danach = self._lauf(stumme_suite(), zustand)

        self.assertEqual(gruen["state"], clr.CLEAR)
        self.assertEqual(gruen["streak"], "0")
        self.assertEqual(danach["streak"], "1", "nach einem gruenen Lauf faengt sie neu an")
        self.assertEqual(danach["red"], "false")

    def test_auch_ein_befund_setzt_die_serie_zurueck(self):
        """Ein Lauf mit Befund hat die Quellen ja erreicht."""
        with tempfile.TemporaryDirectory() as heim:
            zustand = Path(heim) / "live-state.json"
            self._lauf(stumme_suite(), zustand)
            self._lauf(stumme_suite(), zustand)
            self._lauf(suite(tests=12, failures=1), zustand)
            danach = self._lauf(stumme_suite(), zustand)
        self.assertEqual(danach["streak"], "1")
        self.assertEqual(danach["red"], "false")

    def test_gruen_ist_keine_entwarnung(self):
        """Der Zustand bleibt `unknown`, auch wenn der Job gruen ist.

        Daran haengt alles: Der Workflow-Schritt, der das Drift-Issue
        schliesst, prueft `state == 'clear'`. Wuerde ein mildes `unknown`
        hier als `clear` durchgehen, machte der Melder ein offenes Issue zu,
        ohne dass eine Quelle geantwortet haette — der teuerste Fehler, den
        dieses Skript verhindern soll.
        """
        with tempfile.TemporaryDirectory() as heim:
            e = self._lauf(stumme_suite(), Path(heim) / "live-state.json")
        self.assertEqual(e["red"], "false")
        self.assertEqual(e["state"], clr.UNKNOWN, "gruen darf den Zustand nicht zu clear machen")
        self.assertIn("keine Entwarnung", e["red_reason"])

    def test_verlorener_vorzustand_beginnt_bei_null_und_sagt_es(self):
        """Die milde Richtung — aber benannt, nicht stillschweigend.

        Faellt der Cache weg, wird der Job SPAETER rot, nie frueher. Wer das
        nicht im Log sieht, haelt eine verlorene Serie fuer eine erholte
        Quelle.
        """
        with tempfile.TemporaryDirectory() as heim:
            fehlt = Path(heim) / "gibt-es-nicht.json"
            e = self._lauf(stumme_suite(), fehlt)
        self.assertEqual(e["streak"], "1")
        self.assertIn("kein Vorzustand", e["red_reason"])

    def test_kaputter_vorzustand_bricht_nichts_ab(self):
        with tempfile.TemporaryDirectory() as heim:
            kaputt = Path(heim) / "live-state.json"
            kaputt.write_text("{kein json", encoding="utf-8")
            e = self._lauf(stumme_suite(), kaputt)
        self.assertEqual(e["streak"], "1")
        self.assertEqual(e["red"], "false")
        self.assertIn("nicht lesbar", e["red_reason"])

    def test_die_grenze_ist_einstellbar(self):
        """Damit ein Test sie nicht dreimal durchlaufen muss — und damit die
        Zahl an einer Stelle steht und nicht in jeder Zusicherung."""
        self.assertEqual(clr.entscheide_rot(clr.UNKNOWN, 0, grenze=1)[0], True)
        self.assertEqual(clr.entscheide_rot(clr.UNKNOWN, 0, grenze=5)[0], False)
        self.assertEqual(clr.UNKNOWN_RUNS_UNTIL_RED, 3)

    def test_der_workflow_haengt_an_red_nicht_an_state(self):
        """Die Gegenprobe zur Verdrahtung: Ein Skript, das `red` ausgibt, und
        ein Workflow, der weiter `state != 'clear'` prueft, waeren zusammen
        wirkungslos — die ganze Aenderung laege brach, und nichts waere rot
        ausser dem Melder selbst.
        """
        yml = (
            Path(__file__).parent.parent / ".github" / "workflows" / "live-sources.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("steps.verdict.outputs.red == 'true'", yml)
        self.assertNotIn("steps.verdict.outputs.state != 'clear'", yml)
        # Und der Zustand muss einen Lauf ueberleben, sonst zaehlt niemand mit.
        self.assertIn("--state-in live-state.json", yml)
        self.assertIn("--state-out live-state.json", yml)
        self.assertIn("actions/cache/restore", yml)
        self.assertIn("actions/cache/save", yml)
