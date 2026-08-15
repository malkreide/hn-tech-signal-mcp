# Herkunft der Fixtures

Aufgezeichnet am **2026-08-15** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

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
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.LG&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 8101 Bytes
- **SHA-256:** `9bf2a8243edab1b3733baddac90e04a415f3334755bb8b7ceffebea414921e2d`

## `arxiv_latest_2.xml`

- **Werkzeuge:** `arxiv_latest`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.AI&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 9355 Bytes
- **SHA-256:** `31c72479faa79c3963d3056583046536f33f2e1897e3905b89a5ba9fbf634418`

## `arxiv_search_1.xml`

- **Werkzeuge:** `arxiv_search`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=all%3Aretrieval+augmented+generation&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending`
- **Auswahl:** ungekuerzt
- **Groesse:** 7598 Bytes
- **SHA-256:** `00959a92cd6c0db6895807c4c065adc473e45b3d4d540f099767d45f1758f8af`

## `digest_1.xml`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://export.arxiv.org/api/query?search_query=cat%3Acs.AI+OR+cat%3Acs.LG+OR+cat%3Acs.CL&start=0&max_results=6&sortBy=submittedDate&sortOrder=descending`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 16901 Bytes
- **SHA-256:** `e79316c927bd9252afe7e56c384da2806e49b884e2fc651808d345f5c2f79bd0`

## `digest_10.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49300314.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1098 Bytes
- **SHA-256:** `365ac3893bd40fc4b171e6ba47d1b6e6285e52cf5a082e0a19d77d2956612d96`

## `digest_11.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49272784.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 344 Bytes
- **SHA-256:** `93add9543a06bc143837e6673620fe158d1e613ba3b5403b1a4036548d3184e5`

## `digest_12.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49306196.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 534 Bytes
- **SHA-256:** `adf88900f47479d7fbb449e8a5b56e1f508b37e1019807c462feb30ce9dcd9c7`

## `digest_13.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49306577.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 428 Bytes
- **SHA-256:** `a0a53ddd2e7432ba46de497aed3b7eac8377f2c67c7512cae88a158f7d42236f`

## `digest_14.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49294997.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1336 Bytes
- **SHA-256:** `5c3ad0191de33a596d5f19f22aa5d17da83aee3a2345e18a74a4e3b91c57c6f8`

## `digest_15.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49300800.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 899 Bytes
- **SHA-256:** `c977de4332df3af650f4c897b809ef3c4d13ca690532d44871cc6bec685995d0`

## `digest_16.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49300759.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 635 Bytes
- **SHA-256:** `e349b5972c79b255ee08a3738ba0fd75316bc33df7a2725baa14a62317a1eff2`

## `digest_17.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49300568.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 393 Bytes
- **SHA-256:** `54a82f807b4a4d592e354482d0acbfc046ebf9e28cbadb644ea058c69c1e2f05`

## `digest_18.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310248.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 327 Bytes
- **SHA-256:** `97f68848bdaf175c04ae878d690425c96c5f38fcc40e54414feb00623aa76257`

## `digest_19.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49271442.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 257 Bytes
- **SHA-256:** `50b75a058564b4ef93ca6ccd30ba689e3225a50323120046d669c63fb1dbfad6`

## `digest_2.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49303202.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1430 Bytes
- **SHA-256:** `534f9de5028200a204d5a900fb704b30eec5cf9d116934f70abb24709a978b75`

## `digest_3.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310128.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 278 Bytes
- **SHA-256:** `16067a79f6a101c2b7990e2e539ac6412a345395192d272c829467263f0329ac`

## `digest_4.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49312165.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 246 Bytes
- **SHA-256:** `c7c95759a7017ccd5212a9900e9e0568a7888c3da9f3b76df5ed181517d3f02b`

## `digest_5.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49309923.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 214 Bytes
- **SHA-256:** `b093d1729e8e3b335b9738f3628310b381f37191cb89c84bbf458ace56743861`

## `digest_6.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49242085.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 281 Bytes
- **SHA-256:** `2cc4715882ed12a7fa7e723305241e4fe19955e1393e21c04c47096c9b79d619`

## `digest_7.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49276353.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 260 Bytes
- **SHA-256:** `df0a69a3c5f4cca59f21eac1e71aa69d5a6bbf91015aeb81bf38a967ab70744f`

## `digest_8.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49299605.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 2057 Bytes
- **SHA-256:** `1952ae081e5e1610e626ff064c6446ae9c615e7f63a94c0504a6837cc3bbe0b9`

## `digest_9.json`

- **Werkzeuge:** `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49307700.json`
- **Notiz:** Ungekuerzt: der Digest holt zu jeder HN-ID eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 568 Bytes
- **SHA-256:** `df1396c89f9ed63e6922af1985c270f35c21f6b29c4a82bc40cbefb7c32f191b`

## `hn_discussion_1.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49311652.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 242 Bytes
- **SHA-256:** `a1c735f7600fd13ced17c412908b269988f50f937e46483f1e849328593402ed`

## `hn_discussion_2.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49312247.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 435 Bytes
- **SHA-256:** `02614cb387772588d98c61648bbe4606b85c2abde92a306cf31bf24d97ed0ab4`

## `hn_discussion_3.json`

