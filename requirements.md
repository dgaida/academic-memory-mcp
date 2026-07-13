# Systemanforderungen (Requirements)

Dieses Dokument definiert die funktionalen und nicht-funktionalen Anforderungen für das **MCP University Memory System**. Es dient als Grundlage für die Entwicklung, Qualitätssicherung und Systemarchitektur.

---

## 1. Einleitung und Systemübersicht

Das **MCP University Memory System** ist ein lokal laufendes, agentenbasiertes Wissens- und Gedächtnissystem für den Einsatz im Hochschul- und Forschungsbetrieb (speziell optimiert für die TH Köln). Es ermöglicht die automatisierte Verarbeitung von E-Mails, die Verwaltung von Studierendendaten, die semantische Suche in lokalen Dokumenten sowie die automatisierte Generierung von E-Mail-Antworten und Kalendereinträgen.

Das System folgt einem strikten **Offline-First-Ansatz**, um den Schutz personenbezogener Daten von Studierenden und Lehrenden zu gewährleisten.

---

## 2. Funktionale Anforderungen (FA)

### FA-1: Crawler & Dateisystem-Scanning  
*   **FA-1.1 (Rekursiver Scan):** Das System muss Verzeichnisse rekursiv scannen und neue, geänderte oder gelöschte Dateien (PDF, DOCX, MSG, EML, etc.) automatisch erkennen.  
*   **FA-1.2 (Änderungserkennung):** Die Erkennung von Dateiänderungen muss über einen SHA-256-Hash-Vergleich mit den in der Metadatendatenbank gespeicherten Werten erfolgen.  
*   **FA-1.3 (Echtzeit-Überwachung):** Das System muss über ein Watcher-Modul (`mcp-uni watch`) verfügen, das das Dateisystem in Echtzeit überwacht und Dateiänderungen sofort indiziert.  
*   **FA-1.4 (Datenbank-Bereinigung):** Wenn eine Datei im Dateisystem gelöscht wird, müssen die entsprechenden Metadatensätze automatisch aus der zentralen Datenbank entfernt werden.  
*   **FA-1.5 (Ordner-Zusammenfassung):** Das System muss hierarchische Zusammenfassungen von Dateiebene bis zur Root-Verzeichnisebene generieren und in der Datenbank speichern.  

### FA-2: Dokumenten- & E-Mail-Parsing  
*   **FA-2.1 (PDF-Parsing):** PDFs müssen standardmäßig mit `LiteParse` eingelesen werden. `Docling` dient dabei als Backup/Fallback-Lösung.
*   **FA-2.2 (E-Mail-Parsing):** Das System muss Outlook-Mails im `.msg`-Format (via `extract-msg`) und `.eml`-Format fehlerfrei parsen.  
*   **FA-2.3 (Ressourcenschonung):** Um Performance-Engpässe zu vermeiden, dürfen standardmäßig nur die ersten **3 Seiten** eines Dokuments analysiert werden.  
*   **FA-2.4 (Unterdrückung von Warnungen):** Rauschen und nicht-kritische Warnungen von Drittanbieter-Bibliotheken (wie `extract-msg`) müssen unterdrückt werden.  
*   **FA-2.5 (Signierte Anhänge):** Beim Parsing von `.msg`-Dateien müssen signierte Anhänge (`SignedAttachment`) sicher und fehlerfrei behandelt werden.  

