# Herkunft der Fixtures

Aufgezeichnet am **2026-11-03** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

Eine Antwort je **Abfrage**, nicht je Endpunkt: `hn_top_stories` holt erst
eine Liste von IDs und dann jede Story einzeln, `hn_discussion` steigt den
Kommentarbaum hinab, `tech_signal_digest` faechert ueber alle Quellen zugleich
auf. Fuenf Dateien wuerden die Portfolio-Regel erfuellen und fast nichts belegen.

Der **Schluessel** unten ist, woran der Test eine Anfrage wiedererkennt: die
volle URL. Zugeordnet wird nach der Anfrage und nicht nach der Reihenfolge —
`tech_signal_digest` startet seine Abrufe mit `asyncio.gather`, und die
Reihenfolge, in der sie zurueckkommen, ist keine Zusicherung.

Die Antworten stammen aus dem geteilten Client von `server._get_client()`
(gleicher User-Agent, gleiches Timeout, gleiche Pool-Grenzen wie im Betrieb),
abgegriffen ueber einen httpx-Response-Hook. Ausgeloest hat sie jeweils das
Werkzeug selbst — so belegt die Aufzeichnung auch, dass das Werkzeug genau
diese Anfrage schickt.

## Auswahl

Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der
Listeneintraege. Kein Feld eines behaltenen Eintrags ist angetastet, und
Zaehlfelder daneben stehen wie geliefert.

Wo der Server zu jedem Eintrag einer Liste eine weitere Antwort holt — die
ID-Listen von HackerNews —, wird nicht gekuerzt: ein Schnitt waere fuer das
aufgezeichnete `limit` zufaellig richtig und fuer jedes andere falsch.

Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.
Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.

## `arxiv_latest_1.xml`

- **Werkzeuge:** `arxiv_latest`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.AI+OR+cat%3Acs.LG&start=0&max_results=36&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 93183 Bytes
- **SHA-256:** `6b84e9cd6fda8109947015a466cf9119867967923c86f733522a5ecd1ca32ce5`

## `arxiv_search_1.xml`

- **Werkzeuge:** `arxiv_search`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=all%3Aretrieval+augmented+generation&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 8268 Bytes
- **SHA-256:** `07876f34e7361e012c966242d7ec555f3d287b142171cba0f04d27c0356b15e3`

## `digest_1.xml`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.AI+OR+cat%3Acs.LG+OR+cat%3Acs.CL&start=0&max_results=6&sortBy=submittedDate&sortOrder=descending`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 18210 Bytes
- **SHA-256:** `69b944776131e0664fe75280308e5ab1a45946e85fcf7a05991dbfd8b21e1164`

## `digest_10.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50340159.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 501 Bytes
- **SHA-256:** `af290813cad089fd91ceeac89244c970247d14953e82939083b4915a73ed8610`

## `digest_11.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50344919.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 811 Bytes
- **SHA-256:** `9721d2e7476b7863096c09c755720e9ae07b22ba799835f40426f8c71aa99af6`

## `digest_12.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341462.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 733 Bytes
- **SHA-256:** `345fd619c8d64340f3192c54676e4aaffa11fc15e281c60630662bd6ef6240a7`

## `digest_13.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50339827.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 242 Bytes
- **SHA-256:** `3cb2a3f98dd63a8eb58eeff3fee8b192260d62c907d0b89b95c5547b52d21747`

## `digest_14.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50344912.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 300 Bytes
- **SHA-256:** `969c9480aee68df9ad9e9c1a54fab483da07f77f19f6e4b419d90c66af98a10e`

## `digest_15.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50337608.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 2037 Bytes
- **SHA-256:** `079e1f11cce7610f9f39b3acf17991f13bb3aed1570b6deae488a26a02306939`

## `digest_16.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://api.github.com/search/repositories?q=topic%3Allm+stars%3A%3E%3D100&sort=updated&order=desc&per_page=10`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 68614 Bytes
- **SHA-256:** `3069599b7264bd36f2cc3223f544206b82b8d41be890fc678008cc8e1345aa10`

## `digest_17.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50340992.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 486 Bytes
- **SHA-256:** `01f2ec53ba1676fa1e3938ed583871e6a6e92377bcf27fbcbcf9dbf26e219052`

