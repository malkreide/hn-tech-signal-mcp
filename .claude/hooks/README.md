# SessionStart-Hook: Klon-Aktualitaet

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter dem Default-Branch des Remotes liegt. Registriert
ist er in `.claude/settings.json` unter `hooks.SessionStart`.

## Grund

Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einfuehrten, an dem der Branch scheiterte. Gesucht wurde beide
Male in den geaenderten Dateien, wo nichts zu finden war. Die Pruefung kostet
eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.

Das ist dieselbe Pruefung, die `CLAUDE.md` unter «Vor der Arbeit» von Hand
verlangt. Von Hand heisst: wer sie vergisst, merkt es erst an der roten CI.

## Zusicherungen

In dieser Reihenfolge wichtig:

1. **Der Hook blockiert die Session niemals.** Kein Netz, kein Remote, kein
   Git-Repo, detached HEAD, flatterndes DNS, nicht ermittelbarer
   Default-Branch — jeder dieser Faelle endet still mit Exit-Code 0. Ein Hook,
   der bei Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal
   abgeschaltet und schuetzt danach gar nichts. Durchgesetzt wird das doppelt:
   jeder Schritt hat einen expliziten `|| exit 0`-Guard, und ein
   `trap 'exit 0' EXIT` faengt ab, was die Guards nicht abdecken. `set -e`
   steht bewusst **nicht** im Skript.
2. **Kurzes Timeout auf jeden Netzaufruf** (Vorgabe 5 s, einstellbar ueber
   `CLAUDE_STALE_CLONE_TIMEOUT`), damit der Sessionstart nicht haengt.
   Zusaetzlich ist alles Interaktive abgeschaltet (`GIT_TERMINAL_PROMPT=0`,
   `ssh -o BatchMode=yes`): eine Passwortabfrage wuerde sonst bis ins Timeout
   haengen. Credential-Helper bleiben aktiv — ohne sie waere ein privates
   Repo gar nicht pruefbar.
3. **Ausgabe nur, wenn Commits fehlen.** Bei 0 schweigt er. Ein Melder, der
   bei jedem Start etwas sagt, wird ueberlesen.
4. **Der Default-Branch wird ermittelt, nicht angenommen.** Erst der lokal
   notierte `refs/remotes/<remote>/HEAD` (ohne Netz), sonst
   `git ls-remote --symref`. Faellt beides aus, wird **nicht** auf `main`
   geraten, sondern geschwiegen. Drei Server im Portfolio (`openlex-mcp`,
   `swiss-courts-mcp`, `swisstopo-mcp`) heissen ihren Default-Branch
   `master`; die Annahme `main` hat dort schon einmal einen Branch
   15 Commits alt werden lassen.

## Bewusste Entscheidungen

- **Laeuft lokal wie remote.** Es gibt kein `$CLAUDE_CODE_REMOTE`-Gate: ein
  Klon veraltet auf dem Laptop genauso wie in einem wiederverwendeten
  Container, und die rote CI sieht in beiden Faellen gleich aus.
- **Bei detached HEAD wird gemeldet, nicht geschwiegen.** Der Zaehler stimmt
  dort genauso, und ein 15 Commits alter detached HEAD erzeugt genau die CI,
  gegen die der Hook existiert. Er blockiert dabei nichts — «still
  durchgehen» heisst hier: kein Abbruch, nicht: keine Meldung. Wer bewusst
  auf einem alten Tag arbeitet und die Zeile nicht will, entfernt den
  `head_label`-Zweig oder setzt `CLAUDE_STALE_CLONE_TIMEOUT=0`.
- **`FETCH_HEAD` statt `origin/<branch>`** als Vergleichspunkt, gleich wie in
  `CLAUDE.md` — dasselbe Ergebnis, aber unabhaengig davon, ob im Klon
  ueberhaupt ein Remote-Tracking-Ref fuer den Default-Branch existiert.

## Aendern

Nach jeder Aenderung die Gegenprobe fahren; die Zusicherungen oben haengen an
`tests/test_session_start_hook.py`:

```bash
PYTHONPATH=src pytest tests/test_session_start_hook.py -v
```

Jede Zusicherung ist dort einzeln neutralisierbar — wer eine entfernt, muss
genau die zugehoerigen Tests fallen sehen.

Von Hand ausprobieren:

```bash
CLAUDE_PROJECT_DIR="$PWD" ./.claude/hooks/session-start.sh; echo "exit=$?"
```

Ein aktueller Klon gibt nichts aus und endet mit `exit=0`.
