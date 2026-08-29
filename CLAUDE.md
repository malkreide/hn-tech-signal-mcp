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

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

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

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft gibt es überhaupt
nichts, weil Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein
Beleg, sondern ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — drei
gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die Zahl.
Und einen unbekannten vierten Text wörtlich zitieren, statt ihn in eine der
bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon einmal von drei
auf vier Gründe wachsen, und die 👍-Reaktion stand hier zwei Fassungen lang als
Tatsache.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

**Nachtrag 29.8.2026: beide Wege zugleich, in vier Sekunden.** PR #59 in diesem
Repo lief genau durch diese Lücke, und der Ablauf ist auf die Sekunde belegt:

```
09:29:00  Draft → ready (der Auslöser)
09:29:02  «You have reached your Codex usage limits for code reviews.»
09:29:04  gemergt
```

`get_reviews` war leer, `get_comments` trug genau diese eine Meldung — also der
dritte Grund, sechs Tage nach der letzten Beobachtung vom 22.8. Und zwar nicht
als Fortsetzung jener Sperre: Am 23.8. um 08:22 kam eine *andere* Meldung, das
Kontingent war dort also zurück. Was zwischen dem 23. und dem 29. geschah, hat
niemand gemessen; die sechs Tage sind ein Loch, keine Dauer. In diesem Repo
liegt aus der Zeit auch kein einziger Codex-Kommentar — die PRs #56, #57 und
#58 tragen keinen. Das grenzt nichts ein, es heisst nur, dass hier niemand
hingesehen hat.

Zwei Dinge macht dieser Ablauf schärfer als die Absätze davor.

**Zwei Sekunden sind kein Review.** Der Absatz oben sagt, Codex brauche nach dem
Auslöser Zeit — das gilt fürs Lesen eines Diffs, nicht fürs Scheitern. Die
Kontingentprüfung liegt davor und antwortet sofort. Wer also innerhalb von
Sekunden etwas vom Bot sieht, hat keinen besonders schnellen Review vor sich,
sondern eine Ausfallmeldung, und muss den Text lesen. Eine Beobachtung, keine
Messreihe — aber sie trennt zwei Fälle, die vorher beide unter «Codex hat
geantwortet» fielen.

**Die beiden Wege, den Prüfer zu verlieren, decken einander zu.** Hier fielen
sie zusammen: Wäre die Meldung zwei Sekunden später gekommen, wäre sie auf
einem bereits gemergten PR gelandet. Verloren ist sie dadurch nicht — der
Kommentar steht weiter am PR und lässt sich nachlesen. Verloren ist der Anlass
hinzusehen: Niemand liest die Kommentare eines PRs, den er vor vier Sekunden
gemergt hat. «Ich schaue nach dem Merge nach» trägt deshalb nicht; die
Wartezeit muss vor den Merge.

Offen bleibt, ob Codex nach einer Kontingent-Meldung von selbst noch einmal
anläuft, sobald sich das Fenster öffnet. Hier gab es dafür kein Zeitfenster —
zwei Sekunden nach der Meldung war der PR zu. Bis das jemand beobachtet, ist
die sichere Annahme, dass es einen neuen Auslöser braucht.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

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

**ruff:** gepinnt auf `0.16.4`, nur im `dev`-Extra von `pyproject.toml`.
Eine `.pre-commit-config.yaml` existiert nicht — es gibt keinen zweiten Pin
und damit auch keine Abweichung. Lokal vor dem Push genügt
`uv pip install --system -e ".[dev]"`; ein separates ruff nachzuinstallieren
ist nicht mehr nötig.

Vorher stand der Pin in einer `uv pip install`-Zeile der CI, zusammen mit den
Test-Abhängigkeiten. Ein `dev`-Extra gab es nicht, weshalb der Install ein
`|| uv pip install -e .` als Fallback trug — der wich still auf eine
unvollständige Umgebung aus und liess den Fehler erst einen Schritt später
auftauchen, als «ruff not found» statt als «Extra fehlt». Beides ist weg.

Die Zahl hier wandert: Dependabot hebt den Pin an. Im Zweifel gilt
`pyproject.toml`, nicht diese Zeile.

