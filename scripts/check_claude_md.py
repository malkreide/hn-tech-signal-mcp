"""
`CLAUDE.md` gegen die Dateien prüfen, über die sie Aussagen macht.

Anlass: Die Angaben in Teil 2 sind zweimal verrottet, ohne dass etwas rot
wurde. Beim zweiten Mal stand dort das Gegenteil der Wahrheit — «es gibt kein
Versions-Sync-Gate», während `ci.yml` es längst aufrief. Eine Konventionsdatei,
die eine bestehende Prüfung *bestreitet*, kostet mehr als eine, die schweigt:
Wer eine Version anhebt, sucht das rote Gate zuerst an der falschen Stelle.

Geprüft wird nur, was mechanisch belegbar ist:

  1. der Gate-Block gegen die `run:`-Schritte aus `ci.yml` — die Datei
     behauptet selbst, er stehe dort «wörtlich»
  2. der zitierte ruff-Pin gegen `pyproject.toml` — Dependabot hebt ihn an,
     die Prosa zieht nicht mit
  3. die erwähnten Skripte gegen `scripts/`, in beide Richtungen: ein
     genanntes Skript muss existieren, ein vorhandenes genannt sein
  4. die Zahl der Live-Tests gegen die Testdateien — «11» passte zuletzt auf
     keine der beiden Zählweisen

NICHT geprüft und weiterhin Handarbeit: die Zahl der aufgezeichneten Antworten
(46 = 42 JSON + 4 XML, steht in `PROVENANCE.md`), die Beschreibung von
`live-sources.yml` und alle Aussagen, die eine Begründung statt einer Zahl
tragen. Das ist keine Lücke aus Versehen: Prosa, die man nur schwer maschinell
fassen kann, würde als Fehlalarm enden, und ein Gate mit Fehlalarmen wird
abgeschaltet — dann schützt es gar nichts mehr.

Jede geprüfte Angabe muss vorhanden sein. Wer sie herausnimmt, statt sie zu
korrigieren, fällt hier ebenfalls — sonst wäre das Löschen der bequemste Weg
an diesem Gate vorbei.

Verwendung:
    python scripts/check_claude_md.py     # exit 1 bei Abweichung

Bewusst nur Standardbibliothek, wie `check_ruff_pin.py` und
`check_version_sync.py`, und wie diese keine Zeile über 88 Zeichen. Der Grund
gilt dort stärker als hier — jene Dateien werden zwischen Repos mit
`line-length` 88 bis 120 kopiert, und `ruff format` zieht Ausdrücke je nach
Breite anders zusammen. Diese hier ist repo-eigen; die Breite mitzuhalten
kostet nichts und erspart die Frage, warum eine von dreien ausschert.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = ROOT / "CLAUDE.md"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = ROOT / "pyproject.toml"
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"

# Der Install-Schritt ist kein Gate: er stellt die Umgebung her, statt etwas
# zu prüfen. Er steht deshalb bewusst nicht im Block.
KEIN_GATE = ("uv pip install",)


class BefundError(Exception):
    """Eine Abweichung samt Anleitung, wie sie aufzulösen ist."""

    def __init__(self, titel: str, zeilen: list[str], rat: str) -> None:
        super().__init__(titel)
        self.titel = titel
        self.zeilen = zeilen
        self.rat = rat


def ci_gates() -> list[str]:
    """Die `run:`-Schritte aus `ci.yml`, ohne den Install-Schritt.

    Absichtlich per Regex und nicht per YAML-Parser: `yaml` ist keine
    Standardbibliothek, und eine Abhängigkeit einzuführen, damit ein Check
    laufen kann, wäre unverhältnismässig.
    """
    text = CI_YML.read_text(encoding="utf-8")
    runs = [m.strip() for m in re.findall(r"^\s+run: (.+)$", text, re.MULTILINE)]
    return [r for r in runs if not any(k in r for k in KEIN_GATE)]


def md_gates(text: str) -> list[str]:
    """Der Gate-Block aus `CLAUDE.md`."""
    block = re.search(
        r"\*\*Gates, wörtlich aus `ci\.yml`\*\*.*?```bash\n(.*?)```",
        text,
        re.DOTALL,
    )
    if block is None:
        raise BefundError(
            "Der Gate-Block ist nicht auffindbar.",
            ["erwartet: **Gates, wörtlich aus `ci.yml`** gefolgt von ```bash"],
            "Überschrift und Block wiederherstellen — dieser Check hängt "
            "daran, und ohne ihn prüft niemand mehr, ob die Liste stimmt.",
        )
    return [z.strip() for z in block.group(1).strip().splitlines() if z.strip()]


def pruefe_gates(text: str) -> str:
    erwartet = ci_gates()
    steht_da = md_gates(text)
    if erwartet == steht_da:
        return f"Gate-Block ({len(erwartet)} Schritte)"

    zeilen = []
    for gate in erwartet:
        if gate not in steht_da:
            zeilen.append(f"fehlt in CLAUDE.md: {gate}")
    for gate in steht_da:
        if gate not in erwartet:
            zeilen.append(f"steht in CLAUDE.md, nicht in ci.yml: {gate}")
    if not zeilen:
        zeilen.append("gleiche Schritte, andere Reihenfolge als in ci.yml")
    raise BefundError(
        "Der Gate-Block weicht von ci.yml ab.",
        zeilen,
        "Den Block an ci.yml angleichen. Die Datei sagt «wörtlich» — wer "
        "einen Schritt hinzufügt, trägt ihn hier nach.",
    )


def pruefe_ruff_pin(text: str) -> str:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    gepinnt = re.search(r'ruff==([0-9]+\.[0-9]+\.[0-9]+)"', pyproject)
    if gepinnt is None:
        raise BefundError(
            "In pyproject.toml steht kein ruff-Pin.",
            [],
            "Ohne Pin fallen die Gates je nach Umgebung anders aus.",
        )
    zitiert = re.search(r"\*\*ruff:\*\* gepinnt auf `([0-9][^`]*)`", text)
    if zitiert is None:
        raise BefundError(
            "CLAUDE.md nennt den ruff-Pin nicht mehr.",
            ["erwartet: **ruff:** gepinnt auf `X.Y.Z`"],
            "Die Angabe wiederherstellen, statt sie zu entfernen.",
        )
    if zitiert.group(1) != gepinnt.group(1):
        raise BefundError(
            "Der zitierte ruff-Pin weicht von pyproject.toml ab.",
            [
                f"CLAUDE.md:     {zitiert.group(1)}",
                f"pyproject.toml: {gepinnt.group(1)}",
            ],
            "CLAUDE.md nachziehen — Dependabot hebt den Pin, die Prosa nicht.",
        )
    return f"ruff-Pin ({gepinnt.group(1)})"


def pruefe_skripte(text: str) -> str:
    """Genannte Skripte müssen existieren, vorhandene genannt sein.

    Die zweite Richtung ist die wichtigere: `check_version_sync.py` lag
    monatelang unerwähnt in `scripts/`, und die Datei behauptete daneben, es
    gäbe kein solches Gate.
    """
    vorhanden = {p.name for p in SCRIPTS.glob("*.py")}
    genannt = set(re.findall(r"`(?:scripts/)?([a-z_]+\.py)`", text))

    fehlt_auf_platte = sorted(genannt - vorhanden)
    unerwaehnt = sorted(vorhanden - genannt)
    if fehlt_auf_platte or unerwaehnt:
        zeilen = [f"genannt, aber nicht in scripts/: {n}" for n in fehlt_auf_platte]
        zeilen += [f"in scripts/, aber unerwähnt: {n}" for n in unerwaehnt]
        raise BefundError(
            "Die erwähnten Skripte decken sich nicht mit scripts/.",
            zeilen,
            "Ein ungenanntes Skript findet niemand, ein genanntes ohne "
            "Datei schickt auf die falsche Fährte.",
        )
    return f"Skripte ({len(vorhanden)} in scripts/)"


def _ist_live_mark(deko: ast.expr) -> bool:
    return (
        isinstance(deko, ast.Attribute)
        and deko.attr == "live"
        and isinstance(deko.value, ast.Attribute)
        and deko.value.attr == "mark"
    )


def _faelle(deko: ast.expr) -> int | None:
    """Anzahl der Fälle eines `parametrize`-Dekorators, oder None.

    None heisst «nicht statisch auswertbar» — dann kann dieser Check die
    Fallzahl nicht belegen und sagt das, statt zu raten.
    """
    if not isinstance(deko, ast.Call):
        return None
    ziel = deko.func
    if not (isinstance(ziel, ast.Attribute) and ziel.attr == "parametrize"):
        return None
    if len(deko.args) < 2:
        return None
    try:
        return len(ast.literal_eval(deko.args[1]))
    except (ValueError, SyntaxError, TypeError):
        return None


def zaehle_live() -> tuple[int, int]:
    """(Fälle, Funktionen) der `@pytest.mark.live`-Tests."""
    funktionen = 0
    faelle = 0
    unklar: list[str] = []
    for pfad in sorted(TESTS.rglob("*.py")):
        baum = ast.parse(pfad.read_text(encoding="utf-8"))
        for knoten in ast.walk(baum):
            if not isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(_ist_live_mark(d) for d in knoten.decorator_list):
                continue
            funktionen += 1
            eigene = 1
            for deko in knoten.decorator_list:
                anzahl = _faelle(deko)
                if anzahl is None and isinstance(deko, ast.Call):
                    ziel = deko.func
                    if isinstance(ziel, ast.Attribute) and ziel.attr == "parametrize":
                        unklar.append(knoten.name)
                        continue
                if anzahl is not None:
                    eigene *= anzahl
            faelle += eigene
    if unklar:
        raise BefundError(
            "Die Fallzahl der Live-Tests ist nicht statisch auswertbar.",
            [f"dynamisches parametrize in: {name}" for name in sorted(set(unklar))],
            "Entweder die Werte als Literal schreiben, oder diesen Check um "
            "die neue Form erweitern. Eine ungeprüfte Zahl in CLAUDE.md wäre "
            "genau das, was hier verhindert werden soll.",
        )
    return faelle, funktionen


def pruefe_live(text: str) -> str:
    zitiert = re.search(r"(\d+) Fälle aus (\d+) Funktionen", text)
    if zitiert is None:
        raise BefundError(
            "CLAUDE.md nennt die Zahl der Live-Tests nicht mehr.",
            ["erwartet: «N Fälle aus M Funktionen»"],
            "Die Angabe wiederherstellen, statt sie zu entfernen.",
        )
    faelle, funktionen = zaehle_live()
    steht_da = (int(zitiert.group(1)), int(zitiert.group(2)))
    if steht_da != (faelle, funktionen):
        raise BefundError(
            "Die Zahl der Live-Tests weicht ab.",
            [
                f"CLAUDE.md: {steht_da[0]} Fälle aus {steht_da[1]} Funktionen",
                f"gezählt:   {faelle} Fälle aus {funktionen} Funktionen",
            ],
            "Beide Zahlen nachziehen. Sie unterscheiden sich, weil ein Test "
            "parametrisiert ist — wer nur eine nennt, erzeugt die nächste "
            "Verwirrung.",
        )
    return f"Live-Tests ({faelle} Fälle aus {funktionen} Funktionen)"


def main() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    geprueft: list[str] = []
    befunde: list[BefundError] = []

    # Alle Prüfungen laufen, auch wenn eine fällt: zwei Abweichungen in zwei
    # CI-Läufen zu erfahren, kostet zwei Runden statt einer.
    for pruefung in (pruefe_gates, pruefe_ruff_pin, pruefe_skripte, pruefe_live):
        try:
            geprueft.append(pruefung(text))
        except BefundError as b:
            befunde.append(b)

    if befunde:
        print("CLAUDE.md weicht vom Repo ab:", file=sys.stderr)
        for b in befunde:
            print(f"\n  {b.titel}", file=sys.stderr)
            for zeile in b.zeilen:
                print(f"    {zeile}", file=sys.stderr)
            print(f"    -> {b.rat}", file=sys.stderr)
        sys.exit(1)

    print(f"CLAUDE.md OK (geprüft: {'; '.join(geprueft)})")


if __name__ == "__main__":
    main()
