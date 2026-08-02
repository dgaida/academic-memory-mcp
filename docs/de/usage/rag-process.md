# RAG-Prozess (Retrieval Augmented Generation)

Um E-Mails fachlich korrekt zu klassifizieren und kontextbezogen zu beantworten, nutzt das System einen mehrstufigen RAG-Prozess. Dieser Prozess stellt sicher, dass das LLM Zugriff auf spezifisches Wissen (wie Prüfungsordnungen oder Modulbeschreibungen) hat, das in den Vektordatenbanken der jeweiligen E-Mail-Klassen gespeichert ist.

## Ablauf des Prozesses

Der Prozess in `EmailController` läuft in drei Hauptschritten ab:

### 1. Generierung von Suchanfragen
Anstatt den gesamten E-Mail-Text direkt für die Suche zu verwenden, lässt das System das LLM zunächst **3 präzise Suchanfragen (Fragen)** generieren.

- Das LLM analysiert die eingehende E-Mail.  
- Es formuliert Fragen, die darauf abzielen, die notwendigen Informationen zur Beantwortung der Anfrage aus einer Wissensdatenbank zu extrahieren.  

### 2. Vektorsuche (Retrieval)
Die generierten Fragen werden genutzt, um in der Vektordatenbank der zugehörigen E-Mail-Klasse (z.B. `Bachelor_Thesis` oder `PAV`) nach relevanten Textabschnitten (Chunks) zu suchen.

- Für jede der 3 Fragen werden die jeweils passendsten Ergebnisse abgerufen.  
- Das System nutzt hierfür den `SearchIndex`, der auf den eingebetteten Dokumenten im Ordner `data/memory/<Klasse>` basiert.  

### 3. Kontext-Injektion (Augmentation)
Die gefundenen Informationen werden gefiltert und aufbereitet:

- Es werden die **Top 3 eindeutigen Chunks** ausgewählt (basierend auf ihrem Ähnlichkeits-Score).  
- Diese Chunks werden als "Zusätzlicher Kontext" in den Prompt für die Aktions-Klassifizierung (Phase 3) sowie die finale Antwortgenerierung (Phase 6) eingefügt.  

## Automatisierte Web-Quellen-Integration (Web Crawling & Caching)

Für bestimmte E-Mail-Klassen (z. B. `BA_DL_ML_KI`) ist eine automatisierte Web-Quelle konfiguriert (definiert in `config/web_sources.yaml`). Wenn das LLM eine E-Mail dieser Klasse beantwortet, ruft der `WebCrawlerManager` relevante Informationen von der hinterlegten Webseite (und den dort bereitgestellten PDFs) ab.

### Funktionsweise
1. **Caching & Offline-First:** Das System crawlt die Zielseite (z. B. `https://dgaida.github.io/wpf_dlml_th_public/`) und alle darauf verlinkten PDFs (unter Nutzung von `crawl4ai` und einem robusten Fallback über `requests` + `BeautifulSoup` + `pdfminer`). Die gecrawlten Inhalte werden lokal in `data/cache/web_sources/<Klasse>/cache.json` gespeichert.
2. **Offline-Nutzung:** Ist keine Internetverbindung vorhanden oder bricht das Crawling ab, wird der lokale Cache direkt geladen.
3. **Keyword & BM25 Suche:** Der `WebCrawlerManager` teilt die gecrawlten Texte und PDF-Inhalte in Abschnitte auf und sucht mittels BM25 nach Absätzen, die für die Beantwortung der E-Mail hilfreich sind. Diese werden dem LLM als zusätzlicher Kontext übergeben, wobei die Webseite und PDF-Dateien als Quelle hinterlegt werden.

## Vorteile dieses Ansatzes  
- **Präzision:** Durch die Generierung gezielter Fragen wird das Rauschen reduziert, das bei einer Suche mit dem rohen E-Mail-Text entstehen könnte.  
- **Aktualität:** Das System greift immer auf den aktuellen Stand der im `memory`-Ordner indexierten Dokumente zu.  
- **Transparenz:** In den Debug-Logs und Prompts ist genau nachvollziehbar, welche Informationen als Kontext herangezogen wurden.  

---
Siehe auch:

- [E-Mail Klassifizierung](../packages/email-classifier/index.md)  
- [Indizierung von Dokumenten](indexing-details.md)  
- [Konfiguration](../configuration.md)  