## `digest_18.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://api.github.com/search/repositories?q=topic%3Amcp+stars%3A%3E%3D100&sort=updated&order=desc&per_page=10`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 67624 Bytes
- **SHA-256:** `0c1eb4814aeba3095ed505f352cdd86de15decc4e604e81532430de227a514ae`

## `digest_19.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50337661.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 337 Bytes
- **SHA-256:** `bfa1f030fc86f4c3450854d1575ebe978cf670942cf792fe3a770062bd3b5a03`

## `digest_2.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50338728.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 3971 Bytes
- **SHA-256:** `dc789534d45fa8a52c1fa5b2a2876d6281f36363b5d83a6e410a79a8079a88b3`

## `digest_20.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50337558.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 366 Bytes
- **SHA-256:** `a4ecb68fe67b9a65260e7fb2a7dd269d4d4bc223c08440c98d7fd7c82fe0906b`

## `digest_21.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50346153.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 606 Bytes
- **SHA-256:** `be20855332f18c47dbf76517f342dba2e08f043c685296195e5f818139411e2c`

## `digest_22.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50334704.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 783 Bytes
- **SHA-256:** `e142607e4de90d775b81b76696136125c086a28c0805ede7e7da9ba74e9aae7f`

## `digest_3.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50348260.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 297 Bytes
- **SHA-256:** `a609e1511a4b188d5001f41e17b79d8b3920b4cf955db9d9906bb8e49179c0a1`

## `digest_4.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50326246.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 426 Bytes
- **SHA-256:** `2d9a83d7021382d990c53599bb7e57274656e618271921e4dfae4ee25c703d96`

## `digest_5.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://api.github.com/search/repositories?q=topic%3Aai-agents+stars%3A%3E%3D100&sort=updated&order=desc&per_page=10`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 68239 Bytes
- **SHA-256:** `6f90923ddac2221a61b2baa83996d861aa4516c53a80fdd1a1d038a61e275694`

## `digest_6.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341028.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 558 Bytes
- **SHA-256:** `00da47ab54d100bceedc1fe47be277410b59ea5c8bdc53e2770e1f9e6cb6ba6c`

## `digest_7.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341736.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 722 Bytes
- **SHA-256:** `8cae4873d294b435566f4fc7513b2e30470542e38527c546a7279af2ae984295`

## `digest_8.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50344224.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 403 Bytes
- **SHA-256:** `5259cda04574cca3dfc188f246afee4a01a2acf2c9abacbd5953b0e54b8f6219`

## `digest_9.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50347552.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 707 Bytes
- **SHA-256:** `6ab7a646d6b9017b588a4fa57f9c82089e3ed4b35ec4c20cd2dafb946962910e`

## `github_1.json`

- **Werkzeuge:** `github_trending_ai`
- **Schluessel:** `https://api.github.com/search/repositories?q=topic%3Allm+stars%3A%3E%3D100&sort=stars&order=desc&per_page=3`
- **Notiz:** Steht im Plan, damit eine Umgebung ohne Pfad-Sperre ihn ohne Zutun mitnimmt.
- **Auswahl:** 12 von 43 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 16694 Bytes Rohantwort
- **Groesse:** 19387 Bytes
- **SHA-256:** `b6ad49290cc3171cebb0b21953a45cc1f25f0574263087944fd9bc03b75d46dd`

## `hn_discussion_1.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50347685.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 2420 Bytes
- **SHA-256:** `17fff18c36e3d68e4caec74befe84573eb479ef12aa90e3d0cb861daec8922ea`

## `hn_discussion_10.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342301.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 423 Bytes
- **SHA-256:** `5a5d7cfa45a9147b67d01ef85da6e3f3b214bfa80c2983bdb1b1494794385d85`

## `hn_discussion_11.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342040.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 369 Bytes
- **SHA-256:** `248cfc50efba201ac308024c0984c71218c4510645248b541355890442366e14`

## `hn_discussion_12.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50345802.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 624 Bytes
- **SHA-256:** `124e759af08f63c91d56311c53c61909b2fdb3b776f179f2c734d9ad3308d2cf`

## `hn_discussion_13.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50349311.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 976 Bytes
- **SHA-256:** `fa15b5a258f129487119e54724b8efd7d6fa1b0c243afa93279b5e6956f484c0`

