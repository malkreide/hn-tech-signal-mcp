# CLAUDE.md

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — Dieses Repo

**ruff:** gepinnt auf `0.16.1`, nur in `.github/workflows/ci.yml:31`.
Eine `.pre-commit-config.yaml` existiert nicht — es gibt keinen zweiten Pin
und damit auch keine Abweichung. Lokal vor dem Push:
`uv pip install "ruff==0.16.1"`.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
ruff check src tests
ruff format --check src tests
PYTHONPATH=src pytest tests/ -m "not live" -v --cov=hn_tech_signal_mcp --cov-report=term-missing --cov-fail-under=65
```

**Live-Tests (DRIFT-005, behoben):** `live-sources.yml` fährt die 11
`@pytest.mark.live`-Tests gegen HackerNews, arXiv, Lobste.rs und GitHub —
täglich 05:17 UTC, dazu `workflow_dispatch`. Ein roter Lauf eröffnet ein Issue
mit Label `live-drift` oder kommentiert das offene, ein grüner schliesst es
wieder; ohne das sieht ein roter Zeitplan niemand, und ein Melder, der nie
entwarnt, wird ignoriert. Beides nur auf dem Default-Branch: ein grüner
Dispatch auf einem Feature-Branch sagt nichts über `main`.
`ci.yml` wählt Live-Tests weiterhin per `-m "not live"` ab.
Der Workflow installiert bewusst kein ruff — der Pin bleibt einmalig.

**Befund — keine aufgezeichneten Antworten:** die respx-Mocks in
`tests/test_server.py` sind handgeschrieben, ohne Aufnahmedatum. Das
verletzt die Fixture-Regel aus Teil 1 für alle vier Endpunkte.

Alles Weitere (Tool-Übersicht, Setup, Beispiele) steht in `README.md`,
`EXAMPLES.md` und `audits/`.
