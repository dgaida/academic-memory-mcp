# Datenbank-Prozesse

Das System verwendet zwei separate SQLite-Datenbanken, um eine saubere Trennung zwischen allgemeinen Dateimetadaten/Suchindizes und den organisationsspezifischen Personen- und Moduldaten der Hochschule zu gewährleisten:

1. **Zentrale Metadaten-Datenbank (`university.db`):** Verwaltet Dateimetadaten, Ordnerstrukturen, Zusammenfassungen, E-Mail-Konversationen, Studentendaten und Deadlines.  
2. **Personal- und Modulzuordnungen-Datenbank (`th_personal.db`):** Verwaltet die Organisationshierarchie (Fakultäten, Institute), das importierte Hochschulpersonal sowie Modulverantwortlichkeiten und Prüfungsordnungen (MOCOGI).  

Diese Seite beschreibt die Prozesse, die lesend oder schreibend auf diese beiden Datenbanken zugreifen.

---

## Lesende Prozesse

### Prozesse auf die zentrale Datenbank (`university.db`)

*   **CLI (mcp-uni db list-*):** Die Befehle zum Auflisten von Dateien, Ordnern, Studenten usw. lesen direkt aus den entsprechenden Tabellen der `university.db`.  
*   **Search Index:** Bei der Suche werden Metadaten aus der `university.db` gelesen, um die Suchergebnisse aus dem Vektorindex (Qdrant) mit Kontextinformationen (wie Dateipfaden) anzureichern.  
*   **MCP Agent / FastMCP Server:** Agenten lesen über den Server Informationen aus der `university.db`, um Fragen zu beantworten oder den Status von Projekten/Thesen zu prüfen.  
*   **Person Profiler:** Durchsucht Metadaten von E-Mails in der `university.db`, um relevante Korrespondenzen für eine bestimmte Person zu finden.  

### Prozesse auf die Personal-Datenbank (`th_personal.db`)

*   **Knowledge Graph Visualisierung (`python -m th_personal_graph.scripts.visualize_knowledge_graph`):** Das Skript liest alle Knoten (Personen, Module, POs, Fakultäten) und Kanten aus der `th_personal.db`, um die interaktive HTML-Grafik zu generieren.  

---

## Schreibende Prozesse

### Prozesse auf die zentrale Datenbank (`university.db`)

#### 1. Crawler (`mcp-uni index`)
Der Crawler ist der primäre Schreibprozess für die `university.db`. Er führt folgende Aktionen aus:  
*   **Dateimetadaten:** Speichert Pfad, Hash, Änderungszeitpunkt und Typ jeder gefundenen Datei.  
*   **Ordnerstruktur:** Erfasst die Hierarchie der gescannten Verzeichnisse.  
*   **Zusammenfassungen:** Speichert die durch das LLM generierten Zusammenfassungen für Dateien und Ordner.  
*   **E-Mail-Konversationen:** Gruppiert E-Mails zu Konversationen und speichert aggregierte Zusammenfassungen.  

#### 2. Watcher (`mcp-uni watch`)
Der Watcher überwacht das Dateisystem in Echtzeit. Bei Änderungen führt er dieselben Schreiboperationen wie der Crawler für die betroffenen Dateien auf der `university.db` aus.

#### 3. Knowledge Graph Engine
Während der Indexierung extrahiert die Engine Entitäten und Beziehungen aus den Zusammenfassungen der Dokumente und speichert diese als Knoten und Kanten in der Graph-Struktur der `university.db`.  
*   **Namensauflösung:** Knotennamen werden vor dem Speichern über die Alias-Tabelle zu ihrer kanonischen Form aufgelöst, um Duplikate zu vermeiden.  
*   **Kanten-Prioritäten:** Basierend auf `ontology.yaml` implementiert die Engine eine Prioritätslogik. Neue Beziehungen können bestehende Beziehungen derselben Kategorie zwischen zwei Knoten ersetzen, wenn sie eine höhere Priorität haben.  

#### 4. Student Sync (`mcp-uni db sync-students`)
Liest eine lokale `students.yaml` Datei und schreibt die darin enthaltenen Informationen über Studierende, deren Status und Abschlussarbeitsthemen in die `university.db`.

#### 5. Email Controller (`scripts/process_sorted_emails.py`)
Im Rahmen des täglichen E-Mail-Workflows modifiziert der Controller die Datenstruktur:  
*   **Relocation:** Verschiebt E-Mails bei Umklassifizierung physisch auf dem Dateisystem.  
*   **Just-in-Time Zusammenfassung:** Erstellt die `.emails_summary.md` erst bei der Ausführung einer Antwort-Aktion, um den aktuellsten Kontext einzubeziehen.  

#### 6. Ontology Learner (`mcp_university/knowledge_graph/ontology_learner.py`)
Automatisiert das Lernen von Aliasen für die `university.db`:  
*   Extrahiert Name-Email Paare aus E-Mail-Headern.  
*   Analysiert bestehende Wissensgraph-Knoten via LLM auf Modulnamen-Variationen (z.B. "KI" vs "Künstliche Intelligenz").  
*   Speichert die Ergebnisse in der `aliases` Tabelle der `MetadataStore`.  

---

### Prozesse auf die Personal-Datenbank (`th_personal.db`)

Diese Skripte sind Teil des spezialisierten `th_personal_graph`-Packages und operieren isoliert auf der `th_personal.db`:

#### 1. TH Personal Crawler (`python -m th_personal_graph.scripts.crawl_th_koeln_persons`)
Dieses Skript crawlt das offizielle Personenverzeichnis der TH Köln und schreibt:  
*   **Personen-Knoten:** Name, E-Mail-Adresse und akademischer Grad.  
*   **Organisationseinheiten:** Fakultäten und Institute als Knoten.  
*   **Beziehungen:** Verknüpft Personen mit ihren jeweiligen Fakultäten/Instituten ("ist Element von").  

#### 2. MOCOGI Extraktor (`python -m th_personal_graph.scripts.extract_mocogi_data`)
Extrahiert Modulinformationen aus der MOCOGI-API und schreibt:  
*   **Studienangebote:** Studiengänge und Prüfungsordnungen.  
*   **Module:** Alle Module einer Prüfungsordnung.  
*   **Verantwortlichkeiten:** Verknüpft (gematchte) Personen mit Modulen ("ist Modulverantwortlicher", "ist Erstprüfer", "ist Zweitprüfer"). Nutzt Word-Set-Comparison für robustes Namens-Matching mit den importierten Personen aus `th_personal.db`.  

---

## Löschen von Daten

### Automatisches Löschen
Der **Crawler** erkennt während eines Scans in der `university.db`, wenn registrierte Dateien nicht mehr auf dem Dateisystem existieren. In diesem Fall werden die entsprechenden Einträge in der `files`-Tabelle automatisch gelöscht.

### Manuelles Löschen
Über die CLI-Befehlsgruppe `mcp-uni db delete-*` können gezielt Einträge aus der `university.db` entfernt werden:  
*   **Dateien/Ordner:** Löscht Metadaten und (im Falle von Ordnern rekursiv) alle enthaltenen Dateireferenzen.  
*   **Studenten/Deadlines:** Entfernt spezifische Datensätze aus den Verwaltungstabellen.  
*   **Kanten:** Ermöglicht das Entfernen von Beziehungen im Wissensgraphen.  

Beim Löschen eines Knotens oder einer Datei bleiben die verknüpften Zusammenfassungen unter Umständen als verwaiste Einträge bestehen, bis eine Bereinigung durchgeführt wird (Cleanup-Prozess).