### FA-3: E-Mail-Klassifizierung & Sortierung  
*   **FA-3.1 (ML-Modelle):** E-Mails müssen automatisch mittels XGBoost, RandomForest oder einem PyTorch-basierten Transformer-Modell (z.B. MiniLM) klassifiziert werden.  
*   **FA-3.2 (Eingabe-Formatierung):** Das Modell-Eingabeformat muss exakt der Struktur `SUBJECT: <Betreff> | ATTACHMENTS: <Datei1, ...> [SEP] <E-Mail-Body>` entsprechen. Der E-Mail-Body muss für die Klassifizierung nicht standardmäßig anonymisiert werden; eine Anonymisierung des E-Mail-Bodys erfolgt ausschließlich dann, wenn ein Cloud-LLM verwendet wird (gemäß FA-10).
*   **FA-3.3 (Klassendefinition durch Benutzer):** Die E-Mail-Klassen werden dynamisch durch die vom Benutzer über die Ordnerstruktur der Trainingsdaten definierten Ordnernamen festgelegt. Es gibt keine fest vordefinierten Klassen im Code, sodass der Benutzer die Klassennamen flexibel anpassen kann.
*   **FA-3.4 (Pfad-Hierarchie):** Archivierte E-Mails müssen automatisch in eine dreistufige Struktur verschoben werden: `Semester (z.B. 2023_24_WS) / Nachname / (Inbox oder SentItems)`.  
*   **FA-3.5 (Spezial-Routing):** Für E-Mail-Klassen, die mit `BA_` oder `MA_` beginnen, gilt dieselbe dreistufige Struktur wie in FA-3.4 (`Semester (z.B. 2023_24_WS) / Nachname / (Inbox oder SentItems)`).
*   **FA-3.6 (Namensextraktion):** Die Ermittlung des Nachnamens eines Studierenden aus E-Mail-Metadaten muss über eine hierarchische Logik erfolgen:  
    1.  Prüfung von "im Auftrag von"-Headern.  
    2.  *Greedy Name Matching:* Abgleich von Teilen des Anzeigenamens (Display Name) mit dem Local-Part der E-Mail-Adresse. Findet sich der Name im Local-Part, ist dies der Nachname (z.B. `Mustermann Max <mustermann@example.com>` -> "Mustermann").  
    3.  *Dot-Separated Fallback:* Aufteilung des Local-Parts an Punkten (`.`) und Prüfung der Segmente von hinten nach vorne (unter Ignorierung generischer Begriffe).  
    4.  *Generische Fallbacks:* Komma-Trennung (`Nachname, Vorname`), letztes Wort des Anzeigenamens oder Großbuchstaben-Erkennung.  
*   **FA-3.7 (Namen-Normalisierung):** Extrahierte Namen müssen in *Title Case* zurückgegeben werden. Umlaute müssen für Verzeichnispfade normalisiert werden (z.B. "Müller" -> "Mueller" für das Dateisystem), der Originalname muss jedoch erhalten bleiben.  
*   **FA-3.8 (GUI Sichtbarkeit & Benennung):** Alle sortierten E-Mails müssen in der **E-Mail-Workflow-GUI** vollständig sichtbar sein (keine versteckten oder standardmäßig eingeklappten Zeilen). Die verschiedenen Gradio GUIs im System besitzen eindeutige Namen zur Unterscheidung: **E-Mail-Workflow-GUI** (für die E-Mail-Verarbeitung und Archivierung), **E-Mail-Schnellsuche-GUI** (für E-Mail-Suche und Anzeige) und **Terminkalender-GUI** (für die Kalender- und Terminverwaltung).

### FA-4: Hybrid-Suche & RAG-Prozess  
*   **FA-4.1 (Hybrid-Suche):** Das System muss eine hybride Suche anbieten, die BM25-Volltextsuche mit Qdrant-Vektorsuche kombiniert.  
*   **FA-4.2 (Lokales Laden):** Einbettungs- und Sprachmodelle müssen primär lokal geladen werden (`local_files_only=True`). Bei erfolgreichem Laden muss der Log-Eintrag `ERFOLG: Modell <Modellname> wurde LOKAL geladen.` ausgegeben werden.  
*   **FA-4.3 (RAG-Ablauf):** Der RAG-Prozess (Retrieval Augmented Generation) muss mehrstufig aufgebaut sein:
    1.  Generierung von **3 präzisen Suchanfragen (Fragen)** durch das LLM basierend auf der E-Mail.  
    2.  Abruf relevanter Chunks aus der klassenspezifischen Vektordatenbank (z.B. `data/memory/<Klasse>`).  
    3.  Auswahl der **Top 3 eindeutigen Chunks** basierend auf dem Ähnlichkeits-Score.  
    4.  Injektion dieser Chunks als "Zusätzlicher Kontext" in den Prompt für die Antwortgenerierung.  
*   **FA-4.4 (qmd-Integration):** Das System muss optional die global installierte Node.js CLI `qmd` zur Query-Expansion und zum Re-Ranking nutzen. Falls `qmd` fehlt, muss ein automatischer Fallback auf die native Python-Suche (Qdrant + BM25) erfolgen.  

