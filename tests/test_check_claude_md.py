"""Gegenprobe fuer `scripts/check_claude_md.py`.

Der Check prueft eine Datei, die sonst niemand prueft. Faellt er still durch,
merkt es niemand — dieselbe Lage wie vorher, nur mit einem gruenen Haken
daneben. Jede seiner vier Zusicherungen wird hier einzeln neutralisiert.

Gearbeitet wird auf einem Miniatur-Repo in `tmp_path`: die Modulkonstanten
zeigen dorthin, damit die Faelle frei baubar sind. Zusaetzlich laeuft der
Check einmal gegen das echte Repo — sonst pruefte diese Datei nur ihre
eigenen Attrappen.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]


def pruefer():
    """Laedt `scripts/check_claude_md.py` als Modul, ohne `main()` zu rufen."""
    pfad = WURZEL / "scripts" / "check_claude_md.py"
    name = "check_claude_md_probe"
    spec = importlib.util.spec_from_file_location(name, pfad)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"{pfad} laesst sich nicht als Modul laden")
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    try:
        spec.loader.exec_module(modul)
    finally:
        del sys.modules[name]
    return modul


CI = """\
name: CI
jobs:
  test:
    steps:
      - name: Install
        run: uv pip install --system -e ".[dev]"
      - name: Lint
        run: ruff check src tests scripts
      - name: Sync
        run: python scripts/check_version_sync.py
"""

MD = """\
## Teil 2 — Dieses Repo

**ruff:** gepinnt auf `1.2.3`, nur im `dev`-Extra.

**Gates, wörtlich aus `ci.yml`** (Matrix):

```bash
ruff check src tests scripts
python scripts/check_version_sync.py
```

`scripts/` enthält `check_version_sync.py` und `record_fixtures.py`.

Live-Tests: 4 Fälle aus 2 Funktionen.
"""

PYPROJECT = """\
[project]
name = "demo"
dev = [
    "ruff==1.2.3",
]
"""

TESTDATEI = """\
import pytest


@pytest.mark.live
def test_eins():
    pass


@pytest.mark.live
@pytest.mark.parametrize("wert", ["a", "b", "c"])
def test_zwei(wert):
    pass


def test_ohne_marke():
    pass
