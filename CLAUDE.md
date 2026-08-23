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

In *diesem* Repo läuft die Prüfung seit PR #46 automatisch: der SessionStart-Hook
`.claude/hooks/session-start.sh` meldet den Rückstand beim Sessionstart und
schweigt bei 0. Er ersetzt den Befehl oben nicht, sondern erinnert daran — er
blockiert nie und schweigt deshalb auch, wenn Netz, Remote oder Default-Branch
nicht zu ermitteln sind. In den übrigen Servern des Portfolios gibt es ihn noch
nicht; dort bleibt es Handarbeit. Begründung und Zusicherungen:
`.claude/hooks/README.md`.

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

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Bis mindestens zum 22.8. um 08:30, also 23 Stunden später, blieb es dabei. In
der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden, ohne
dass jemand hineingesehen hat.

Vier Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann reagiert er mit 👍 und schreibt nichts.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo ist keine Codex-Umgebung eingerichtet** — dann schreibt er
  stattdessen «To use Codex here, create an environment for this repo», und
  daran ändert kein Wartefenster etwas.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein echter Review ist ein Review-Objekt («💡 Codex Review»,
mit Commit-Angabe), die Limit-Meldung ein gewöhnlicher Issue-Kommentar. Das
sind zwei verschiedene Abfragen — `get_reviews` gegen `get_comments`; wer nur
eine davon nimmt, übersieht die andere Hälfte. Genau so ist die Limit-Meldung
zuerst durchgerutscht.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Eine Absage taugt umgekehrt nicht als Beleg fürs Gegenteil, denn die vier
Fälle kommen in einer Reihenfolge: Ist das Kontingent leer, meldet Codex das
— ob überhaupt eine Umgebung besteht, prüft er dann womöglich gar nicht. In
`swiss-public-data-mcp` kam am 22.8. die Limit-Meldung und am 23.8., nach
Rückkehr des Kontingents, die Umgebungs-Meldung; erst als der erste Engpass
weg war, wurde der zweite sichtbar. Eine Limit-Meldung belegt also, dass die
App reagiert, nicht dass sie hier arbeiten könnte.

Belastbar ist nur ein Review-Objekt, und dafür gibt es eine eigene Abfrage:

```
search_pull_requests: user:malkreide type:pr reviewed-by:chatgpt-codex-connector[bot]
```

Am 23.8.2026 über die 41 Server-Repos: 25 mit mindestens einem echten Review,
16 nur mit Absagen. «Belegt» heisst dabei «damals», nicht «heute» — ein Review
vom 16.8. sagt über den aktuellen Stand nichts.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Zeigt das freies Kontingent, während Reviews weiter
scheitern, ist das ein bekannter Fehler bei mehreren verbundenen Konten — dann
den GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Dieses Repo

**ruff:** gepinnt auf `0.16.3`, nur im `dev`-Extra von `pyproject.toml`.
Eine `.pre-commit-config.yaml` existiert nicht — es gibt keinen zweiten Pin
und damit auch keine Abweichung. Lokal vor dem Push genügt
`uv pip install --system -e ".[dev]"`; ein separates ruff nachzuinstallieren
ist nicht mehr nötig.

Vorher stand der Pin in einer `uv pip install`-Zeile der CI, zusammen mit den
Test-Abhängigkeiten. Ein `dev`-Extra gab es nicht, weshalb der Install ein
`|| uv pip install -e .` als Fallback trug — der wich still auf eine
unvollständige Umgebung aus und liess den Fehler erst einen Schritt später
auftauchen, als «ruff not found» statt als «Extra fehlt». Beides ist weg.

Die Zahl hier wandert: Dependabot hebt den Pin an (zuletzt PR #45, 0.16.1 →
0.16.3), und dieser Absatz zieht nicht von selbst nach. Im Zweifel gilt
`pyproject.toml`, nicht diese Zeile.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet. `scripts/check_ruff_pin.py`
sagt es einem sonst erst in der CI — es prüft beide Aufrufwege (`ruff` aus dem
`PATH` und `python -m ruff`). Ein per `uv tool install` global abgelegtes ruff
unter `~/.local/bin` gewinnt gegen das Extra; dann entweder jenes entfernen oder
die Gates mit `python -m ruff` fahren.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```bash
python scripts/check_ruff_pin.py
ruff check src tests scripts
ruff format --check src tests scripts
PYTHONPATH=src pytest tests/ -m "not live" -v --cov=hn_tech_signal_mcp --cov-report=term-missing --cov-fail-under=65
python scripts/check_version_sync.py
python scripts/check_claude_md.py
```

