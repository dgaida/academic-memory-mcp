# Empfehlungen zur E-Mail-Beantwortung mittels OKF

Diese Dokumentation beschreibt, wie ein Large Language Model (LLM) oder ein KI-Agent, das zur automatisierten oder halbautomatisierten Beantwortung von E-Mails eingesetzt wird, das Open Knowledge Format (OKF) optimal nutzen sollte. Die Empfehlungen basieren auf den Prinzipien der [Open Knowledge Format v0.2 Spezifikation](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf).

---

## Kernkonzepte der OKF-basierten E-Mail-Beantwortung

Ein OKF-Bundle ist nicht bloß eine Sammlung statischer Markdown-Dateien. Es ist eine strukturierte, herkunftsgesicherte (provenance-aware) und beziehungsreiche Wissensdatenbank. Bei der Verwendung des OKF für die E-Mail-Beantwortung sollte das LLM folgenden Leitlinien folgen:

### 1. Progressive Disclosure (Schrittweise Offenlegung)
Um die Kontextgröße des LLM zu schonen und irrelevantes Rauschen zu vermeiden, sollte das System das Prinzip der *Progressiven Disclosure* anwenden:  
- Das System navigiert die Verzeichnisstruktur schrittweise über die `index.md`-Dateien.  
- Anstatt das gesamte OKF-Wissensbundle in den Prompt zu laden, liest der Agent zunächst die `index.md` auf der obersten Ebene oder in relevanten Unterordnern (z. B. `concepts/` oder `tables/`), um eine Übersicht der verfügbaren Themen zu erhalten.  
- Erst wenn ein konkretes Konzept oder Dokument als relevant identifiziert wurde, wird dieses gezielt geladen.  

### 2. Concept-Centric RAG (Konzeptzentriertes Retrieval)
Im traditionellen RAG werden oft unstrukturierte Textabschnitte (Chunks) geladen, die den eigentlichen Kontext zerreißen. Mit OKF wird RAG *konzeptzentriert*:  
- Jedes OKF-Artefakt (Konzepte, Entitäten, Definitionen, Tabellen) stellt eine in sich geschlossene Wissenseinheit dar.  
- Das LLM sollte ermutigt werden, nach ganzen Konzepten (z. B. `/concepts/examination-supervision.md`) zu suchen und diese als atomare Einheiten in den Kontext aufzunehmen.  
- Dies stellt sicher, dass Definitionen und Regeln stets im korrekten logischen Zusammenhang präsentiert werden.  

### 3. Navigation über den Wissensgraphen (Graph-Linking)
OKF-Konzepte sind über standardisierte Markdown-Links miteinander verknüpft (z. B. `[Prüfungsordnung](/documents/examination-guidelines.md)`). Ein intelligenter E-Mail-Agent sollte diese Links aktiv nutzen:  
- Wenn eine E-Mail Fragen aufwirft, die ein bestimmtes Konzept betreffen, kann der Agent den Links folgen, um verwandte Konzepte, Definitionen oder Tabellen zu laden (z. B. von einem abstrakten Konzept zu einer konkreten Modul-Tabelle).  
- Dies ermöglicht eine mehrstufige (Multi-Hop) Argumentation, um komplexe administrative Fragen präzise zu beantworten.  

### 4. Berücksichtigung von Vertrauensstufen (Trust Tiers)
Das LLM muss bei der Beantwortung sensibler E-Mails (z. B. rechtliche Auskünfte zu Prüfungsordnungen) das Attribut `verified` im Frontmatter der OKF-Dateien prüfen:  
- **Human-Reviewed (Menschlich geprüft):** Höchste Vertrauensstufe. Konzepte mit einem `human:<id>` Verifizierer können direkt als absolute Wahrheit verwendet werden.  
- **Machine-Confirmed (Maschinell bestätigt):** Mittlere Vertrauensstufe. Wurde durch automatisierte Validierungsprozesse verifiziert. Sollte mit angemessener Sorgfalt verwendet werden.  
- **Unverified (Ungeprüft):** Niedrige Vertrauensstufe. Informationen ohne `verified`-Eintrag sollten im E-Mail-Entwurf vorsichtig formuliert oder mit einem Hinweis versehen werden, dass eine manuelle Prüfung empfohlen wird.  

