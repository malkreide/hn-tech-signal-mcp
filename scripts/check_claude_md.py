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
     keine der beiden Zählweisen; geprüft werden beide Stellen desselben
     Satzes, «N deselected» und «N Fälle aus M Funktionen», weil ein Nachzug
     an nur einer von beiden den Satz still in sich widersprüchlich macht

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
    python scripts/check_claude_md.py         # exit 1 bei Abweichung
    python scripts/check_claude_md.py --fix   # Zahlen nachziehen

`--fix` zieht nach, was aus den Quelldateien ableitbar ist: den Gate-Block,
den ruff-Pin und die beiden Live-Zahlen. Anlass ist der Fall, der diesen
Check zweimal ausgelöst hat — Dependabot hebt den Pin in `pyproject.toml`,
und main liegt rot, bis jemand eine Prosazeile nachzieht. Beim Zug auf 0.16.4
waren das drei Tage. Ein vorhergesagter Fehler, den nur Handarbeit behebt,
wird irgendwann als bekannt abgetan.

Zwei Grenzen, beide absichtlich:

  * Die Skript-Liste hat keine Reparatur. Ein unerwähntes Skript braucht
    einen Satz darüber, was es tut — den kann niemand aus dem Dateinamen
    ableiten, und eine erfundene Zeile wäre schlimmer als die rote Runde:
    sie machte das Gate grün über einer Angabe, die nie jemand geprüft hat.
  * `--fix` stellt keine *entfernte* Aussage wieder her, es korrigiert nur
    eine falsche. Sonst wäre Löschen wieder der bequemste Weg am Gate vorbei
    — diesmal einer, den die Automatik selbst zuschüttet.

Repariert wird nie blind: nach jeder Reparatur läuft dieselbe Prüfung noch
einmal über den neuen Text. Greift sie nicht, endet der Lauf mit einem
`ReparaturError` statt mit einem grünen Haken über einer halben Änderung.
`ci.yml` ruft den Check bewusst ohne `--fix` auf — ein Gate, das sich selbst
repariert, kann nie rot werden.