## `hn_discussion_14.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342074.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 747 Bytes
- **SHA-256:** `00410fcfa0813eaf323f5af6f9bcb2ad945b781969878644218aa15610e61923`

## `hn_discussion_15.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343264.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 276 Bytes
- **SHA-256:** `0a79a791ca9379066363fed6969889287b05e93d129cb7ed6cee79a90815746b`

## `hn_discussion_16.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50349220.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 478 Bytes
- **SHA-256:** `754f9234b8d3a74a8bbb38527e3ec290481d200c404cff00d7c420bbc9254941`

## `hn_discussion_17.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343034.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 661 Bytes
- **SHA-256:** `33e9232bbfb34ec4008652ad426fb0f854ea5719a43174eaae04b810a5e40f86`

## `hn_discussion_18.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343394.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 963 Bytes
- **SHA-256:** `2bcc461848aad609aa26e0a20cd8eb95fec4fbead449c6e07311971f7d48bf55`

## `hn_discussion_19.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50348923.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 880 Bytes
- **SHA-256:** `3654884da4a6391f9b803ddc141c9b106db060378621c3191e2d202827c06c66`

## `hn_discussion_2.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341841.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1739 Bytes
- **SHA-256:** `4f3bd696cf2cdf62839a9ab075b9569eb5a82c5a68a86e6ee0e5bdedf86e038c`

## `hn_discussion_20.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342336.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 527 Bytes
- **SHA-256:** `a470187c84a041d18df8862cb09f690625190df32b3ca86c1b0f304813166614`

## `hn_discussion_21.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50345867.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 627 Bytes
- **SHA-256:** `955621831fcb7b89a468511ae39038adc24c6d0328ea573c5ed9503c23755930`

## `hn_discussion_22.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341840.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 332 Bytes
- **SHA-256:** `c909cf8586338fd3305818c9af3d1c5a85b01473428f7c03df318e733f828c29`

## `hn_discussion_23.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343731.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 908 Bytes
- **SHA-256:** `351066e55b5368da57122c0eb71f6288beb78222a76d1e0da49f07f6d81b4157`

## `hn_discussion_24.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50347251.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 508 Bytes
- **SHA-256:** `8311c085d1fc1ebc6f2209653d5360541ef447f69e37a027e49fd2ac41db49ff`

## `hn_discussion_25.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50344516.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 928 Bytes
- **SHA-256:** `1eec4725e7b5deddc446ec040ea5a6aaa4b01230d5a11e210fab0b2ac31c7972`

## `hn_discussion_3.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343628.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1316 Bytes
- **SHA-256:** `8fc17375e105fccef865400192955fc9470a7259a3404235fa1bfe03ef9f7fb8`

## `hn_discussion_4.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342071.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 621 Bytes
- **SHA-256:** `a92f346f0c8d4ba05e4af09a531b75db238d1920665493827dbd361914cf79cc`

## `hn_discussion_5.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342657.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 684 Bytes
- **SHA-256:** `f686477f029aceaf1e718d77932784936ac38d07c7e0b6b91cae56249934247a`

## `hn_discussion_6.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50342153.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1120 Bytes
- **SHA-256:** `dde993f34ec07bc3ea9e8cf3d972a9e746449f1c8d07ef41ab3714ad1827071d`

## `hn_discussion_7.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50343529.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1464 Bytes
- **SHA-256:** `93facfa49796c5f63b2e322b41e1db45f3038836446ab98eaca56859615389ef`

## `hn_discussion_8.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50344881.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1131 Bytes
- **SHA-256:** `a4ad67019c9882107a0c64417bc0c6a4aae531a845d9d08519419fca1d232a4b`

## `hn_discussion_9.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50349286.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1091 Bytes
- **SHA-256:** `66acf5aa63c58f3a730f84c36f13e46feebadb10ffb89af7faef0e7bf22e4105`

## `hn_search_1.json`

- **Werkzeuge:** `hn_search`
- **Schluessel:** `https://hn.algolia.com/api/v1/search?query=rust&hitsPerPage=3&numericFilters=created_at_i%3E1791102715`
- **Auswahl:** 27 von 125 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 3657 Bytes Rohantwort
- **Groesse:** 4195 Bytes
- **SHA-256:** `b114c683653563793b64dd2de6541c87b4aeac80ea319a8bf07214bef0a57be9`