### 5. Aktualitätsprüfung (Freshness & Staleness)
Ein E-Mail-Agent darf keine veralteten Informationen verbreiten. Im OKF wird die Aktualität über zwei Frontmatter-Felder gesteuert:  
- **`stale_after`:** Der Agent muss das aktuelle Datum mit dem Feld `stale_after` abgleichen. Ist das aktuelle Datum größer oder gleich `stale_after`, gilt das Konzept als veraltet. Der Agent sollte dieses Wissen nicht mehr aktiv für Antworten nutzen oder den Nutzer explizit darauf hinweisen, dass die Information veraltet sein könnte.  
- **`status`:** Hat ein Dokument den Status `deprecated` oder `draft`, sollte der Agent dies bei der Beantwortung berücksichtigen (z. B. Entwürfe nicht als finale Regelungen zitieren).  

### 6. Herkunftsnachweis & Zitate (Provenance & Footnotes)
Jede administrative Aussage in einer generierten E-Mail sollte belegbar sein. OKF v0.2 sieht dafür ein standardisiertes Zitationsschema mittels Markdown-Fußnoten vor:  
- Der Agent sollte in der generierten E-Mail die genaue Quelle des Wissens angeben (z. B. unter Verweis auf das konkrete Dokument `/documents/regulations.md`).  
- Wenn Konzepte im OKF-Format Fußnoten verwenden, die auf `sources` im Frontmatter verweisen, sollte das LLM diese präzise auflösen und in der Antwort als Beleg (z. B. „Gemäß § 12 der Prüfungsordnung ...“) anführen.  

### 7. Nutzung von Attested Computations (Beglaubigte Berechnungen)
Für mathematische oder regelbasierte Auskünfte (z. B. Berechnung von Fristen, Notenschnitten oder ECTS-Hürden) sollte das LLM niemals selbst rechnen ("halluzinieren"). Stattdessen nutzt es das OKF-Konzept `Attested Computation`:  
- Der Agent identifiziert ein Konzept vom Typ `Attested Computation` (z. B. Fristenberechnung für Krankmeldungen).  
- Anstatt die Berechnung im Text selbst durchzuführen, übergibt der Agent die notwendigen Parameter an den definierten `executor` (z. B. ein Python-Skript oder eine Datenbankabfrage).  
- Der Agent liest das Ergebnis aus dem `receipt` (Beleg) und bindet diesen mathematisch gesicherten Wert in den E-Mail-Entwurf ein. Dies eliminiert Rechenfehler des Sprachmodells vollständig.  

---

## Beispielhafter Prompt-Ablauf für das E-Mail-LLM

Wenn eine neue E-Mail eingeht (z. B. *"Kann ich meine Prüfung am 15. August wegen Krankheit verschieben und wie lange habe ich Zeit, das Attest einzureichen?"*), sollte das Beantwortungssystem das LLM wie folgt steuern:

1. **Suchphase (Retrieve):**  
   - Suche in der OKF-Vektordatenbank nach Begriffen wie "Krankmeldung", "Prüfungsrücktritt", "Attest Frist".  
   - Finde das Konzept `/concepts/exam-withdrawal-illness.md`.  
2. **Prüfungsphase (Evaluate):**  
   - Lade das Konzept und analysiere das Frontmatter:  
     ```yaml
     status: stable
     stale_after: 2026-12-31
     verified: { by: human:professor-gaida, at: 2026-03-15T09:00:00Z }
     ```
   - *Ergebnis:* Das Dokument ist stabil, nicht veraltet (`stale_after` liegt in der Zukunft) und besitzt die höchste Vertrauensstufe (`human-reviewed`).  
