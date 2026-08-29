"""Gegenprobe fuer `scripts/check_claude_md.py`.

Der Check prueft eine Datei, die sonst niemand prueft. Faellt er still durch,
merkt es niemand — dieselbe Lage wie vorher, nur mit einem gruenen Haken
daneben. Jede seiner vier Zusicherungen wird hier einzeln neutralisiert.

Dazu `--fix`, das dieselben Angaben nachzieht statt sie nur zu melden. Eine
Automatik, die schreibt, braucht zwei Gegenproben mehr als eine, die liest:
dass sie genau dann schreibt, wenn etwas abweicht (und sonst die Datei nicht
anfasst), und dass sie nicht erfindet, was ihr niemand belegt hat.

Gearbeitet wird auf einem Miniatur-Repo in `tmp_path`: die Modulkonstanten
zeigen dorthin, damit die Faelle frei baubar sind. Zusaetzlich laeuft der
Check einmal gegen das echte Repo — sonst pruefte diese Datei nur ihre
eigenen Attrappen.
"""

from __future__ import annotations

import importlib.util
import os
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

Live-Tests: «4 deselected»: 4 Fälle aus 2 Funktionen.
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


def md(wurzel: Path) -> str:
    return (wurzel / "CLAUDE.md").read_text(encoding="utf-8")


def pin_anheben(wurzel: Path, neu: str) -> None:
    """Der Dependabot-Fall: die Zahl wandert in `pyproject.toml`, sonst nichts."""
    pfad = wurzel / "pyproject.toml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("1.2.3", neu), encoding="utf-8")


def ci_schritt_anhaengen(wurzel: Path, befehl: str) -> None:
    pfad = wurzel / ".github" / "workflows" / "ci.yml"
    pfad.write_text(
        pfad.read_text(encoding="utf-8") + f"      - name: Neu\n        run: {befehl}\n",
        encoding="utf-8",
    )


def live_test_anhaengen(wurzel: Path) -> None:
    pfad = wurzel / "tests" / "test_demo.py"
    pfad.write_text(
        pfad.read_text(encoding="utf-8") + "\n\n@pytest.mark.live\ndef test_drei():\n    pass\n",
        encoding="utf-8",
    )


def eingefroren(wurzel: Path) -> Path:
    """CLAUDE.md auf mtime 0 setzen — ein Schreibzugriff faellt danach auf.

    Ein Vergleich des Inhalts kann das nicht: Wer dieselben Bytes zurueck-
    schreibt, sieht darin genauso aus wie einer, der die Datei in Ruhe laesst.
    """
    pfad = wurzel / "CLAUDE.md"
    os.utime(pfad, (0, 0))
    return pfad


def faellt(modul, capsys, argv: list[str] | None = None) -> str:
    with pytest.raises(SystemExit) as exit_info:
        modul.main([] if argv is None else argv)
    assert exit_info.value.code == 1
    return capsys.readouterr().err


def test_stimmiges_repo_ist_gruen(repo, capsys):
    modul, _ = repo
    modul.main([])
    assert "CLAUDE.md OK" in capsys.readouterr().out


# --- 1. Gate-Block gegen ci.yml ------------------------------------------


def test_neuer_ci_schritt_ohne_eintrag_im_block_faellt(repo, capsys):
    modul, wurzel = repo
    ci_schritt_anhaengen(wurzel, "python neu.py")

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
    pin_anheben(wurzel, "1.9.0")

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
    live_test_anhaengen(wurzel)

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
    md_schreiben(wurzel, "4 Fälle aus 2 Funktionen.", "einige.")

    assert "nennt die Zahl der Live-Tests nicht mehr" in faellt(modul, capsys)


def test_entfernte_deselected_angabe_faellt(repo, capsys):
    """Die zweite Haelfte desselben Satzes. Bliebe sie ungeprueft, zoege ein
    Nachzug nur die eine Zahl nach und liesse den Satz sich widersprechen."""
    modul, wurzel = repo
    md_schreiben(wurzel, "«4 deselected»: ", "")

    assert "abgewählten Live-Tests nicht mehr" in faellt(modul, capsys)


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
    pin_anheben(wurzel, "1.9.0")
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")

    fehler = faellt(modul, capsys)
    assert "ruff-Pin weicht" in fehler
    assert "unerwähnt: check_neues.py" in fehler


