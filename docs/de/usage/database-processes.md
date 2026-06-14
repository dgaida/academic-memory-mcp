# Datenbank-Prozesse

Diese Seite beschreibt die Prozesse, die lesend oder schreibend auf die zentrale Metadaten-Datenbank (SQLite) zugreifen.

## Lesende Prozesse

Mehrere Komponenten greifen lesend auf die Datenbank zu, um Informationen bereitzustellen oder darauf basierend Entscheidungen zu treffen:

*   **CLI (mcp-uni db list-*):** Die Befehle zum Auflisten von Dateien, Ordnern, Studenten usw. lesen direkt aus den entsprechenden Tabellen.
*   **Search Index:** Bei der Suche werden Metadaten aus der SQLite-Datenbank gelesen, um die Suchergebnisse aus dem Vektorindex (Qdrant) mit Kontextinformationen (wie Dateipfaden) anzureichern.
*   **MCP Agent / FastMCP Server:** Agenten lesen über den Server Informationen aus der Datenbank, um Fragen zu beantworten oder den Status von Projekten/Thesen zu prüfen.
*   **Knowledge Graph Visualisierung:** Das Skript `visualize_knowledge_graph.py` liest alle Knoten und Kanten aus, um die interaktive HTML-Grafik zu generieren.
*   **Person Profiler:** Durchsucht Metadaten von E-Mails, um relevante Korrespondenzen für eine bestimmte Person zu finden.

## Schreibende Prozesse

Die folgenden Prozesse modifizieren den Zustand der Datenbank. Dies geschieht typischerweise während der Indexierung oder durch explizite Management-Befehle.

### 1. Crawler (`mcp-uni index`)
Der Crawler ist der primäre Schreibprozess. Er führt folgende Aktionen aus:
*   **Dateimetadaten:** Speichert Pfad, Hash, Änderungszeitpunkt und Typ jeder gefundenen Datei.
*   **Ordnerstruktur:** Erfasst die Hierarchie der gescannten Verzeichnisse.
*   **Zusammenfassungen:** Speichert die durch das LLM generierten Zusammenfassungen für Dateien und Ordner.
*   **E-Mail-Konversationen:** Gruppiert E-Mails zu Konversationen und speichert aggregierte Zusammenfassungen.

### 2. Watcher (`mcp-uni watch`)
Der Watcher überwacht das Dateisystem in Echtzeit. Bei Änderungen führt er dieselben Schreiboperationen wie der Crawler für die betroffenen Dateien aus, um die Datenbank synchron zu halten.

### 3. Knowledge Graph Engine
Während der Indexierung extrahiert die Engine Entitäten und Beziehungen aus den Zusammenfassungen der Dokumente und speichert diese als Knoten und Kanten in der Graph-Struktur der Datenbank. Hierbei werden bestehende Beziehungen ggf. nach Priorität aktualisiert.

### 4. Person Crawler (`scripts/crawl_th_koeln_persons.py`)
Dieses Skript crawlt die offizielle Personenseite der TH Köln und schreibt:
*   **Personen-Knoten:** Name und E-Mail-Adresse.
*   **Organisationseinheiten:** Fakultäten und Institute als Knoten.
*   **Beziehungen:** Verknüpft Personen mit ihren jeweiligen Fakultäten/Instituten ("ist Element von").

### 5. MOCOGI Extraktor (`scripts/extract_mocogi_data.py`)
Extrahiert Modulinformationen aus der MOCOGI-API und schreibt:
*   **Studienangebote:** Studiengänge und Prüfungsordnungen.
*   **Module:** Alle Module einer Prüfungsordnung.
*   **Verantwortlichkeiten:** Verknüpft (gematchte) Personen mit Modulen ("ist Modulverantwortlicher", "ist Erstprüfer", "ist Zweitprüfer").

### 6. Student Sync (`mcp-uni db sync-students`)
Liest eine lokale `students.yaml` Datei und schreibt die darin enthaltenen Informationen über Studierende, deren Status und Abschlussarbeitsthemen in die Datenbank.

### 7. Ontology Learner
Analysiert E-Mail-Header und bestehende Graph-Knoten, um Alias-Namen (z.B. Abkürzungen von Modulen oder Namen-E-Mail-Paare) zu identifizieren und in der Alias-Tabelle zu speichern.

## Löschen von Daten

### Automatisches Löschen
Der **Crawler** erkennt während eines Scans, wenn Dateien, die in der Datenbank registriert sind, nicht mehr auf dem Dateisystem existieren. In diesem Fall werden die entsprechenden Einträge in der `files`-Tabelle automatisch gelöscht.

### Manuelles Löschen
Über die CLI-Befehlsgruppe `mcp-uni db delete-*` können gezielt Einträge entfernt werden:
*   **Dateien/Ordner:** Löscht Metadaten und (im Falle von Ordnern rekursiv) alle enthaltenen Dateireferenzen.
*   **Studenten/Deadlines:** Entfernt spezifische Datensätze aus den Verwaltungstabellen.
*   **Kanten:** Ermöglicht das Entfernen von Beziehungen im Wissensgraphen.

Beim Löschen eines Knotens oder einer Datei bleiben die verknüpften Zusammenfassungen unter Umständen als verwaiste Einträge bestehen, bis eine Bereinigung durchgeführt wird (Cleanup-Prozess).
