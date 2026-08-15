# Mitwirken an hn-tech-signal-mcp

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für dein Interesse! Dieser Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Loslegen

```bash
git clone https://github.com/malkreide/hn-tech-signal-mcp
cd hn-tech-signal-mcp
pip install -e ".[dev]"
```

## Tests ausführen

```bash
# Unit-Tests (kein Netzwerkzugriff nötig)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Integrationstests (Netzwerkzugriff nötig)
PYTHONPATH=src pytest tests/ -m "live"
```

## Code-Stil

- Python 3.11+, FastMCP, Pydantic v2
- Ruff für Linting: `ruff check src/`
- Alle Tools benötigen Pydantic `BaseModel`-Eingabevalidierung
- Alle Tools brauchen vollständige Docstrings

## Neues Tool hinzufügen

1. Pydantic-Eingabemodell definieren
2. Tool mit `@mcp.tool(name=..., annotations={...})` implementieren
3. Unit-Tests (gemocktes HTTP mit `respx`) und mind. einen `@pytest.mark.live`-Test schreiben
4. `README.md`, `README.de.md` und `CHANGELOG.md` aktualisieren

## Pull Requests

- Eine Funktion pro PR
- Alle Unit-Tests müssen bestehen
- Bestehende Code-Konventionen einhalten

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** täglich um 05:17 UTC, dazu jederzeit von Hand über *Actions → Live sources → Run
workflow*. Siehe [`.github/workflows/live-sources.yml`](.github/workflows/live-sources.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `live-drift` (Titel: «Live-Quellencheck rot»). Ein zweiter roter Lauf erkennt das offene Issue **am Label**, nicht am Titel, und hängt sich an denselben Thread. Wer das Label von Hand entfernt, bekommt beim nächsten roten Lauf ein zweites Issue. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über die Signalquellen (Hacker News, Lobsters, arXiv) widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.