def test_das_echte_repo_besteht_den_check(capsys):
    """Ohne diesen Fall pruefte die Datei nur ihre eigenen Attrappen."""
    pruefer().main([])
    assert "CLAUDE.md OK" in capsys.readouterr().out


# --- 5. `--fix`: nachziehen statt nur melden -----------------------------


def test_fix_zieht_den_pin_nach(repo, capsys):
    """Der Fall, der main dreimal getroffen hat, ohne eine Handbewegung."""
    modul, wurzel = repo
    pin_anheben(wurzel, "1.9.0")

    modul.main(["--fix"])

    ausgabe = capsys.readouterr().out
    assert "nachgezogen" in ausgabe
    assert "CLAUDE.md OK" in ausgabe
    assert "**ruff:** gepinnt auf `1.9.0`," in md(wurzel)


def test_fix_zieht_den_gate_block_nach(repo):
    modul, wurzel = repo
    ci_schritt_anhaengen(wurzel, "python neu.py")

    modul.main(["--fix"])

    assert modul.md_gates(md(wurzel)) == modul.ci_gates()


def test_fix_zieht_beide_live_zahlen_nach(repo):
    """Die Fallzahl steht zweimal im selben Satz. Zoege `--fix` nur eine nach,
    stuende der gruene Haken ueber einem Satz, der sich selbst widerspricht."""
    modul, wurzel = repo
    live_test_anhaengen(wurzel)

    modul.main(["--fix"])

    text = md(wurzel)
    assert "5 Fälle aus 3 Funktionen" in text
    assert "«5 deselected»" in text
    assert "«4 deselected»" not in text


def test_fix_stellt_eine_entfernte_angabe_nicht_wieder_her(repo, capsys):
    """Sonst waere Loeschen wieder der bequemste Weg am Gate vorbei — diesmal
    einer, den die Automatik selbst zuschuettet."""
    modul, wurzel = repo
    md_schreiben(wurzel, "**ruff:** gepinnt auf `1.2.3`,", "**ruff:** gepinnt,")
    pfad = eingefroren(wurzel)

    assert "nennt den ruff-Pin nicht mehr" in faellt(modul, capsys, ["--fix"])
    assert pfad.stat().st_mtime == 0


def test_fix_repariert_die_skriptliste_nicht(repo, capsys):
    """Ein unerwaehntes Skript braucht einen Satz darueber, was es tut. Den
    kann niemand aus dem Dateinamen ableiten — eine erfundene Zeile waere
    schlimmer als die rote Runde."""
    modul, wurzel = repo
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")
    pfad = eingefroren(wurzel)

    assert "unerwähnt: check_neues.py" in faellt(modul, capsys, ["--fix"])
    assert pfad.stat().st_mtime == 0


def test_fix_zieht_nach_und_meldet_den_rest(repo, capsys):
    """Ein Teillauf ist rot und hat trotzdem Arbeit abgenommen."""
    modul, wurzel = repo
    pin_anheben(wurzel, "1.9.0")
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")

    fehler = faellt(modul, capsys, ["--fix"])

    assert "unerwähnt: check_neues.py" in fehler
    assert "**ruff:** gepinnt auf `1.9.0`," in md(wurzel)


def test_ohne_fix_wird_die_datei_nicht_angefasst(repo, capsys):
    """Der Gate-Lauf in der CI liest, er schreibt nicht."""
    modul, wurzel = repo
    pin_anheben(wurzel, "1.9.0")
    pfad = eingefroren(wurzel)

    assert "ruff-Pin weicht" in faellt(modul, capsys, [])
    assert pfad.stat().st_mtime == 0


def test_fix_ruehrt_ein_stimmiges_repo_nicht_an(repo, capsys):
    modul, wurzel = repo
    pfad = eingefroren(wurzel)

    modul.main(["--fix"])

    assert pfad.stat().st_mtime == 0
    assert "nachgezogen" not in capsys.readouterr().out


