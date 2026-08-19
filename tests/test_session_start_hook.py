"""Gegenprobe fuer den SessionStart-Hook `.claude/hooks/session-start.sh`.

Die Zusicherungen des Hooks stehen in `.claude/hooks/README.md`; jede von
ihnen haengt hier an mindestens einem Test, der faellt, wenn man sie aus dem
Skript entfernt.

Kein Netz: die Remotes sind lokale Bare-Repos bzw. — fuer den Timeout-Pfad —
ein Socket, der annimmt und dann schweigt.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "session-start.sh"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git fehlt")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> None:
    (repo / "datei.txt").write_text(message, encoding="utf-8")
    _git(repo, "add", "datei.txt")
    _git(repo, "commit", "-m", message)


def _remote_head_entfernen(klon: Path) -> None:
    """`refs/remotes/origin/HEAD` ist ein symbolischer Ref — `update-ref -d`
    laesst ihn stehen und der Test prueft dann nicht, was er prueft."""
    _git(klon, "symbolic-ref", "-d", "refs/remotes/origin/HEAD")
    geblieben = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=klon,
        capture_output=True,
        text=True,
    )
    assert geblieben.returncode != 0, "Remote-HEAD steht noch — der Test prueft nichts"


def _run_hook(cwd: Path, timeout_seconds: str = "5") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(cwd),
            "CLAUDE_PROJECT_DIR": str(cwd),
            "CLAUDE_STALE_CLONE_TIMEOUT": timeout_seconds,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
        timeout=90,
    )


@pytest.fixture
def klon_hinter_remote(tmp_path: Path):
    """Baut Remote + Klon und gibt einen Regler fuer den Rueckstand zurueck.

    `default_branch` ist frei waehlbar — genau darauf zielt der Test, der
    `master` statt `main` verlangt.
    """

    def _bauen(default_branch: str = "main", commits_voraus: int = 0) -> Path:
        quelle = tmp_path / "quelle"
        quelle.mkdir()
        _git(quelle, "init", "-b", default_branch)
        _commit(quelle, "erster Commit")

        bare = tmp_path / "remote.git"
        _git(quelle, "clone", "--bare", str(quelle), str(bare))
        # Der Default-Branch des Remotes steht in dessen HEAD — den liest der
        # Hook aus, statt einen Namen anzunehmen.
        _git(bare, "symbolic-ref", "HEAD", f"refs/heads/{default_branch}")

        klon = tmp_path / "klon"
        _git(tmp_path, "clone", str(bare), str(klon))

        for nummer in range(commits_voraus):
            _commit(quelle, f"Remote-Commit {nummer + 1}")
        if commits_voraus:
            _git(quelle, "push", str(bare), default_branch)

        return klon

    return _bauen


def test_meldet_die_zahl_der_fehlenden_commits(klon_hinter_remote):
    klon = klon_hinter_remote(commits_voraus=3)

    ergebnis = _run_hook(klon)

    assert ergebnis.returncode == 0
    assert "3 Commits" in ergebnis.stdout
    assert "origin/main" in ergebnis.stdout


def test_singular_bei_genau_einem_fehlenden_commit(klon_hinter_remote):
    klon = klon_hinter_remote(commits_voraus=1)

    ergebnis = _run_hook(klon)

    assert "1 Commit hinter" in ergebnis.stdout
    assert "1 Commits" not in ergebnis.stdout


def test_schweigt_wenn_der_klon_aktuell_ist(klon_hinter_remote):
    klon = klon_hinter_remote(commits_voraus=0)

    ergebnis = _run_hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_default_branch_master_wird_ermittelt_nicht_angenommen(klon_hinter_remote):
    """Die Annahme `main` hat schon einmal einen Branch 15 Commits alt werden
    lassen. Ein fest verdrahtetes `origin/main` scheitert hier."""
    klon = klon_hinter_remote(default_branch="master", commits_voraus=2)

    ergebnis = _run_hook(klon)

    assert ergebnis.returncode == 0
    assert "2 Commits" in ergebnis.stdout
    assert "origin/master" in ergebnis.stdout
    assert "origin/main" not in ergebnis.stdout


def test_default_branch_wird_ohne_lokalen_remote_head_vom_remote_geholt(klon_hinter_remote):
    """Frische Klone in der Remote-Umgebung haben kein
    `refs/remotes/origin/HEAD` — dann muss `ls-remote --symref` einspringen."""
    klon = klon_hinter_remote(default_branch="master", commits_voraus=2)
    _remote_head_entfernen(klon)

    ergebnis = _run_hook(klon)

    assert "origin/master" in ergebnis.stdout


def test_detached_head_blockiert_nicht(klon_hinter_remote):
    klon = klon_hinter_remote(commits_voraus=2)
    _git(klon, "checkout", "--detach", "HEAD")

    ergebnis = _run_hook(klon)

    assert ergebnis.returncode == 0
    assert "detached HEAD" in ergebnis.stdout


def test_ohne_remote_still_und_ohne_fehler(tmp_path: Path):
    repo = tmp_path / "ohne-remote"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(repo, "erster Commit")

    ergebnis = _run_hook(repo)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert ergebnis.stderr == ""


def test_kein_git_repo_still_und_ohne_fehler(tmp_path: Path):
    kein_repo = tmp_path / "kein-repo"
    kein_repo.mkdir()

    ergebnis = _run_hook(kein_repo)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert ergebnis.stderr == ""


def test_repo_ohne_commits_still_und_ohne_fehler(tmp_path: Path):
    leer = tmp_path / "leer"
    leer.mkdir()
    _git(leer, "init", "-b", "main")

    ergebnis = _run_hook(leer)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_unerreichbares_remote_blockiert_nicht(klon_hinter_remote):
    """Kein Netz, kein Remote — der Hook geht still durch."""
    klon = klon_hinter_remote(commits_voraus=2)
    _git(klon, "remote", "set-url", "origin", "https://127.0.0.1:1/gibt-es-nicht.git")

    ergebnis = _run_hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_haengendes_remote_laeuft_ins_timeout_statt_in_den_sessionstart(klon_hinter_remote):
    """Ein Remote, das die Verbindung annimmt und dann schweigt, ist der Fall,
    den ein blosser Verbindungsfehler nicht abdeckt: ohne Timeout haengt hier
    der Sessionstart, bis jemand abbricht."""
    klon = klon_hinter_remote(commits_voraus=2)

    lauscher = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lauscher.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lauscher.bind(("127.0.0.1", 0))
    lauscher.listen(8)
    port = lauscher.getsockname()[1]
    stoppen = threading.Event()
    offen: list[socket.socket] = []

    def _annehmen_und_schweigen() -> None:
        lauscher.settimeout(0.5)
        while not stoppen.is_set():
            try:
                verbindung, _ = lauscher.accept()
            except (TimeoutError, OSError):
                continue
            offen.append(verbindung)

    thread = threading.Thread(target=_annehmen_und_schweigen, daemon=True)
    thread.start()
    try:
        _git(klon, "remote", "set-url", "origin", f"git://127.0.0.1:{port}/remote.git")
        # Ohne lokalen Remote-HEAD laeuft schon die Branch-Ermittlung ins Netz.
        _remote_head_entfernen(klon)

        start = time.monotonic()
        ergebnis = _run_hook(klon, timeout_seconds="2")
        gebraucht = time.monotonic() - start
    finally:
        stoppen.set()
        thread.join(timeout=5)
        for verbindung in offen:
            verbindung.close()
        lauscher.close()

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    # Grosszuegige Schranke: der Test soll das fehlende Timeout zeigen, nicht
    # die Laufzeit der CI-Maschine messen.
    assert gebraucht < 30, f"Hook lief {gebraucht:.1f}s — greift das Timeout nicht?"


def test_hook_ist_in_settings_json_registriert():
    import json

    settings = json.loads((HOOK.resolve().parents[1] / "settings.json").read_text(encoding="utf-8"))
    befehle = [
        eintrag["command"]
        for gruppe in settings["hooks"]["SessionStart"]
        for eintrag in gruppe["hooks"]
    ]
    assert any("session-start.sh" in befehl for befehl in befehle)


def test_hook_ist_ausfuehrbar():
    import os

    assert os.access(HOOK, os.X_OK), "ohne x-Bit startet der Hook nicht"


def test_der_grund_steht_dokumentiert():
    """Eine Zusicherung ohne ihren Grund wird beim naechsten Aufraeumen
    entfernt. Der Vorfall gehoert deshalb in den Text, nicht nur in einen
    Commit."""
    readme = (HOOK.resolve().parents[0] / "README.md").read_text(encoding="utf-8")
    skript = HOOK.read_text(encoding="utf-8")

    assert "3.8.2026" in readme
    assert "3.8.2026" in skript
    assert "rote CI" in readme