- **Werkzeuge:** `hn_discussion`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49311729.json`
- **Notiz:** Ungekuerzt: der Server steigt den Kommentarbaum ueber `kids` hinab.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 212 Bytes
- **SHA-256:** `7674fc2170eb440f25055815273ba5432e955d5f833ae6dfe81861fc74dbec4e`

## `hn_search_1.json`

- **Werkzeuge:** `hn_search`
- **Schluessel:** `https://hn.algolia.com/api/v1/search?query=rust&hitsPerPage=3&numericFilters=created_at_i%3E1784223095`
- **Auswahl:** 28 von 159 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 4107 Bytes Rohantwort
- **Groesse:** 4372 Bytes
- **SHA-256:** `f916d666b83facc827a815c8f2a4097d284d93c0b637fda2537c6c2be967d46a`

## `hn_top_1.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/topstories.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 6003 Bytes
- **SHA-256:** `b1022c40ce3829ad7aa25f6869cc15bce0294e3bcdc337ecac0900b96269cfb3`

## `hn_top_10.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49237183.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 389 Bytes
- **SHA-256:** `19e0e582585aeb705228fec32947471257d99e1031f70173de47f9c805e5bea5`

## `hn_top_11.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310362.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 335 Bytes
- **SHA-256:** `90b02a0d1e780d680eb47aafff6c17ad95636332f0849c1049ab429475e8b4cc`

## `hn_top_12.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310682.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 508 Bytes
- **SHA-256:** `9968c6ad00f9258a783c1350af5170127e47394cfa4c1f303b62dd437671925b`

## `hn_top_13.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49246366.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1864 Bytes
- **SHA-256:** `f6cc715872a6333374be2fbecd6ce5ec0f902f3bfdb251f2d9d2db9d094e15bf`

## `hn_top_14.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49306333.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 361 Bytes
- **SHA-256:** `e7725e10118e23ea68fb8218add6ddfad120d2c3c5827af9eac7ff59b5d0f8f6`

## `hn_top_15.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49271382.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 532 Bytes
- **SHA-256:** `84c93d8a140665b40d6af6475dca3213cd870629f23be328630164e262d3c743`

## `hn_top_16.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310495.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 376 Bytes
- **SHA-256:** `0f6d647e2876f143240c13894455c1ce00f4f2ed57c6a7bb7e1f1f126980c6da`

## `hn_top_17.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49260582.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 351 Bytes
- **SHA-256:** `70bec9f5a187cf8fe4bac2e14427127ed84680c9c7f7c69e6ed809daeb15563e`

## `hn_top_18.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49304447.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 1037 Bytes
- **SHA-256:** `20baf3ff365a49f4050d50f2ee97f3981b66df9af086a6e6ba01ec30e3580a59`

## `hn_top_19.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49308685.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 315 Bytes
- **SHA-256:** `0bfcdf0a35b7cd1915a88a95461f874677f5a331bfef73837201cde3065ea918`

## `hn_top_2.json`

- **Werkzeuge:** `hn_discussion`, `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49311651.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 339 Bytes
- **SHA-256:** `672afdbd4942bbc9b1bdb04b64fd0052519fafd3cbffc185205a5dc27fe6705d`

## `hn_top_3.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49307592.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 644 Bytes
- **SHA-256:** `eb93e0b802f54bf707919d9baf7d583e8ae215cb442252ef54b1ad344fd698bb`

## `hn_top_4.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49298035.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 697 Bytes
- **SHA-256:** `6f37534d5c881c0f1c3b11ec2dd075373f883c0f0c05b28b647064536138f05c`

## `hn_top_5.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49309549.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 514 Bytes
- **SHA-256:** `a07edfd311ed24d7da1fb5454af989ee7f22241c293114c9990aa999bf5565ee`

## `hn_top_6.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310533.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 748 Bytes
- **SHA-256:** `e1f2e479deb1ef58280ec71b8cc21f650364b1297a01b0610e7603e5a28dbbff`

## `hn_top_7.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49309451.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 857 Bytes
- **SHA-256:** `3d342efe970eb342ef44dbff4b3da12448fceec393a1e73446e852cf436b97c2`

## `hn_top_8.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49310926.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 267 Bytes
- **SHA-256:** `c32006946d69f6361706bab0cbcdabde5c1e4647f5ef61891593e9850ee38ad4`

## `hn_top_9.json`

- **Werkzeuge:** `hn_top_stories`, `tech_signal_digest`
- **Schluessel:** `https://hacker-news.firebaseio.com/v0/item/49312008.json`
- **Notiz:** Ungekuerzt: der Server holt zu jeder ID der Liste eine weitere Antwort.
- **Auswahl:** ungekuerzt — der Server holt zu Eintraegen dieser Liste weitere Antworten, ein Schnitt liesse ihn ins Leere greifen
- **Groesse:** 293 Bytes
- **SHA-256:** `2b512eaf897e1d44db53aaf9683d0709c633c8dd890b84cc143d9649abe0f773`

## `lobsters_1.json`

- **Werkzeuge:** `lobsters_hot`, `tech_signal_digest`
- **Schluessel:** `https://lobste.rs/hottest.json`
- **Auswahl:** 7 von 29 Listeneintraegen — jede Liste im Baum auf die ersten 3 gekuerzt, aus 16613 Bytes Rohantwort
- **Groesse:** 1777 Bytes
- **SHA-256:** `91427ee4c641c3b68d0a0cab97df311dada5a6bd3d69241acb17b0d7441346b3`