def test_ein_ableitbarer_befund_nennt_den_weg_ohne_handarbeit(repo, capsys):
    modul, wurzel = repo
    pin_anheben(wurzel, "1.9.0")

    assert "--fix" in faellt(modul, capsys, [])


def test_ein_nicht_ableitbarer_befund_verspricht_kein_fix(repo, capsys):
    """Der Hinweis waere sonst ein Versprechen, das der naechste Lauf bricht."""
    modul, wurzel = repo
    (wurzel / "scripts" / "check_neues.py").write_text("", encoding="utf-8")

    assert "--fix" not in faellt(modul, capsys, [])


def test_eine_wirkungslose_reparatur_faellt_laut_auf(repo, monkeypatch):
    """Eine Reparatur, die ihren eigenen Befund nicht ausraeumt, darf nicht als
    Erfolg durchgehen: sonst stuende ein gruener Haken ueber halber Arbeit."""
    modul, wurzel = repo
    pin_anheben(wurzel, "1.9.0")
    monkeypatch.setattr(modul, "PRUEFUNGEN", ((modul.pruefe_ruff_pin, lambda text: text),))
    pfad = eingefroren(wurzel)

    with pytest.raises(modul.ReparaturError) as info:
        modul.main(["--fix"])

    assert "wirkungslos" in str(info.value)
    assert pfad.stat().st_mtime == 0


def test_das_echte_repo_braucht_keine_reparatur():
    """Wie beim Check selbst: ohne diesen Fall pruefte die Datei nur ihre
    eigenen Attrappen. Bewusst ueber die Reparaturen statt ueber `main()` —
    ein Test darf die echte CLAUDE.md nicht schreiben, auch nicht aus Versehen.
    """
    modul = pruefer()
    text = modul.CLAUDE_MD.read_text(encoding="utf-8")

    for _, reparatur in modul.PRUEFUNGEN:
        if reparatur is not None:
            assert reparatur(text) == text


# --- 6. Wer repariert, und wer nur prueft --------------------------------

CI_YML = WURZEL / ".github" / "workflows" / "ci.yml"
NACHZIEHEN_YML = WURZEL / ".github" / "workflows" / "claude-md-nachziehen.yml"


def aufrufe_des_checks(workflow: Path) -> list[str]:
    """Die `run:`-Zeilen, die den Check starten — nicht die, die ihn erwaehnen.

    Ein blosses `"check_claude_md.py --fix" in text` war hier schon einmal
    gruen, obwohl der Aufruf selbst das Flag verloren hatte: Ein Kommentar und
    eine Fehlermeldung im selben Workflow nennen dieselbe Zeichenkette.
    """
    return [
        zeile
        for zeile in workflow.read_text(encoding="utf-8").splitlines()
        if zeile.strip().startswith("run:") and "check_claude_md.py" in zeile
    ]


def test_das_gate_in_der_ci_repariert_nicht():
    """Ein Gate, das sich selbst repariert, kann nie rot werden."""
    aufrufe = aufrufe_des_checks(CI_YML)

    assert aufrufe, "ci.yml ruft den Check nicht mehr auf"
    assert all("--fix" not in zeile for zeile in aufrufe)


def test_der_nachzieh_workflow_faehrt_den_check_mit_fix():
    aufrufe = aufrufe_des_checks(NACHZIEHEN_YML)

    assert aufrufe, "der Nachzieh-Workflow ruft den Check nicht mehr auf"
    assert all("--fix" in zeile for zeile in aufrufe)


def test_der_nachzieh_workflow_laeuft_nur_fuer_dependabot():
    """Ungefragt in fremde Branches zu schreiben waere die groessere
    Ueberraschung als eine rote Runde."""
    assert "if: github.actor == 'dependabot[bot]'" in NACHZIEHEN_YML.read_text(encoding="utf-8")


def test_der_nachzieh_workflow_committet_nur_claude_md():
    """Ein Bot, der mehr mitnimmt als angekuendigt, ist schwerer zu pruefen
    als eine rote Runde."""
    text = NACHZIEHEN_YML.read_text(encoding="utf-8")

    assert "git add -- CLAUDE.md" in text
    assert "git add -A" not in text
    assert "git add ." not in text