### FA-5: E-Mail-Workflow-Steuerung & GUI  
*   **FA-5.1 (Gradio GUI):** Die Interaktion muss über eine Gradio-basierte Benutzeroberfläche erfolgen, aufgeteilt in zwei Tabs:  
    *   *Tab 1 (Schnell-Einsortierung):* Massenverarbeitung und Archivierung bereits korrekt klassifizierter Mails.  
    *   *Tab 2 (Detail-Ansicht):* Detailanalyse einer ausgewählten Mail mit KI-Zusammenfassung (max. 2 Sätze), Kontext-Anzeige und Aktions-Auswahl.  
*   **FA-5.2 (Aktions-Vorschläge):** Basierend auf dem E-Mail-Inhalt und dem RAG-Kontext muss das System eine von sechs Aktionen vorschlagen:  
    1.  *Antwort schreiben:* Entwurf basierend auf Thema, Personas und der bisherigen Konversation. Die Zusammenfassung des Ordners (aus der Datei `.emails_summary.md`), in dem die E-Mail archiviert wird, soll dem LLM ebenfalls übergeben werden, damit das LLM Kontext über die bisherige Konversation hat.
    2.  *Antwort mit Terminvorschlag:* Ermittelt freie Slots aus `free_slots.md` via `get_appointment_slots` und integriert sie.  
    3.  *Termin direkt buchen:* Erstellt einen Kalendereintrag bei Terminbestätigungen.  
    4.  *Nur archivieren:* Verschiebt die Mail ins Archiv.  
    5.  *Aufgabe "Anhang lesen" (Abschlussarbeiten):* Automatische Verarbeitung finaler Abgaben.  
    6.  *Kolloquium-Termin:* Spezielle Buchung für Abschlussvorträge.  
*   **FA-5.3 (Archivierungs-Vorschlag):** Das System muss automatisch die Aktion "Nur archivieren" vorschlagen für:  
    *   E-Mails, die älter als der konfigurierte Schwellenwert (z.B. 6 Monate) sind.  
    *   E-Mails, die sich im `SentItems`-Ordner befinden.  
    *   Bereits beantwortete E-Mails.  
*   **FA-5.4 (Anhänge-Handhabung in der GUI):** Die GUI muss eine Checkbox für "Anhang speichern" in Tab 1 und Tab 2 bereitstellen. Der Auswahlzustand von Tab 1 muss beim Wechsel zu Tab 2 erhalten bleiben.  
*   **FA-5.5 (Aktion "Anhang lesen" - Automatisierung):** Bei der Einstufung als finale Abgabe müssen folgende Schritte vollautomatisch ausgeführt werden:  
    1.  Speichern aller E-Mail-Anhänge direkt im studentischen Hauptordner (`Semester / Nachname /`).  
    2.  Erstellen/Aktualisieren der Konfigurationsdatei `config.json` im Hauptordner des Studenten mit dem Dateinamen der PDF-Arbeit.  
    3.  Erstellen einer Kalender-Erinnerung in Outlook für **genau 7 Tage nach E-Mail-Eingang um 08:00 Uhr**.  
    4.  Automatisches Generieren eines Outlook-Antwortentwurfs zur Bestätigung des Empfangs.  
*   **FA-5.6 (Aktion "Kolloquium-Termin" - Automatisierung):**  
    1.  Erstellen/Aktualisieren der `config.json` im Ordner des Studenten mit Vortragsparametern (Datum, Uhrzeit, Raum, Ortstyp).  
    2.  Automatisches Eintragen des Kolloquiums in den Outlook-Kalender (Dauer fest auf 60 Minuten eingestellt) und Übertrag der Daten in die `config.json`.  

