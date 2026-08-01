> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 📡 hn-tech-signal-mcp

![Version](https://img.shields.io/badge/version-0.3.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Kein API-Key erforderlich](https://img.shields.io/badge/auth-kein%20API--Key-brightgreen)](https://github.com/malkreide/hn-tech-signal-mcp)
![CI](https://github.com/malkreide/hn-tech-signal-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für globale Tech- und KI-Signalanalyse — aggregiert HackerNews, arXiv, Lobste.rs und GitHub zu einem strukturierten Briefing. Kein API-Key erforderlich.

[🇬🇧 English Version](README.md)

### Demo

![Demo: Claude nutzt tech_signal_digest über arXiv, HackerNews und GitHub](docs/assets/demo.svg)

---

## Übersicht

**hn-tech-signal-mcp** verwandelt jeden KI-Assistenten in einen proaktiven Tech-Intelligence-Analysten. Der Server aggregiert vier Signalschichten — Forschungsfront, Entwickler-Diskurs, kuratiertes Signal und Open-Source-Praxis — zu einem einzigen, strukturierten Briefing.

**Kein API-Key erforderlich.** Alle vier Datenquellen sind öffentliche APIs. Optional: `GITHUB_TOKEN` setzen für höhere GitHub-Rate-Limits (5'000 statt 60 Anfragen/Stunde).

**Anchor-Demo-Query:**
*«Gib mir ein Tech-Signal-Digest zu KI heute — was passiert in Forschung, Entwickler-Diskurs und Open Source?»*

---

## Signalarchitektur

```
FRONTIER    arXiv API      → Neueste KI/ML-Paper (cs.AI, cs.LG, cs.CL, cs.CV)
DISCOURSE   HackerNews     → Sechs Feeds + Algolia-Volltextsuche + Kommentar-Threads
            Lobste.rs      → Kuratiertes, rauscharmes Tech-Signal
PRACTICE    GitHub-Suche   → Was Entwicklerinnen und Entwickler gerade bauen
            HN «Show HN»   → Was Einzelne diese Woche veröffentlichen
```

Die vier Schichten funktionieren wie ein Radar: arXiv zeigt, was am Horizont erscheint; HN und Lobste.rs zeigen, was die Community diskutiert; GitHub zeigt, was tatsächlich gebaut wird.

Innerhalb der Diskursschicht gibt es zwei Tiefenstufen: Feeds und Suche zeigen, *worüber* geredet wird — `hn_discussion` zeigt, *was tatsächlich argumentiert wird*: die Gegenargumente und die «wir haben das produktiv versucht»-Antworten, in denen das eigentliche Signal steckt.

---

## Tools

| # | Tool | Quelle | Beschreibung |
|---|---|---|---|
| 1 | `hn_top_stories` | HackerNews | Sechs Feeds: top/best/new/ask/show/job, mit Score-Filter |
| 2 | `hn_search` | HN Algolia | Volltextsuche in der gesamten HN-Historie |
| 3 | `hn_discussion` | HackerNews | Verschachtelter Kommentar-Thread zu einer Story |
| 4 | `arxiv_latest` | arXiv | Neueste Paper nach Kategorie (cs.AI etc.) |
| 5 | `arxiv_search` | arXiv | Suche nach Stichwort/Titel/Autorin |
| 6 | `lobsters_hot` | Lobste.rs | Kuratierte Tech-Stories, nach Tag filterbar |
| 7 | `github_trending_ai` | GitHub | Trending KI-Repos nach Topic und Sterne |
| 8 | `tech_signal_digest` | Alle Quellen | Aggregiertes Markdown-Briefing |

### HackerNews-Feeds

| Feed | Inhalt | Umfang upstream |
|---|---|---|
| `top` | Frontpage im aktuellen Ranking | 500 Einträge |
| `best` | Am höchsten bewertete neuere Stories | 200 Einträge |
| `new` | Neueste Einreichungen, ungefiltert | 500 Einträge |
| `ask` | Ask HN — woran die Praxis hängenbleibt | ~30 Einträge |
| `show` | Show HN — was Leute veröffentlichen | 200 Einträge |
| `job` | Stelleninserate aus dem YC-Portfolio (`type: "job"`, keine Kommentare, Score immer 1) | ~30 Einträge |

`ask` und `job` sind upstream kurze Feeds — ein hohes `limit` liefert entsprechend weniger Stories als angefragt.

---

## Architektur-Entscheid

Dieser Server nutzt **Architektur A (nur Live-API, zwei Pfade pro Quelle)**. Ein Bulk-Dump existiert nicht.

Begründung (live geprüft am 28.07.2026 gegen die [offizielle HackerNews-API](https://github.com/HackerNews/API)):

- Alle sechs Feed-Endpoints (`{top,best,new,ask,show,job}stories.json`) antworten mit HTTP 200 und 29–500 IDs. Keine Auth, keine Rate-Limit-Header, `Cache-Control: no-cache`.
- HackerNews bietet keinen Bulk-Export — Caching liegt vollständig bei diesem Server. Die TTLs stehen in `CACHE_TTL`.
- Die Firebase-API kennt keine Suche. Historische und Volltext-Abfragen laufen über den Algolia-Index; das ist der zweite Pfad und wird von `hn_search` genutzt.
- `item/<id>.json` ist ein Request pro Item. Feeds und Kommentar-Threads fächern deshalb auf — beides ist begrenzt (`HN_MAX_CONCURRENCY`, `max_comments`).

Konsequenzen:

- Jeder Upstream-Call wiederholt bei Netzwerkfehlern, 5xx und 429 mit exponentiellem Backoff (2s / 4s / 8s). Andere 4xx scheitern sofort.
- Ein prozessweiter, gepoolter `httpx.AsyncClient`, geschlossen über den FastMCP-Lifespan.
- Unbekannte Item-IDs liefern HTTP 200 mit `null`-Body statt 404 — `hn_discussion` übersetzt das in eine explizite «kein Item gefunden»-Meldung.

---

## Installation

```bash
# Empfohlen: uvx (kein Installationsschritt nötig)
uvx hn-tech-signal-mcp

# Alternativ: pip
pip install hn-tech-signal-mcp
```

---

## Schnellstart

```bash
# Server starten (stdio-Modus für Claude Desktop)
uvx hn-tech-signal-mcp

# Mit optionalem GitHub-Token für höhere Rate-Limits
GITHUB_TOKEN=ghp_yourtoken uvx hn-tech-signal-mcp
```

Sofort in Claude Desktop ausprobieren:
> *«Gib mir ein Tech-Signal-Digest zu KI heute»*
> *«Was sind die neuesten cs.AI-Paper der letzten 48 Stunden?»*
> *«Was diskutiert HackerNews diese Woche über MCP?»*
> *«Zeig mir Trending-GitHub-Repos zum Thema ai-agents»*

---

## Konfiguration

### Umgebungsvariablen

| Variable | Standard | Beschreibung |
|---|---|---|
| `GITHUB_TOKEN` | – | Optional. GitHub Personal Access Token. Ohne Token: 60 Anfragen/h. Mit Token: 5'000/h. |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` oder `streamable_http` |
| `MCP_PORT` | `8000` | Port für HTTP-Transport |

### Claude Desktop Konfiguration

```json
{
  "mcpServers": {
    "hn-tech-signal": {
      "command": "uvx",
      "args": ["hn-tech-signal-mcp"],
      "env": {
        "GITHUB_TOKEN": "ghp_yourtoken_optional"
      }
    }
  }
}
```

**Konfigurationsdatei-Speicherorte:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Anwendungsbeispiele

### KI-Fachgruppe / Stadtverwaltung

```
«Gib mir ein Tech-Signal-Digest zu KI heute»
→ tech_signal_digest(focus="AI")

«Was sind die Top-5-arXiv-Paper zu LLM-Agenten diese Woche?»
→ arxiv_search(query="LLM agents", category_filter="cs.AI", limit=5)

«Was diskutiert HackerNews über das Model Context Protocol?»
→ hn_search(query="model context protocol", days_back=30)
```

### Forschungsmonitoring

```
«Zeig mir die neuesten NLP-Paper von arXiv»
→ arxiv_latest(category="cs.CL", limit=10)

«Suche arXiv-Paper zu Retrieval-Augmented Generation»
→ arxiv_search(query="retrieval augmented generation RAG", limit=10)

[→ Weitere Anwendungsbeispiele nach Zielgruppe →](EXAMPLES.md)
```

---

## Bekannte Einschränkungen

- **GitHub Rate-Limit**: 60 Anfragen/h ohne Token. `GITHUB_TOKEN` für den Produktiveinsatz setzen.
- **arXiv**: Neue Paper erscheinen mit bis zu 24 Stunden Verzögerung. An Wochenenden und Feiertagen verzögerte Batches.
- **HackerNews**: Top/Best-Listen aktualisieren sich alle paar Minuten. Sehr neue Stories haben noch geringe Scores.
- **HackerNews-Feeds `ask` / `job`**: Upstream existieren nur ~30 Einträge — ein hohes `limit` liefert entsprechend weniger. Job-Posts haben `type: "job"`, keine Kommentarzahl und Score 1.
- **`hn_discussion` liefert immer eine Stichprobe, nie den ganzen Thread**: Ein Request pro Kommentar bedeutet, dass grosse Diskussionen (900+ Kommentare) nicht vollständig geholt werden können. Das Budget wird über die Verschachtelungsebenen aufgeteilt und innerhalb einer Ebene reihum auf die Geschwister-Threads verteilt — es entsteht ein repräsentativer Querschnitt statt eines einzigen erschöpfend gelesenen Unter-Threads. Das Feld `truncated` zeigt an, ob gekürzt wurde.
- **`hn_discussion` gibt Klartext zurück, kein HTML**: Die HN-Auszeichnung wird für die Lesbarkeit entfernt. Die Ausgabe nicht wieder als HTML rendern — die Umwandlung ist kein Sanitizer.
- **Lobste.rs**: Kleinere Community als HN; tech-fokussiert, aber nicht alle KI-Themen abgedeckt.

---

## Sicherheit & Limiten

- **Read-only:** Alle Tools führen ausschliesslich HTTP-GET-Anfragen aus — keine Posts, Kommentare, Votes oder Schreibzugriffe nach oben.
- **Keine Personendaten:** Der Server fragt öffentliche Tech-Aggregatoren ab. Es werden keine Personendaten erhoben; Autor:innennamen aus öffentlichen Posts/Papers werden 1:1 von der Quelle zurückgegeben und nicht angereichert oder verknüpft.
- **Rate-Limits:** arXiv's Richtlinie von ≤3 Anfragen/Sekunde wird standardmässig respektiert; GitHub-Suche ist ohne `GITHUB_TOKEN` auf 60 Anfragen/Stunde limitiert. Pro Anfrage gilt ein Timeout.
- **Kein Bulk-Harvesting:** Der Server ist für interaktive, dialogische Nutzung gebaut — nicht für Scraping oder Mirroring. Nicht zum Umgehen von Pagination oder ToS einsetzen.
- **Nutzungsbedingungen:** Die Daten unterliegen den ToS der jeweiligen Quellen — [HackerNews](https://news.ycombinator.com/), [arXiv API](https://info.arxiv.org/help/api/tou.html), [Lobste.rs](https://lobste.rs/about), [GitHub](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service).
- **Keine Garantien:** Community-Projekt, nicht affiliiert mit HackerNews / Y Combinator, arXiv / Cornell, Lobste.rs oder GitHub. Verfügbarkeit hängt von den vorgelagerten APIs ab.

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Mitwirken

Siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md) ([English](CONTRIBUTING.md)).

---

## Sicherheit

Siehe [SECURITY.de.md](SECURITY.de.md) ([English](SECURITY.md)) für die
Sicherheitslage und die Meldung von Schwachstellen.

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

---

## Autorin / Autor

Hayal Oezkan · [malkreide](https://github.com/malkreide)
