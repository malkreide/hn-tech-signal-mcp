# CLAUDE.md

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

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

**ruff:** gepinnt auf `0.16.1`, nur im `dev`-Extra von `pyproject.toml`.
Eine `.pre-commit-config.yaml` existiert nicht — es gibt keinen zweiten Pin
und damit auch keine Abweichung. Lokal vor dem Push genügt
`uv pip install --system -e ".[dev]"`; ein separates ruff nachzuinstallieren
ist nicht mehr nötig.

Vorher stand der Pin in einer `uv pip install`-Zeile der CI, zusammen mit den
Test-Abhängigkeiten. Ein `dev`-Extra gab es nicht, weshalb der Install ein
`|| uv pip install -e .` als Fallback trug — der wich still auf eine
unvollständige Umgebung aus und liess den Fehler erst einen Schritt später
auftauchen, als «ruff not found» statt als «Extra fehlt». Beides ist weg.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
python scripts/check_ruff_pin.py
ruff check src tests scripts
ruff format --check src tests scripts
PYTHONPATH=src pytest tests/ -m "not live" -v --cov=hn_tech_signal_mcp --cov-report=term-missing --cov-fail-under=65
```

Der `pytest`-Aufruf ist zugleich das Coverage-Gate: `--cov-fail-under=65`
steht im Befehl, nicht in einer Konfigurationsdatei. Ein Lauf über eine
einzelne Testdatei fällt daran, nicht am Test. Die ruff-Pfade stehen ohne
Schrägstrich (`src tests scripts`) — dasselbe Ergebnis, aber beim Kopieren
zwischen Repos nicht verwechseln.

**Drei ist die ganze Liste — es gibt kein Versions-Sync-Gate.** `scripts/`
enthält nur `record_fixtures.py`, ein `check_version_sync.py` fehlt, und kein
Workflow ruft eines auf. Die Version ist `dynamic` und kommt aus
`src/hn_tech_signal_mcp/__init__.py` (`0.4.1`); `server.json` trägt sie ein
zweites Mal (`0.4.1`). Beide stimmen heute überein, gehalten wird das von
nichts — und weil `pyproject.toml` die Zahl gar nicht nennt, fällt beim
Anheben leicht die zweite Stelle unter den Tisch.

`scripts` steht seit dem Fixture-Recorder mit im Gate. Vorher lag dort nichts;
ein ungeprüftes Verzeichnis fällt erst auf, wenn etwas drin steht.

**Live-Tests (DRIFT-005, behoben):** `live-sources.yml` fährt die 11
`@pytest.mark.live`-Tests gegen HackerNews, arXiv, Lobste.rs und GitHub —
täglich 05:17 UTC, dazu `workflow_dispatch`. Ein roter Lauf eröffnet ein Issue
mit Label `live-drift` oder kommentiert das offene, ein grüner schliesst es
wieder; ohne das sieht ein roter Zeitplan niemand, und ein Melder, der nie
entwarnt, wird ignoriert. Beides nur auf dem Default-Branch: ein grüner
Dispatch auf einem Feature-Branch sagt nichts über `main`.
`ci.yml` wählt Live-Tests weiterhin per `-m "not live"` ab.
Der Workflow installiert bewusst kein ruff — der Pin bleibt einmalig.

**Fixtures: aufgezeichnet.** `tests/fixtures/` hält 46 echte Antworten;
Herkunft, Schlüssel, Auswahlregel und SHA-256 stehen je Datei in
`tests/fixtures/PROVENANCE.md` — Portfolio-Konvention, gleich wie in
`swisstopo-mcp` und `swiss-environment-mcp`. Neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`, geladen wird über
`tests/fixture_data.py`. Die respx-Stubs in `tests/test_server.py` bleiben für
die Fehlerpfade — Timeout, 5xx, leere Trefferliste —, die sich nicht auf Zuruf
aufzeichnen lassen.

Eine Aufzeichnung je **Abfrage**, nicht je Endpunkt: `hn_top_stories` holt erst
eine ID-Liste und dann jede Story einzeln, `hn_discussion` steigt den
Kommentarbaum hinab, `tech_signal_digest` fächert mit `asyncio.gather` über alle
Quellen zugleich auf. Zugeordnet wird deshalb nach der Anfrage und nie nach der
Reihenfolge.

Zwei Stolperstellen, die beim Aufzeichnen auffielen:

- `hn_search` schreibt `int(time.time()) - days_back * 86400` in die URL. Der
  Schlüssel einer Aufzeichnung ändert sich damit **jede Sekunde**; die Tests
  halten die Uhr auf dem Aufnahmezeitpunkt an und rechnen ihn aus dem
  Schlüssel zurück, statt eine Zahl einzutragen.
- Der Recorder fasst gleiche Anfragen zusammen. Die Story der Diskussion lag
  schon unter ihrem `hn_top`-Namen im Ordner — `hn_discussion_1.json` ist
  bereits ein Kommentar. Wer die Story sucht, sucht nach `type == "story"` mit
  aufgezeichneten `kids`, nicht nach dem Dateinamen.

**Befund — eine Quelle fehlt:** `api.github.com/search/repositories` antwortet
aus der Aufnahmeumgebung mit HTTP 403 (`sessions are bound to their configured
repositories`). Gemessen, nicht aus der Meldung geschlossen: dieselbe 403 kommt
mit und ohne Token, ohne `Server`-Header, ohne `x-github-request-id` und mit
`documentation_url` auf docs.anthropic.com — die Anfrage erreicht GitHub nie.
Gesperrt ist der **Pfad**, nicht der Host und nicht die Authentisierung; ein
eigenes `GITHUB_TOKEN` ändert daran nichts, nötig ist eine Umgebung ohne diese
Beschränkung. `github_trending_ai` bleibt deshalb bei handgeschriebenen Stubs;
die Begründung steht als `NICHT_VON_HIER` im Recorder und wird von
`test_die_gesperrte_quelle_steht_begruendet_im_recorder` festgehalten.

Der Aufruf steht trotzdem im `PLAN` — er war einmal herausgenommen, und damit
war die Lücke zwar dokumentiert, aber selbst mit Zugriff nicht mehr zu
schliessen: der Lauf hätte sie gar nicht angefahren. Eine dokumentierte Lücke
ohne den Weg, sie zu füllen, ist keine Lücke mehr, sondern ein Loch mit
Beschriftung. Ein von der Umgebung abgewiesener Pfad (`GESPERRT`) wird beim
Aufzeichnen mit Begründung übersprungen statt wiederholt — das Werkzeug meldet
ihn als gewöhnlichen Fehler, und der sah für den Recorder aus wie ein
Retry-Grund: vier Versuche, 14 Sekunden Backoff, danach ein `raise`, der den
ganzen restlichen Plan mitnahm. Eng gefasst: eine 403 **ohne** diese Signatur
läuft weiter durch den Backoff, sonst wäre eine einmal schliessende Quelle
dauerhaft ohne Aufzeichnung.

Alles Weitere (Tool-Übersicht, Setup, Beispiele) steht in `README.md`,
`EXAMPLES.md` und `audits/`.