### FA-6: Personen-Profile & PersonProfiler  
*   **FA-6.1 (Profil-Generierung):** Das System muss Markdown-basierte Personen-Steckbriefe in `D:\Steckbriefe\<email>.md` generieren und aktualisieren.  
*   **FA-6.2 (Profil-Inhalt):** Der Steckbrief muss Rolle, bevorzugte Anrede (Du/Sie), den ersten Kontakt sowie relevante Projekte/Thesen enthalten.  
*   **FA-6.3 (Anrede-Bestimmung - Du/Sie):** Die bevorzugte Anrede muss durch Analyse der letzten 4 gesendeten E-Mails an die Person und der letzten 4 empfangenen E-Mails von der Person ermittelt werden. Massenmails/Sammelmails (z.B. "Hallo zusammen") müssen dabei ignoriert werden.  
*   **FA-6.4 (Performance-Grenze):** Für die Profilerstellung dürfen maximal die **100 neuesten E-Mails** einer Person herangezogen werden.  
*   **FA-6.5 (Inkrementelle Updates):** Bei Updates eines bestehenden Profils dürfen nur E-Mails berücksichtigt werden, die neuer sind als das Änderungsdatum der Steckbrief-Datei.  
*   **FA-6.6 (Tracking):** Verarbeitete E-Mails müssen in der SQLite-Datenbank `profiles_tracking.db` getrackt werden.  

### FA-7: Outlook VBA-Makros  
*   **FA-7.1 (Datenexport):** VBA-Makros müssen E-Mails im standardisierten Format `YYYYMMDD_HHMMSS - Subject.msg` in den `inbox`-Ordner exportieren.  
*   **FA-7.2 (Freie Zeitfenster):** Freie Terminfenster müssen in eine Datei `free_slots.md` exportiert werden.  
*   **FA-7.3 (Outlook-Fehlervermeidung):** Zum Verschieben von Elementen in Outlook muss `target_folder.Items.Add(0)` anstelle von `mail.Move()` verwendet werden, um spezifische VBA-Laufzeitfehler zu vermeiden.  
*   **FA-7.4 (Konto-Festlegung):** Die Makros müssen auf das in `config/user.yaml` definierte Benutzerkonto des Users ausgelegt sein. Bei Laden der Konfiguration werden die VBA-Dateien automatisch auf die konfigurierte E-Mail-Adresse des Benutzers angepasst.
*   **FA-7.5 (Benutzer-Konfiguration):** Die Benutzerdaten (Name, primäre E-Mail-Adresse und alternative E-Mail-Adressen) müssen vom Benutzer über eine YAML-Konfigurationsdatei (`config/user.yaml`) flexibel definiert werden können.

### FA-8: Model Context Protocol (MCP) Server  
*   **FA-8.1 (Server-Start):** Das System muss einen MCP-Server über das CLI-Kommando `mcp-uni serve-mcp` bereitstellen.  
*   **FA-8.2 (Tools für Agenten):** Der Server must folgende Tools für externe Clients (z.B. Claude Desktop) bereitstellen:  
    *   `search_documents`: Semantische Suche in Dokumenten.  
    *   `get_folder_summary`: Abfrage aggregierter Ordner-Informationen.  
    *   `get_student_context`: Vollständige Historie und Status eines Studenten.  
    *   `generate_mail_reply`: Entwurf einer E-Mail basierend auf Kontext und Skills.  
    *   `get_open_tasks`: Extraktion offener Aufgaben.  

### FA-9: Metadaten, Wissensgraph & TH Personal Graph  
*   **FA-9.1 (Datenbank-Trennung):** Das System muss zwei getrennte SQLite-Datenbanken pflegen:  
    1.  `university.db`: Dateimetadaten, Ordnerstrukturen, Studenten-Synchronisierung (`sync-students`), E-Mail-Konversationen.  
    2.  `th_personal.db`: Organisationshierarchie, Hochschulpersonal der TH Köln und Modulverantwortlichkeiten.  
*   **FA-9.2 (Ontology Learner):** Das System muss automatisch Name-E-Mail-Paare sowie Modulnamen-Variationen (z.B. "KI" vs. "Künstliche Intelligenz") lernen und in der Tabelle `aliases` speichern.  
*   **FA-9.3 (Kanten-Prioritäten):** Beziehungen im Wissensgraphen müssen Prioritäten besitzen (definiert in `ontology.yaml`). Beziehungen mit höherer Priorität müssen bestehende Beziehungen niedrigerer Priorität überschreiben.  
*   **FA-9.4 (TH Personal Crawler):** Ein Crawler-Skript muss das Personenverzeichnis der TH Köln crawlen und Personen sowie Organisationseinheiten in `th_personal.db` anlegen.  
*   **FA-9.5 (MOCOGI Extraktion):** Studiengänge, POs, Module und Prüfer müssen über die MOCOGI-API extrahiert, mittels Fuzzy-Matching Personen zugeordnet und in `th_personal.db` gespeichert werden.  
*   **FA-9.6 (Visualisierung):** Der Wissensgraph muss als interaktive HTML-Datei (`knowledge_graph.html`) visualisiert werden können.  

