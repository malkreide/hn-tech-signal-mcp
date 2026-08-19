#!/usr/bin/env bash
#
# Klon-Aktualitaet: meldet beim Sessionstart, wie viele Commits der
# ausgecheckte Stand hinter dem Default-Branch des Remotes liegt.
#
# GRUND
#   Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
#   Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau
#   die, die das Gate einfuehrten, an dem der Branch scheiterte. Die Pruefung
#   kostet eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# ZUSICHERUNGEN, in dieser Reihenfolge wichtig:
#   1. Der Hook blockiert die Session NIEMALS. Kein Netz, kein Remote,
#      kein Git-Repo, flatterndes DNS, unbekannter Default-Branch — jeder
#      dieser Faelle endet still mit Exit-Code 0. Ein Hook, der bei
#      Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal
#      abgeschaltet und schuetzt danach gar nichts.
#   2. Jeder Netzaufruf laeuft unter einem kurzen Timeout (Vorgabe 5 s),
#      damit der Sessionstart nicht haengt.
#   3. Ausgabe nur, wenn tatsaechlich Commits fehlen. Bei 0 schweigt er.
#   4. Der Default-Branch wird ermittelt, nicht als "main" angenommen —
#      drei Server im Portfolio heissen ihn "master", und genau diese
#      Annahme hat schon einmal einen Branch 15 Commits alt werden lassen.
#
# Details und Stellschrauben: .claude/hooks/README.md

# Bewusst kein `set -e`: ein fehlschlagendes Kommando darf hier nichts
# abbrechen, sondern nur zum stillen Ausstieg fuehren. Der EXIT-Trap ist die
# Rueckfallebene fuer alles, was die expliziten Guards unten nicht abfangen —
# er erzwingt Exit-Code 0 auf jedem Pfad.
set -u
trap 'exit 0' EXIT

readonly TIMEOUT_SECONDS="${CLAUDE_STALE_CLONE_TIMEOUT:-5}"

# Nichts darf interaktiv nachfragen: eine Passwort- oder Host-Key-Abfrage
# haengt sonst bis ins Timeout und kostet den Sessionstart genau die Sekunden,
# die dieser Hook sparen soll. Credential-Helper bleiben absichtlich aktiv —
# ohne sie koennte ein privates Repo gar nicht erst geprueft werden.
export GIT_TERMINAL_PROMPT=0
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=${TIMEOUT_SECONDS}"
unset GIT_ASKPASS SSH_ASKPASS 2>/dev/null || true

# `timeout` ist GNU-coreutils und fehlt auf macOS ohne Homebrew. Der
# Watchdog-Zweig unten haelt die Zusicherung auch dort.
TIMEOUT_BIN=""
for candidate in timeout gtimeout; do
    if command -v "$candidate" >/dev/null 2>&1; then
        TIMEOUT_BIN="$candidate"
        break
    fi
done

run_limited() {
    local seconds="$1"
    shift
    if [ -n "$TIMEOUT_BIN" ]; then
        "$TIMEOUT_BIN" -k 1 "$seconds" "$@"
        return $?
    fi
    "$@" &
    local job_pid=$!
    ( sleep "$seconds"; kill -TERM "$job_pid" ) >/dev/null 2>&1 &
    local watchdog_pid=$!
    wait "$job_pid"
    local status=$?
    kill -TERM "$watchdog_pid" >/dev/null 2>&1
    wait "$watchdog_pid" 2>/dev/null
    return $status
}

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0
# Ein Repo ohne Commits hat kein HEAD, gegen das sich zaehlen liesse.
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0

remote="origin"
if ! git remote get-url "$remote" >/dev/null 2>&1; then
    remote="$(git remote 2>/dev/null | head -n 1)"
fi
[ -n "$remote" ] || exit 0

# Default-Branch ermitteln, nicht raten. Zuerst der lokal notierte
# Remote-HEAD (kein Netz), sonst der Remote selbst. Faellt beides aus, wird
# nichts angenommen — lieber keine Meldung als eine gegen den falschen Branch.
default_branch=""
if symref="$(git symbolic-ref --short "refs/remotes/${remote}/HEAD" 2>/dev/null)"; then
    default_branch="${symref#"${remote}/"}"
fi
if [ -z "$default_branch" ]; then
    default_branch="$(
        run_limited "$TIMEOUT_SECONDS" git ls-remote --symref "$remote" HEAD 2>/dev/null |
            sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' |
            head -n 1
    )"
fi
[ -n "$default_branch" ] || exit 0

run_limited "$TIMEOUT_SECONDS" git fetch --quiet "$remote" "$default_branch" >/dev/null 2>&1 || exit 0

behind="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
# Alles ausser einer reinen Zahl ist ein Fehlerfall und schweigt.
case "$behind" in
    ''|*[!0-9]*) exit 0 ;;
    0) exit 0 ;;
esac

if [ "$behind" -eq 1 ]; then
    commit_word="Commit"
else
    commit_word="Commits"
fi

head_label="$(git symbolic-ref --short --quiet HEAD 2>/dev/null)"
[ -n "$head_label" ] || head_label="detached HEAD $(git rev-parse --short HEAD 2>/dev/null)"

cat <<EOF
[Klon-Aktualitaet] ${head_label} liegt ${behind} ${commit_word} hinter ${remote}/${default_branch}.

Angleichen vor der Arbeit:
    git fetch ${remote} ${default_branch} && git merge FETCH_HEAD

Grund: Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff
steht — es fehlen dann genau die Commits, die das Gate einfuehren, an dem der
Branch scheitert. Nicht in den geaenderten Dateien suchen, bevor dieser Stand
angeglichen ist.
EOF

exit 0