3. **Ausführungsphase für Berechnungen (Attest):**  
   - Falls eine Fristenberechnung erforderlich ist, finde die verknüpfte `Attested Computation` für Attest-Fristen, berechne das Abgabedatum basierend auf dem Prüfungsdatum (15. August) via Skript und verwende das exakte Ergebnis.  
4. **Generierungsphase (Draft):**  
   - Generiere den Antwort-Entwurf unter Einhaltung der Tonalität und verweise explizit auf die Quelle:  
     > "... Sie müssen das ärztliche Attest unverzüglich, spätestens jedoch innerhalb von 3 Werktagen (somit bis zum 18. August), beim Prüfungsamt einreichen. [1] ..."
     >
     > **Quellen:**
     > [1] TH Köln Prüfungsordnung (§ 15 Rücktritt wegen Krankheit), hinterlegt in `/documents/examination-guidelines.md`.

---

## Reale Implementierung im MCP University Memory System

Im **MCP University Memory System** wurde dieses theoretische Modell vollumfänglich und durchsetzbar implementiert. Sobald eine E-Mail als `PAV_PO-Wechsel` klassifiziert wird, steuert das System das LLM über folgende konkrete Funktionalitäten und Mechanismen:

### 1. Progressive Disclosure über `OKF_BUNDLE_PATH`
Anstatt das gesamte OKF-Bundle (z. B. unter `D:/PAV/okf`) in den Kontext des LLM zu laden, übergibt der Controller den Pfad des Bundles über die Variable `OKF_BUNDLE_PATH` im zusätzlichen Kontext an den Agenten.  
- Der Agent liest zuerst die Übersichtsdatei `index.md` im OKF-Verzeichnis mittels des Tools `read_file(path="<OKF_BUNDLE_PATH>/index.md")`.  
- Das LLM identifiziert die relevanten Konzepte und liest diese gezielt und schrittweise (Multi-Hop über Markdown-Links) nach, z. B. `read_file(path="<OKF_BUNDLE_PATH>/concepts/exam-withdrawal-illness.md")`.  

### 2. Pflicht-Prüfkette via `SKILL_okfv02.md`
Das System lädt automatisch den Skill `SKILL_okfv02.md` und hängt ihn an die Vorgaben des Agenten an. Der Agent durchläuft bei jedem geladenen Konzept zwingend folgende 4-stufige Prüfkette in seinen Zwischenschritten (Chain-of-Thought):  
1. **Status-Prüfung:** Ist `status: deprecated` oder `draft` im Frontmatter hinterlegt?  
2. **Aktualitäts-Prüfung:** Liegt das heutige Datum vor oder nach `stale_after`?  
3. **Vertrauensstufe:** Ist das Konzept `unverified`, `machine-confirmed` oder `human-reviewed` (Verifizierung über `verified`-Einträge)?  
4. **Herkunftsnachweis:** Die Aussagen in der Antwort-Mail werden unter präziser Nennung der in `sources` hinterlegten Originaldokumente belegt und zitiert.  

### 3. Beglaubigte Berechnungen mit `execute_okf_computation`
Für mathematische und regelbasierte Bestimmungen (z. B. Fristen zur Abgabe von Attesten) wird dem LLM das Tool `execute_okf_computation` bereitgestellt:  
- **Parameter:** Das Tool erwartet den `concept_path` (Pfad zum Konzept-File) und die Eingabewerte als `parameters`.  
- **Sicherheits-Gate:** Das Tool lädt das Konzept, prüft selbstständig die Gültigkeit (`status`, `stale_after`) und führt den Berechnungs-Code aus dem Konzept deterministisch aus.  
- **Attestierung:** Das generierte `receipt` wird durch einen deterministischen Prüfer (Attester) verifiziert. Nur bei erfolgreicher Attestierung wird das Ergebnis zurückgegeben. Das LLM darf niemals selbst rechnen.  