### FA-10: Anonymisierung & Datenschutz (Datenschutz-First)  
*   **FA-10.1 (Lokale Anonymisierung):** Personenbezogene Daten (PII) wie Namen von Studierenden müssen vor der Übermittlung an optionale Cloud-LLMs lokal anonymisiert werden (unter Verwendung des lokalen Ollama-Modells via `Anonymizer`).  
*   **FA-10.2 (Bidirektionalität):** Vor der Ausführung von lokalen Tools (z.B. Kalendereinträge, Suchen) müssen die Daten lokal wieder de-anonymisiert werden.  

---

## 3. Nicht-funktionale Anforderungen (NFA)

### NFA-1: Sicherheit & Privatsphäre  
*   **NFA-1.1 (Lokale Ausführung):** Alle Kernkomponenten (LLM via Ollama, Vektordatenbank Qdrant, Metadaten-Datenbanken SQLite, Parsing, Indexierung) müssen vollständig offline und lokal ohne Internetverbindung lauffähig sein.  
*   **NFA-1.2 (Datenisolierung):** Studentendaten, E-Mails und Notizen dürfen den lokalen Computer des Benutzers niemals unverschlüsselt oder unanonymisiert verlassen.  

### NFA-2: Performance & Skalierbarkeit  
*   **NFA-2.1 (Parser-Begrenzung):** Um RAM- und CPU-Ressourcen zu schonen, muss das Parsing von Dokumenten (PDFs, DOCX) hart auf die ersten **3 Seiten** limitiert sein.  
*   **NFA-2.2 (LLM-Kontextfenster-Schonung):** Bei der Steckbrieferstellung und -aktualisierung dürfen maximal die **100 neuesten E-Mails** einer Person herangezogen werden, um das Kontextfenster lokaler LLMs nicht zu überschreiten.  
*   **NFA-2.3 (Antwortzeiten der GUI):** Suchergebnisse in der E-Mail-Schnellsuche-GUI müssen durch die Nutzung eines Index-Caches (`data/cache/email_search_cache.json`) in unter 1 Sekunde geliefert werden.  

### NFA-3: Zuverlässigkeit & Robustheit  
*   **NFA-3.1 (Dateisperren auf Windows):** Da das System unter Windows läuft, müssen alle im Code geöffneten Dateien (z.B. via Context Manager) zwingend geschlossen werden, bevor sie verschoben, umbenannt oder gelöscht werden, um `[WinError 32]` zu verhindern.  
*   **NFA-3.2 (Fehlertoleranz des Crawlers):** Die Ordnerzusammenfassung des Crawlers muss über eine automatische Ein-Mal-Wiederholungslogik (Retry-Logik) mit detaillierter Debug-Ausgabe (`.folder_summary_items_debug.txt`) verfügen.  
*   **NFA-3.3 (Zusammenfassungs-Verifizierung):** Das System muss nach dem Schreiben von Ordnerzusammenfassungen die tatsächliche Existenz der erzeugten Dateien auf dem Dateisystem verifizieren.  
*   **NFA-3.4 (Vergangenheits-Termine):** Bei der Buchung von Terminen müssen Termine in der Vergangenheit automatisch erkannt, nicht im Kalender eingetragen und direkt als `Archiviert (Termin in Vergangenheit)` markiert werden.  

