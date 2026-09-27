# Herkunft der Fixtures

Aufgezeichnet am **2026-09-27** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

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
- **Groesse:** 92107 Bytes
- **SHA-256:** `e0bf347cbb8a74e187d24208f21d55276c405fad37b23d84559d64cdad1d65c1`

## `arxiv_search_1.xml`

- **Werkzeuge:** `arxiv_search`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=all%3Aretrieval+augmented+generation&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 6728 Bytes
- **SHA-256:** `469cd2d5d9afcabed875f0c5411bcdd66ec0d4c12978ae14531f3c78550d0460`

## `digest_1.xml`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.AI+OR+cat%3Acs.LG+OR+cat%3Acs.CL&start=0&max_results=6&sortBy=submittedDate&sortOrder=descending`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 15478 Bytes
- **SHA-256:** `41e04df8c510378cea3fc6db1ab26814b1c4c02babe531304f32536e12b31e5d`

## `digest_10.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49857656.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1074 Bytes
- **SHA-256:** `3d0f6b8c2ed09bd1d10c4451a1791dcf6a5c47711390af05adf9e17e7e2c6176`

## `digest_11.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49851883.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 332 Bytes
- **SHA-256:** `3a25c237d5e56044d7d299fba43cb81edacebc8d0d34fff4ac1f54c6138e2949`

## `digest_12.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49858676.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 396 Bytes
- **SHA-256:** `fdaf82f6276118ff668341dea8ef8451046526861829c7128805e006e3630894`

## `digest_13.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49829202.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 519 Bytes
- **SHA-256:** `b20d504ce5e51221e173a3225efbd62217b620b066fa0a0e36e32de0dbb1e1ff`

## `digest_14.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49858424.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 401 Bytes
- **SHA-256:** `a67dedae1b20b3a9665a4eb756104b3ed308dca82fac66f2b0b8fa69fd475b5f`

## `digest_15.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49847430.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 269 Bytes
- **SHA-256:** `fe343f2a1ff1cd90ca6052745f66a3e404a2eb9ece25c593349926c6e678ee2f`

## `digest_16.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49860074.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 450 Bytes
- **SHA-256:** `c04f986ceef9f1a89d481368736b7973ca1c700cf1c8cead565da7f78a907f63`

## `digest_17.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49845172.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1444 Bytes
- **SHA-256:** `955d8100645bbb31b9480905f5de50d80fe784e2f57697ea78bb4b0a6481ae32`

## `digest_18.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49827900.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 285 Bytes
- **SHA-256:** `da18888c76626d53dfe9dc778b6c6c73c3abc344ece14a2c70b113354ffceda0`

## `digest_19.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49851555.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 323 Bytes
- **SHA-256:** `55947f122d35e56967a4c6a18dc4c65abd476587cda26a3d028fc6de4cce69a0`

## `digest_2.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49853137.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 643 Bytes
- **SHA-256:** `978f65b66c1a15c2cef9064103632e9bfac54fe512569267c1167ad20af5f482`

## `digest_3.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49836579.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 939 Bytes
- **SHA-256:** `7fe3c2849dda274814d9b2dec8528fd02c7eacb648ca2e5183064cf0fb5e0702`

## `digest_4.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49854875.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1101 Bytes
- **SHA-256:** `5c6d0564897ada3e79d9a819becbf52ce942fd609786dc2836dc50fdf0c38100`

## `digest_5.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49862809.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 508 Bytes
- **SHA-256:** `e7b49a562794ef5e47431f4507f3db8274510a6472da0f121774c141f90bcf5c`

## `digest_6.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49850991.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 271 Bytes
- **SHA-256:** `447ec38714ab5165bea132af17a024b30bf3a798d9355de464f9387f5236e452`

## `digest_7.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49852905.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 432 Bytes
- **SHA-256:** `179ea478dcc5aaa8a3bcaea0ff422b67688218bad8e4dd2c61affc618e4df148`

## `digest_8.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49857729.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 554 Bytes
- **SHA-256:** `44994bf7ee0fc716660cf75862701d4b2aae7dffde705eb22b0443a213899d7c`

## `digest_9.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49844037.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 447 Bytes
- **SHA-256:** `9dccd920105fca8b16eab647f03053eb8591dd8a0605dd667fce6b23a562f18a`

## `hn_discussion_1.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49865554.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 425 Bytes
- **SHA-256:** `25b956f9b675fd4d89229cd3fd9a30892b68e0954bde08dfd6c6a6744d1b2713`

## `hn_discussion_2.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49865546.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 614 Bytes
- **SHA-256:** `c9b0dc37cb920616bd48f4e4dd35918fc5494a3271c69cd55ecf54546372b5b4`

