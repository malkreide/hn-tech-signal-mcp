"""`ci.yml` muss von Hand startbar bleiben.

Eine Zusicherung, die nur in der Prosa von CLAUDE.md steht, ist keine. Wer
`workflow_dispatch` beim naechsten Umbau des `on:`-Blocks verliert, merkt es
sonst erst, wenn er die Gates auf `main` erneut fahren will und keinen Knopf
findet — und greift dann zum Vorwand-Commit, den der Schluessel gerade
ersparen soll.

Kein YAML-Parser: `yaml` ist keine Standardbibliothek, und eine Abhaengigkeit
fuer eine Zusicherung ueber eine Zeile einzufuehren, waere unverhaeltnismaessig
— dieselbe Begruendung, die `scripts/check_claude_md.py` fuer den Gate-Block
notiert.
"""

from __future__ import annotations

import re
from pathlib import Path

CI_YML = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

# Nur der `on:`-Block, also alles Eingerueckte bis zur naechsten Zeile am
# linken Rand (`jobs:`). Absichtlich nicht die ganze Datei: `workflow_dispatch`
# irgendwo im Text zu finden, wuerde auch ein Kommentar oder ein `if:` erfuellen
# — und genau das ist kein Knopf.
ON_BLOCK = re.compile(r"^on:[ \t]*\n((?:[ \t].*\n|[ \t]*\n)*)", re.MULTILINE)

# Ein Schluessel auf der ersten Stufe des `on:`-Blocks. Eine Kommentarzeile
# beginnt mit `#` und faellt damit durch.
DISPATCH = re.compile(r"^  workflow_dispatch:[ \t]*$", re.MULTILINE)


def _on_block() -> str:
    block = ON_BLOCK.search(CI_YML.read_text(encoding="utf-8"))
    assert block is not None, "ci.yml hat keinen `on:`-Block auf der ersten Stufe"
    return block.group(1)


def test_ci_ist_von_hand_startbar() -> None:
    """`workflow_dispatch` steht als Schluessel im `on:`-Block."""
    assert DISPATCH.search(_on_block()) is not None, (
        "In ci.yml fehlt `workflow_dispatch:` im `on:`-Block. Ohne ihn laufen "
        "die Gates nur auf `push` nach `main` und auf einen PR, und ein "
        "erneuter Lauf auf `main` braucht einen Vorwand-Commit."
    )


def test_der_on_block_endet_vor_jobs() -> None:
    """Die Abgrenzung selbst geprueft: `jobs:` gehoert nicht mehr dazu.

    Ohne diese Zusicherung koennte `ON_BLOCK` stillschweigend die ganze Datei
    fassen, und der Test oben wuerde zum Teilstring-Treffer verkommen — die
    Falle, an der `_fail_if_stumm` am 14.9.2026 einen einwandfrei arbeitenden
    Digest als stumme Quelle zaehlte.
    """
    block = _on_block()
    assert "jobs:" not in block
    assert "runs-on" not in block