### NFA-4: Kompatibilität & Plattformunterstützung  
*   **NFA-4.1 (Plattformen):** Das System muss uneingeschränkt auf Windows 10/11, macOS (Intel und Apple Silicon) sowie Linux lauffähig sein.  
*   **NFA-4.2 (Python-Kompatibilität):** Das System muss mit Python 3.10+ kompatibel sein. F-Strings dürfen keine verschachtelten Anführungszeichen desselben Typs enthalten, um die Kompatibilität mit Python 3.10 zu wahren.  
*   **NFA-4.3 (Umgebungs-Support):** Das Projekt muss sowohl Standard-Pip-Virtual-Environments (`venv`) als auch Anaconda-Umgebungen (`environment.yml`) nativ unterstützen.  
*   **NFA-4.4 (GPU-Unterstützung):** Das System muss optional NVIDIA GPUs via CUDA sowie Apple Silicon GPUs via MPS für die Beschleunigung von Transformer-Modellen unterstützen.  
*   **NFA-4.5 (Zeitzonen-Sperre):** Alle Kalendereinträge und Termine müssen zwingend in der Zeitzone `Europe/Berlin` angelegt werden. Die Standarddauer für Termine beträgt 30 Minuten (Kolloquien ausgenommen: 60 Minuten).  

### NFA-5: Wartbarkeit & Qualitätsstandards  
*   **NFA-5.1 (Google-Style Docstrings):** Alle Klassen, Methoden und Funktionen müssen lückenlos mit Google-Style Docstrings versehen sein. Diese müssen zwingend die Sektionen `Args:` und `Returns:` (sofern Parameter/Rückgabewerte vorhanden) enthalten.  
*   **NFA-5.2 (Docstring-Abdeckung):** Die Docstring-Abdeckung (überprüft mit dem Tool `interrogate`) muss dauerhaft bei mindestens **99%** liegen.  
*   **NFA-5.3 (Typisierung):** Die Verwendung von expliziten Python-Typ-Hints für alle Funktionsparameter sowie Rückgabewerte (einschließlich `-> None` für `__init__`) ist verpflichtend.  
*   **NFA-5.4 (Variablennamen):** Es müssen sprechende, selbsterklärende Variablennamen verwendet werden (z.B. `local_part` statt `lp`, `display_name` statt `dn`). Abkürzungen sind zu vermeiden.  
*   **NFA-5.5 (Erhaltungs-Richtlinie):** Vorhandene Kommentare, Docstrings und Logging-Statements dürfen niemals gelöscht werden, es sei denn, sie sind nachweislich fehlerhaft oder obsolet.  
*   **NFA-5.6 (Code-Formatierung & Linting):** Der Code muss ruff-konform sein. Vor jedem Commit muss `ruff check . --fix` ausgeführt werden. Fehlerklassen wie E741, E402, F401, F541 sind unzulässig.  
*   **NFA-5.7 (Detailliertes Logging):** Jeder Verarbeitungsschritt von E-Mails muss detailliert und nachvollziehbar in `process_emails.log` protokolliert werden.  
*   **NFA-5.8 (Testabdeckung):** Das System muss über eine umfassende Testsuite (pytest) mit einer Testabdeckung von mindestens 95% verfügen. Dabei gelten folgende Mocking-Regeln:  
    *   `SentenceTransformer.encode` muss so gemockt werden, dass ein Dummy-Vektor der Größe 384 zurückgegeben wird.  
    *   Outlook-Kollektionen müssen ein 1-basiertes Indexing verwenden.  
    *   `extract_msg` muss via `side_effect` für aufeinanderfolgende Aufrufe von `openMsg` gemockt werden.  

### NFA-6: Internationalisierung & Dokumentation  
*   **NFA-6.1 (Bilinguale Dokumentation):** Die Dokumentation muss zweisprachig (Deutsch und Englisch) aufgebaut sein. Hierfür wird das MkDocs-Ecosystem mit dem Plugin `mkdocs-static-i18n` und der Konfiguration `docs_structure: folder` verwendet.  
*   **NFA-6.2 (Autoritative Sprache):** Deutsch ist die führende und autoritative Sprache für alle Benutzerdokumentationen, Benutzeroberflächen und LLM-Instruktionen. Englisch dient als vollständige Übersetzung.  
*   **NFA-6.3 (Relative Pfade):** In allen Markdown-Dokumenten müssen relative Pfade (z.B. `../assets/`) für Links und Bilder verwendet werden, um die Portabilität der Dokumentationsseite zu gewährleisten.  
*   **NFA-6.4 (Clean-Up-Richtlinie):** Vor jeder Veröffentlichung oder Abgabe müssen alle temporären Entwicklungsartefakte (`__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`, `*.log`, temporäre Testdateien wie `test.docx`, Build-Ordner `dist/`, `build/` und `*.egg-info`) vollständig gelöscht werden.  