## `hn_search_1.json`

- **Werkzeuge:** `hn_search`
- **Schluessel:** `https://hn.algolia.com/api/v1/search?query=rust&hitsPerPage=3&numericFilters=created_at_i%3E1787915165`
- **Auswahl:** 26 von 163 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 4156 Bytes Rohantwort
- **Groesse:** 4299 Bytes
- **SHA-256:** `a685ae09e4c9ffd049fb80df25216cbdfb1ebe7b9109c503b2bd626e43ac2708`

## `hn_top_1.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/topstories.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 6003 Bytes
- **SHA-256:** `522a5024b88bfff21de53301322d63e9b495f5924b83fec10f66c4983b36d464`

## `hn_top_10.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49858513.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1538 Bytes
- **SHA-256:** `ba7bb5dbb6f80361bafdc4925e64ff544d0646d58a419a3c90bb0289b8fc6c96`

## `hn_top_11.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49844657.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 803 Bytes
- **SHA-256:** `cecaf80af2be0cfc294ae5e3181de1a227f2646286678391f2110a4342034ac5`

## `hn_top_12.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49842764.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 763 Bytes
- **SHA-256:** `3663541c3881ebe2049434a260eb3f3a5a8e8f84c4eb80d33132ce8b40a33a13`

## `hn_top_13.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49839438.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 471 Bytes
- **SHA-256:** `533c262a41de462e4fdb6caf602de8b957474dfcfd66f28dd95e6d673872507f`

## `hn_top_14.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49832768.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 444 Bytes
- **SHA-256:** `b02c9a53957886b482eef90fa8e38ac3860e2d2500aacff7aadca1c790c34409`

## `hn_top_15.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49865067.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 466 Bytes
- **SHA-256:** `9d11d9e780ba35d64a8612665047aa7f9b441edff22f7396545fed5b2fa3a8a0`

## `hn_top_16.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49844663.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1155 Bytes
- **SHA-256:** `7eee5aca2ab821c1d13f7c4e3f7d5e58b0ed60ca003d3b4ecdc3f6354c0eda8a`

## `hn_top_17.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49854693.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 517 Bytes
- **SHA-256:** `501ad94edda41d93d110b44526edc5aaf4f3dd9696b8be2f65c745e4aedf7a1d`

## `hn_top_18.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49839567.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 454 Bytes
- **SHA-256:** `92a2dcb752cff342d37c6fe430ad7dd13b43a575715b477b2b3bbff04d312f41`

## `hn_top_19.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49863600.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 308 Bytes
- **SHA-256:** `2f41035cb1e33fb4d97f4eb4d830413d3abc228f215b73beca5ee5f4aec0998b`

## `hn_top_2.json`

- **Werkzeuge:** `hn_discussion`, `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49865343.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 295 Bytes
- **SHA-256:** `ff976324b94309dc2b300c17417815b6fd6415cc5b1a1f49bf0b6166f1b9dc83`

## `hn_top_3.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49863864.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 619 Bytes
- **SHA-256:** `b192404b8d40219efd18a17398fecbe2719796a0c8062e9248d5282a9fb51b46`

## `hn_top_4.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49864642.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 702 Bytes
- **SHA-256:** `3852d035ebec3d7e0219b029b959894a0e48859ed2e2b2fcae80550bb4b4a311`

## `hn_top_5.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49849723.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 290 Bytes
- **SHA-256:** `18141f78beff82f52242fc66df906317edbeef2996b830fc812906e6a67059bf`

## `hn_top_6.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49856988.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 372 Bytes
- **SHA-256:** `b45cd1d348983f2b25b83e31294808290d7503e7ea0f6290e6cb17484394245b`

## `hn_top_7.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49854219.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 306 Bytes
- **SHA-256:** `7d17ca9ce24ecebe2dd11960c7cae3aaf7e7b53fd447c4b806365f32027fb3cc`

## `hn_top_8.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49859112.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 438 Bytes
- **SHA-256:** `7344deec949d822eb821791df887526bf932992c83ca214f9083a29be9e2dc2a`

## `hn_top_9.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49856193.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 469 Bytes
- **SHA-256:** `cfd839393307cf94b9b98ce5b44ebbe1085290c64cf2f2850b0b26e5d0a8850e`

## `lobsters_1.json`

- **Werkzeuge:** `lobsters_hot`, `tech_signal_digest`
- **Schluessel:** `https://lobste.rs/hottest.json`
- **Auswahl:** 7 von 29 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 14884 Bytes Rohantwort
- **Groesse:** 1730 Bytes
- **SHA-256:** `febb57fa08adc5cda82040c9e2fe5b87469587678cfc727c936dcdcfae5e07fa`