Der `pytest`-Aufruf ist zugleich das Coverage-Gate: `--cov-fail-under=65`
steht im Befehl, nicht in einer Konfigurationsdatei. Ein Lauf über eine
einzelne Testdatei fällt daran, nicht am Test. Die ruff-Pfade stehen ohne
Schrägstrich (`src tests scripts`) — dasselbe Ergebnis, aber beim Kopieren
zwischen Repos nicht verwechseln.

**Das Versions-Sync-Gate gehört dazu.** `scripts/` enthält
`check_ruff_pin.py`, `check_version_sync.py`, `check_claude_md.py` und
`record_fixtures.py`. Die Version ist `dynamic` und kommt aus
`src/hn_tech_signal_mcp/__init__.py` (`0.4.1`); `server.json` trägt sie zweimal
(`version` und `packages[0].version`), beide READMEs je einmal im Badge. Weil
`pyproject.toml` die Zahl gar nicht nennt, fiel beim Anheben früher leicht eine
der Stellen unter den Tisch — genau das hält jetzt `check_version_sync.py` fest,
statt auf Sorgfalt zu setzen. Es prüft zusätzlich, dass in `src/` keine
hartkodierte Version steht.

An dieser Stelle stand bis zu dieser Änderung das Gegenteil: «Drei ist die
ganze Liste — es gibt kein Versions-Sync-Gate», zusammen mit der Angabe,
`scripts/` enthalte nur `record_fixtures.py`. Das war überholt, seit das Skript
und sein CI-Schritt dazukamen. Eine Konventionsdatei, die eine Prüfung
*bestreitet*, die es gibt, ist schlimmer als eine, die sie verschweigt: Wer eine
Version anhebt, verlässt sich auf den Absatz und sucht das rote Gate zuerst an
der falschen Stelle.

`scripts` steht seit dem Fixture-Recorder mit im Gate. Vorher lag dort nichts;
ein ungeprüftes Verzeichnis fällt erst auf, wenn etwas drin steht.

**Diese Datei wird selbst geprüft.** `scripts/check_claude_md.py` hält vier
Angaben aus Teil 2 gegen ihre Quellen: den Gate-Block gegen die `run:`-Schritte
aus `ci.yml`, den zitierten ruff-Pin gegen `pyproject.toml`, die erwähnten
Skripte gegen `scripts/` (in beide Richtungen — ein unerwähntes Skript fällt
genauso auf wie ein genanntes ohne Datei) und die Zahl der Live-Tests gegen die
Testdateien. Jede dieser Angaben muss vorhanden sein: Wer sie herausnimmt,
statt sie zu korrigieren, fällt ebenfalls, sonst wäre Löschen der bequemste Weg
am Gate vorbei.

Bewusst ungeprüft bleibt, was sich nur als Prosa fassen lässt — die Zahl der
aufgezeichneten Antworten, die Beschreibung von `live-sources.yml`, jede
Begründung. Ein Gate mit Fehlalarmen wird abgeschaltet und schützt danach gar
nichts; lieber vier belegte Angaben als zwölf wacklige.

**Live-Tests (DRIFT-005, behoben):** `live-sources.yml` fährt die
`@pytest.mark.live`-Tests gegen HackerNews, arXiv, Lobste.rs und GitHub —
täglich 05:17 UTC, dazu `workflow_dispatch`. Ein roter Lauf eröffnet ein Issue
mit Label `live-drift` oder kommentiert das offene, ein grüner schliesst es
wieder; ohne das sieht ein roter Zeitplan niemand, und ein Melder, der nie
entwarnt, wird ignoriert. Beides nur auf dem Default-Branch: ein grüner
Dispatch auf einem Feature-Branch sagt nichts über `main`.
`ci.yml` wählt Live-Tests weiterhin per `-m "not live"` ab und meldet sie als
«12 deselected»: 12 Fälle aus 10 Funktionen, denn `test_live_hn_extended_feeds`
ist dreifach parametrisiert (`ask`, `show`, `job`). Wer die Funktionen zählt und
die Differenz für einen Fehler hält, sucht umsonst — hier stand vorher «11», was
auf keine der beiden Zählweisen passt. Beide Zahlen prüft
`scripts/check_claude_md.py`.
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