## `hn_top_1.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/topstories.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 6003 Bytes
- **SHA-256:** `7b3f5f5f08681fd7407f47715bd9953d06d40544fdc216b1a2b9e93531b83732`

## `hn_top_10.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50345924.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 569 Bytes
- **SHA-256:** `521a3a501a2e085928f906cc217bd4d655ec1c1e632e36ee330997a8bc002d21`

## `hn_top_11.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50321605.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 276 Bytes
- **SHA-256:** `340a81a8284118cfac46c0d0c63f82db492dacf132ef52a917e7583fba7480ce`

## `hn_top_12.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50336518.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1190 Bytes
- **SHA-256:** `bdba105348a488b6126de1896843ba3760f9c778b9ffc4af1df91945a01f15f5`

## `hn_top_13.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50348740.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 304 Bytes
- **SHA-256:** `894581daa065a9a4707eaa61da6c6223b2346aedf2e93ddc0989e27cd016fda0`

## `hn_top_14.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50320904.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 361 Bytes
- **SHA-256:** `1847259b41be0a91455a7e2258a5bf46e256dfcf1ce722db5ef7d1fad445190e`

## `hn_top_15.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50340619.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 621 Bytes
- **SHA-256:** `40b9d4e1070d4e04a5145d94cf91c212d22d32b483a77b833dec76ddb362f53b`

## `hn_top_16.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50339221.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1924 Bytes
- **SHA-256:** `f663de48916a5a80e12dd9ddf727c5fe0a09dd4cece74358125c51a0861dd94f`

## `hn_top_17.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50347464.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 288 Bytes
- **SHA-256:** `a4be780eaea423b805d648769fdfa4f1c9bb3773cf41530acc661b3d03b4c0ad`

## `hn_top_18.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50349155.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 394 Bytes
- **SHA-256:** `cf3d7ef0ba22dd5bba0d8a1311c16b4b8f5d28623cf51d62bdfccc399d933534`

## `hn_top_19.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50339913.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 5575 Bytes
- **SHA-256:** `7fb50526bd80c664a04175ab6740ae5095d46a0d0e7d4e99217883503bd54b46`

## `hn_top_2.json`

- **Werkzeuge:** `hn_discussion`, `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50341174.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 4133 Bytes
- **SHA-256:** `b2dfb39f594a058eda12867885e575622ad6981e756facb903a9e1907cbb6ee3`

## `hn_top_3.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50346981.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 863 Bytes
- **SHA-256:** `5d8e4d5cc7c9bbdcdaefcb63ed87442aa3f5406ffa2f793fe2ce97bc4bc7da34`

## `hn_top_4.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50348962.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 266 Bytes
- **SHA-256:** `c919842eccb06b9e2f584f8e1ccf2f02ff51358593d4f8b5d491fbfa05597012`

## `hn_top_5.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50346849.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 493 Bytes
- **SHA-256:** `694a5ff40360974eb2106d17105768e788b3978c0ff35f37435e2f27da3ddbc4`

## `hn_top_6.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50340088.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 7427 Bytes
- **SHA-256:** `aa16d8a0b38506e1076409b9d4d6b983d325d358b165540984b84b4436a234de`

## `hn_top_7.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50334523.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 347 Bytes
- **SHA-256:** `23f9ea44a819860912e9a17f5cecec3643457dc1d988ec1e150de631e1a32639`

## `hn_top_8.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50323123.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 417 Bytes
- **SHA-256:** `cbf47cc1d18eb7a5c8d0a7ab682382dbb92ef5ce6720455d781b4dd88f2686f7`

## `hn_top_9.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/50339397.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1126 Bytes
- **SHA-256:** `f79625b179fb984b69fffa8bce31dc3ce7204b4a47526139d07bc3112ccf85a4`

## `lobsters_1.json`

- **Werkzeuge:** `lobsters_hot`, `tech_signal_digest`
- **Schluessel:** `https://lobste.rs/hottest.json`
- **Auswahl:** 10 von 32 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 14547 Bytes Rohantwort
- **Groesse:** 1694 Bytes
- **SHA-256:** `5c257e2b9eed14f2900678fb59888dea47a3d2c23fda0f57f0a5b4ba4a55fe06`