Zweimal ist genau daran etwas gerissen. Nach `0.16.1 → 0.16.3` (PR #45) stand
die alte Zahl noch da; das Gate gab es damals noch nicht, und die Abweichung
blieb still. Nach dem Zug auf `0.16.4` gab es das Gate — und der Default-Branch
lag drei Tage rot (Läufe 127 und 128), weil niemand eine Prosazeile nachzog.
Ein vorhergesagter Fehler, den niemand behebt, ist kein Gate, sondern eine
Fussnote: Wer den roten Haken als bekannt abtut, hat sich angewöhnt, ihn zu
übersehen, und übersieht den nächsten mit.

Deshalb zieht der Nachzug jetzt von selbst: `python scripts/check_claude_md.py
--fix` schreibt die Zahl nach, und auf Dependabot-PRs tut das
`claude-md-nachziehen.yml` ungefragt. Was `--fix` kann und was bewusst nicht,
steht weiter unten bei «Diese Datei wird selbst geprüft».

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
`check_ruff_pin.py`, `check_version_sync.py`, `check_claude_md.py`,
`classify_live_run.py` und `record_fixtures.py`. Die Version ist `dynamic` und kommt aus
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

**`classify_live_run.py` entscheidet, ob `live-sources.yml` ein Issue anfasst.**
`if: failure()` und `if: success()` kennen zusammen zwei Antworten; ein
Live-Lauf hat drei. Die dritte ist `unknown`: Die Suite ist nicht gelaufen — ein
gescheitertes `uv pip install`, ein Timeout, eine umbenannte Marke — und über
die Quellen sagt der Lauf dann nichts.

Der teurere Fehler war die andere Richtung. Überspringt die Suite jeden Test,
endet pytest mit `0`; das traf `success()`, und der Aufräumschritt schloss ein
offenes Drift-Issue mit dem Satz «Die Quellen antworten wieder wie erwartet»,
ohne dass eine einzige Quelle gefragt worden wäre. Ein Melder, der auf einen
Nicht-Lauf hin entwarnt, ist schlimmer als keiner.

Deshalb liest die Einordnung das JUnit-XML statt des Exit-Codes: Der Exit-Code
sagt `0` für «alles grün» und für «alles übersprungen» dasselbe, das XML zählt
Tests, Übersprungene, Fehlschläge und Fehler getrennt. `finding` öffnet oder
kommentiert, `clear` schliesst, `unknown` lässt den Thread in Ruhe und macht den
Job rot. Sie steht in `scripts/` und nicht in einem `run:`-Block, weil der
einzige Teil des Workflows, der etwas behauptet, sonst an der einzigen Stelle
läge, an der ihn niemand testen kann — `tests/test_classify_live_run.py`.

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

**`--fix` zieht nach, statt nur zu melden.** Drei der vier Angaben lassen sich
aus ihren Quellen ableiten — Gate-Block, ruff-Pin, Live-Zahlen —, und genau die
hat bisher Handarbeit nachgetragen. Zwei Grenzen sind Absicht:

- Die **Skript-Liste** hat keine Reparatur. Ein unerwähntes Skript braucht
  einen Satz darüber, was es tut; den kann niemand aus dem Dateinamen ableiten,
  und eine erfundene Zeile wäre schlimmer als die rote Runde — sie machte das
  Gate grün über einer Angabe, die nie jemand geprüft hat.
- `--fix` korrigiert eine **falsche** Angabe, es stellt keine **entfernte**
  wieder her. Sonst wäre Löschen erneut der bequemste Weg am Gate vorbei,
  diesmal einer, den die Automatik selbst zuschüttet.

Repariert wird nie blind: Nach jeder Reparatur läuft dieselbe Prüfung noch
einmal über den neuen Text; greift sie nicht, endet der Lauf mit einem
`ReparaturError` statt mit einem grünen Haken über halber Arbeit. Und `ci.yml`
ruft den Check weiter **ohne** `--fix` auf — ein Gate, das sich selbst
repariert, kann nie rot werden. Beide Seiten dieser Trennung hält
`tests/test_check_claude_md.py` fest.

**`claude-md-nachziehen.yml` fährt `--fix` auf Dependabot-PRs** und committet
das Ergebnis auf den PR-Branch. Nur dort: Bei einem PR von Hand sitzt der Autor
davor und sieht das rote Gate, ein Bot-PR hat niemanden. Der Commit stammt vom
`GITHUB_TOKEN`, und daraus erzeugt GitHub keinen gewöhnlichen Folgelauf — der
PR-Haken bleibt am vorigen Commit stehen oder der neue Lauf wartet auf Freigabe.
Das ist ein Klick; die drei roten Tage auf `main` waren der Grund, und die
verhindert der Nachzug so oder so. Ein Kommentar am PR sagt es, damit niemand
den roten Haken für einen gescheiterten Nachzug hält.

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
auf keine der beiden Zählweisen passt. Alle drei Zahlen dieses Satzes prüft
`scripts/check_claude_md.py` — «12 deselected» gehört dazu, weil ein Nachzug an
nur einer Hälfte den Satz still in sich widersprüchlich machte.
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