Bewusst nur Standardbibliothek, wie `check_ruff_pin.py` und
`check_version_sync.py`, und wie diese keine Zeile über 88 Zeichen. Der Grund
gilt dort stärker als hier — jene Dateien werden zwischen Repos mit
`line-length` 88 bis 120 kopiert, und `ruff format` zieht Ausdrücke je nach
Breite anders zusammen. Diese hier ist repo-eigen; die Breite mitzuhalten
kostet nichts und erspart die Frage, warum eine von dreien ausschert.
"""

import argparse
import ast
import re
import sys
from collections.abc import Callable
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

FIX_FLAG = "--fix"

# Je Angabe ein Ausdruck, den Prüfung und Reparatur teilen: zwei getrennte
# Muster für dieselbe Stelle wären die nächste Abweichung, die niemand sieht.
GATE_BLOCK = re.compile(
    r"(\*\*Gates, wörtlich aus `ci\.yml`\*\*.*?```bash\n)(.*?)(```)",
    re.DOTALL,
)
RUFF_PIN = re.compile(r'ruff==([0-9]+\.[0-9]+\.[0-9]+)"')
RUFF_ZITAT = re.compile(r"(\*\*ruff:\*\* gepinnt auf `)([0-9][^`]*)(`)")
LIVE_ANGABE = re.compile(r"(\d+) Fälle aus (\d+) Funktionen")
LIVE_ABGEWAEHLT = re.compile(r"«(\d+) deselected»")


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
    block = GATE_BLOCK.search(text)
    if block is None:
        raise BefundError(
            "Der Gate-Block ist nicht auffindbar.",
            ["erwartet: **Gates, wörtlich aus `ci.yml`** gefolgt von ```bash"],
            "Überschrift und Block wiederherstellen — dieser Check hängt "
            "daran, und ohne ihn prüft niemand mehr, ob die Liste stimmt.",
        )
    return [z.strip() for z in block.group(2).strip().splitlines() if z.strip()]


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


def repariere_gates(text: str) -> str | None:
    """Den Block durch die `run:`-Schritte aus `ci.yml` ersetzen."""
    if GATE_BLOCK.search(text) is None:
        return None
    block = "\n".join(ci_gates()) + "\n"
    return GATE_BLOCK.sub(lambda m: m.group(1) + block + m.group(3), text, count=1)


def pin_aus_pyproject() -> str:
    gepinnt = RUFF_PIN.search(PYPROJECT.read_text(encoding="utf-8"))
    if gepinnt is None:
        raise BefundError(
            "In pyproject.toml steht kein ruff-Pin.",
            [],
            "Ohne Pin fallen die Gates je nach Umgebung anders aus.",
        )
    return gepinnt.group(1)


def pruefe_ruff_pin(text: str) -> str:
    gepinnt = pin_aus_pyproject()
    zitiert = RUFF_ZITAT.search(text)
    if zitiert is None:
        raise BefundError(
            "CLAUDE.md nennt den ruff-Pin nicht mehr.",
            ["erwartet: **ruff:** gepinnt auf `X.Y.Z`"],
            "Die Angabe wiederherstellen, statt sie zu entfernen.",
        )
    if zitiert.group(2) != gepinnt:
        raise BefundError(
            "Der zitierte ruff-Pin weicht von pyproject.toml ab.",
            [
                f"CLAUDE.md:     {zitiert.group(2)}",
                f"pyproject.toml: {gepinnt}",
            ],
            "CLAUDE.md nachziehen — Dependabot hebt den Pin, die Prosa nicht.",
        )
    return f"ruff-Pin ({gepinnt})"


def repariere_ruff_pin(text: str) -> str | None:
    if RUFF_ZITAT.search(text) is None:
        return None
    gepinnt = pin_aus_pyproject()
    return RUFF_ZITAT.sub(lambda m: m.group(1) + gepinnt + m.group(3), text, count=1)


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
    zitiert = LIVE_ANGABE.search(text)
    if zitiert is None:
        raise BefundError(
            "CLAUDE.md nennt die Zahl der Live-Tests nicht mehr.",
            ["erwartet: «N Fälle aus M Funktionen»"],
            "Die Angabe wiederherstellen, statt sie zu entfernen.",
        )
    # Dieselbe Zahl steht im selben Satz ein zweites Mal, als das, was
    # `ci.yml` per `-m "not live"` abwählt. Bliebe sie ungeprüft, zöge ein
    # Nachzug nur die eine Hälfte nach und liesse den Satz sich selbst
    # widersprechen — grün, und trotzdem falsch.
    abgewaehlt = LIVE_ABGEWAEHLT.search(text)
    if abgewaehlt is None:
        raise BefundError(
            "CLAUDE.md nennt die Zahl der abgewählten Live-Tests nicht mehr.",
            ["erwartet: «N deselected»"],
            "Die Angabe wiederherstellen, statt sie zu entfernen. Sie ist "
            "das, was ein CI-Lauf tatsächlich ausgibt — daran prüft ein "
            "Leser die Zahl nach, ohne etwas zu zählen.",
        )
    faelle, funktionen = zaehle_live()
    steht_da = (
        int(zitiert.group(1)),
        int(zitiert.group(2)),
        int(abgewaehlt.group(1)),
    )
    if steht_da != (faelle, funktionen, faelle):
        ist = f"{steht_da[0]} Fälle aus {steht_da[1]} Funktionen"
        soll = f"{faelle} Fälle aus {funktionen} Funktionen"
        raise BefundError(
            "Die Zahl der Live-Tests weicht ab.",
            [
                f"CLAUDE.md: {ist}, «{steht_da[2]} deselected»",
                f"gezählt:   {soll}, «{faelle} deselected»",
            ],
            "Alle drei Zahlen nachziehen. Fälle und Funktionen unterscheiden "
            "sich, weil ein Test parametrisiert ist — wer nur eine nennt, "
            "erzeugt die nächste Verwirrung.",
        )
    return f"Live-Tests ({faelle} Fälle aus {funktionen} Funktionen)"


def repariere_live(text: str) -> str | None:
    if LIVE_ANGABE.search(text) is None or LIVE_ABGEWAEHLT.search(text) is None:
        return None
    faelle, funktionen = zaehle_live()
    angabe = f"{faelle} Fälle aus {funktionen} Funktionen"
    text = LIVE_ABGEWAEHLT.sub(f"«{faelle} deselected»", text, count=1)
    return LIVE_ANGABE.sub(angabe, text, count=1)


Pruefung = Callable[[str], str]
Reparatur = Callable[[str], "str | None"]

# Prüfung → Reparatur; `None` heisst «nicht mechanisch ableitbar». Warum
# `pruefe_skripte` bewusst keine hat, steht oben im Modul-Docstring.
PRUEFUNGEN: tuple[tuple[Pruefung, Reparatur | None], ...] = (
    (pruefe_gates, repariere_gates),
    (pruefe_ruff_pin, repariere_ruff_pin),
    (pruefe_skripte, None),
    (pruefe_live, repariere_live),
)


class ReparaturError(Exception):
    """Eine Reparatur hat ihren Befund nicht ausgeräumt.

    Das ist ein Fehler in diesem Skript, keine Abweichung in CLAUDE.md, und
    darf deshalb nicht wie ein Befund aussehen: sonst schriebe `--fix` eine
    halbe Änderung in die Datei und meldete daneben brav denselben Befund
    wie zuvor. Ein Abbruch mit Traceback ist hier das Ehrlichere.
    """

    def __init__(self, vorher: BefundError, nachher: BefundError) -> None:
        super().__init__(
            f"Reparatur wirkungslos: «{vorher.titel}» — danach: "
            f"«{nachher.titel}». CLAUDE.md wurde nicht geschrieben."
        )


def _pruefe(pruefung: Pruefung, text: str) -> tuple[str | None, BefundError | None]:
    """(Ergebnis, Befund) — genau eines von beiden ist `None`."""
    try:
        return pruefung(text), None
    except BefundError as b:
        return None, b


def _melden(befunde: list[BefundError], *, nachziehbar: bool) -> None:
    print("CLAUDE.md weicht vom Repo ab:", file=sys.stderr)
    for b in befunde:
        print(f"\n  {b.titel}", file=sys.stderr)
        for zeile in b.zeilen:
            print(f"    {zeile}", file=sys.stderr)
        print(f"    -> {b.rat}", file=sys.stderr)
    if nachziehbar:
        print(
            f"\n  Ableitbar und ohne Handarbeit nachziehbar mit:"
            f"\n    python scripts/check_claude_md.py {FIX_FLAG}",
            file=sys.stderr,
        )


def _argumente(argv: list[str]) -> bool:
    zerleger = argparse.ArgumentParser(
        prog="check_claude_md.py",
        description="CLAUDE.md gegen die Dateien prüfen, über die sie redet.",
    )
    zerleger.add_argument(
        FIX_FLAG,
        action="store_true",
        help=(
            "ableitbare Angaben nachziehen statt sie nur zu melden: "
            "Gate-Block, ruff-Pin, Live-Zahlen"
        ),
    )
    return zerleger.parse_args(argv).fix


def main(argv: list[str] | None = None) -> None:
    fix = _argumente(sys.argv[1:] if argv is None else argv)

    text = CLAUDE_MD.read_text(encoding="utf-8")
    vorher = text
    geprueft: list[str] = []
    offen: list[tuple[BefundError, bool]] = []
    nachgezogen: list[str] = []

    # Alle Prüfungen laufen, auch wenn eine fällt: zwei Abweichungen in zwei
    # CI-Läufen zu erfahren, kostet zwei Runden statt einer.
    for pruefung, reparatur in PRUEFUNGEN:
        ergebnis, befund = _pruefe(pruefung, text)
        if befund is None:
            geprueft.append(str(ergebnis))
            continue
        entwurf = reparatur(text) if fix and reparatur is not None else None
        if entwurf is None:
            offen.append((befund, reparatur is not None))
            continue
        # Gegenprobe vor dem Schreiben: eine Reparatur, die ihren eigenen
        # Befund nicht ausräumt, darf nicht als Erfolg durchgehen.
        ergebnis, geblieben = _pruefe(pruefung, entwurf)
        if geblieben is not None:
            raise ReparaturError(befund, geblieben)
        text = entwurf
        geprueft.append(str(ergebnis))
        nachgezogen.append(befund.titel)

    # Nur schreiben, wenn sich wirklich etwas geändert hat. Ein Lauf ohne
    # `--fix` kommt hier nie mit verändertem Text an.
    if text != vorher:
        CLAUDE_MD.write_text(text, encoding="utf-8")
    for titel in nachgezogen:
        print(f"CLAUDE.md nachgezogen: {titel}")

    if offen:
        # Ein Teil kann nachgezogen sein und der Rest trotzdem stehen —
        # dann ist der Lauf rot, hat aber schon Arbeit abgenommen.
        _melden(
            [b for b, _ in offen],
            nachziehbar=not fix and any(r for _, r in offen),
        )
        sys.exit(1)

    print(f"CLAUDE.md OK (geprüft: {'; '.join(geprueft)})")


if __name__ == "__main__":
    main()