"""


@pytest.fixture
def repo(tmp_path: Path, monkeypatch):
    """Ein stimmiges Miniatur-Repo; der Check muss darauf gruen sein."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(CI, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(MD, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    for name in ("check_version_sync.py", "record_fixtures.py"):
        (tmp_path / "scripts" / name).write_text("", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_demo.py").write_text(TESTDATEI, encoding="utf-8")

    modul = pruefer()
    monkeypatch.setattr(modul, "ROOT", tmp_path)
    monkeypatch.setattr(modul, "CLAUDE_MD", tmp_path / "CLAUDE.md")
    monkeypatch.setattr(modul, "CI_YML", tmp_path / ".github/workflows/ci.yml")
    monkeypatch.setattr(modul, "PYPROJECT", tmp_path / "pyproject.toml")
    monkeypatch.setattr(modul, "SCRIPTS", tmp_path / "scripts")
    monkeypatch.setattr(modul, "TESTS", tmp_path / "tests")
    return modul, tmp_path


def md_schreiben(wurzel: Path, alt: str, neu: str) -> None:
    pfad = wurzel / "CLAUDE.md"
    text = pfad.read_text(encoding="utf-8")
    assert alt in text, f"Vorlage passt nicht mehr: {alt!r}"
    pfad.write_text(text.replace(alt, neu, 1), encoding="utf-8")


def faellt(modul, capsys) -> str:
    with pytest.raises(SystemExit) as exit_info:
        modul.main()
    assert exit_info.value.code == 1
    return capsys.readouterr().err


def test_stimmiges_repo_ist_gruen(repo, capsys):
    modul, _ = repo
    modul.main()
    assert "CLAUDE.md OK" in capsys.readouterr().out


# --- 1. Gate-Block gegen ci.yml ------------------------------------------


def test_neuer_ci_schritt_ohne_eintrag_im_block_faellt(repo, capsys):
    modul, wurzel = repo
    ci = wurzel / ".github" / "workflows" / "ci.yml"
    ci.write_text(
        ci.read_text(encoding="utf-8") + "      - name: Neu\n        run: python neu.py\n",
        encoding="utf-8",
    )

    fehler = faellt(modul, capsys)
    assert "fehlt in CLAUDE.md: python neu.py" in fehler


def test_erfundener_schritt_im_block_faellt(repo, capsys):
    modul, wurzel = repo
    md_schreiben(
        wurzel,
        "python scripts/check_version_sync.py\n```",
        "python scripts/check_version_sync.py\npython scripts/gibt_es_nicht.py\n```",
    )

    fehler = faellt(modul, capsys)
    assert "nicht in ci.yml" in fehler


def test_install_schritt_gehoert_nicht_in_den_block(repo, capsys):
    """Der Install stellt die Umgebung her, statt zu pruefen — stuende er im
    Block, waere die Liste der Gates nicht mehr die Liste der Gates."""
    modul, wurzel = repo
    md_schreiben(
        wurzel,
        "```bash\nruff check",
        '```bash\nuv pip install --system -e ".[dev]"\nruff check',
    )

    assert "nicht in ci.yml" in faellt(modul, capsys)


def test_entfernter_gate_block_faellt(repo, capsys):
    modul, wurzel = repo
    md_schreiben(wurzel, "**Gates, wörtlich aus `ci.yml`**", "**Gates**")

    assert "nicht auffindbar" in faellt(modul, capsys)


# --- 2. ruff-Pin gegen pyproject.toml ------------------------------------


def test_angehobener_pin_ohne_nachzug_faellt(repo, capsys):
    """Genau der Fall, der zweimal unbemerkt blieb: Dependabot hebt den Pin,
    die Prosa bleibt stehen."""
    modul, wurzel = repo
    pfad = wurzel / "pyproject.toml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("1.2.3", "1.9.0"), encoding="utf-8")

    fehler = faellt(modul, capsys)
    assert "ruff-Pin weicht" in fehler
    assert "1.9.0" in fehler


def test_entfernte_pin_angabe_faellt(repo, capsys):
    modul, wurzel = repo
    md_schreiben(wurzel, "**ruff:** gepinnt auf `1.2.3`,", "**ruff:** gepinnt,")

    assert "nennt den ruff-Pin nicht mehr" in faellt(modul, capsys)


# --- 3. Skripte gegen scripts/ -------------------------------------------


def test_unerwaehntes_skript_faellt(repo, capsys):
    """Die wichtigere Richtung: `check_version_sync.py` lag monatelang
    unerwaehnt in `scripts/`, waehrend die Datei sein Gate bestritt."""
    modul, wurzel = repo
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")

    fehler = faellt(modul, capsys)
    assert "unerwähnt: check_neues.py" in fehler


def test_genanntes_skript_ohne_datei_faellt(repo, capsys):
    modul, wurzel = repo
    (wurzel / "scripts" / "record_fixtures.py").unlink()

    fehler = faellt(modul, capsys)
    assert "nicht in scripts/: record_fixtures.py" in fehler


# --- 4. Zahl der Live-Tests ----------------------------------------------


def test_neuer_live_test_ohne_nachzug_faellt(repo, capsys):
    modul, wurzel = repo
    pfad = wurzel / "tests" / "test_demo.py"
    pfad.write_text(
        pfad.read_text(encoding="utf-8") + "\n\n@pytest.mark.live\ndef test_drei():\n    pass\n",
        encoding="utf-8",
    )

    fehler = faellt(modul, capsys)
    assert "5 Fälle aus 3 Funktionen" in fehler


def test_geaenderte_parametrisierung_faellt(repo, capsys):
    """Die Fallzahl haengt an der Parametrisierung, nicht an der Zahl der
    Funktionen — genau die Differenz, die zur Angabe «11» gefuehrt hat."""
    modul, wurzel = repo
    pfad = wurzel / "tests" / "test_demo.py"
    pfad.write_text(
        pfad.read_text(encoding="utf-8").replace('["a", "b", "c"]', '["a", "b"]'),
        encoding="utf-8",
    )

    fehler = faellt(modul, capsys)
    assert "3 Fälle aus 2 Funktionen" in fehler


def test_entfernte_live_angabe_faellt(repo, capsys):
    modul, wurzel = repo
    md_schreiben(wurzel, "Live-Tests: 4 Fälle aus 2 Funktionen.", "Live-Tests: einige.")

    assert "nennt die Zahl der Live-Tests nicht mehr" in faellt(modul, capsys)


def test_dynamisches_parametrize_wird_gemeldet_statt_geraten(repo, capsys):
    """Raten waere hier das Schlechteste: der Check liefe, ohne zu pruefen."""
    modul, wurzel = repo
    pfad = wurzel / "tests" / "test_demo.py"
    pfad.write_text(
        pfad.read_text(encoding="utf-8").replace(
            '@pytest.mark.parametrize("wert", ["a", "b", "c"])',
            '@pytest.mark.parametrize("wert", list(range(3)))',
        ),
        encoding="utf-8",
    )

    fehler = faellt(modul, capsys)
    assert "nicht statisch auswertbar" in fehler
    assert "test_zwei" in fehler


# --- Sammelverhalten und echtes Repo -------------------------------------


def test_alle_befunde_stehen_in_einem_lauf(repo, capsys):
    """Zwei Abweichungen in zwei CI-Laeufen zu erfahren, kostet zwei Runden."""
    modul, wurzel = repo
    pfad = wurzel / "pyproject.toml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("1.2.3", "1.9.0"), encoding="utf-8")
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")

    fehler = faellt(modul, capsys)
    assert "ruff-Pin weicht" in fehler
    assert "unerwähnt: check_neues.py" in fehler


def test_das_echte_repo_besteht_den_check(capsys):
    """Ohne diesen Fall pruefte die Datei nur ihre eigenen Attrappen."""
    pruefer().main()
    assert "CLAUDE.md OK" in capsys.readouterr().out
