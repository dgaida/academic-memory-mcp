# Personaldatenbank & Personen-Steckbriefe

Dieses Modul ermöglicht die Verwaltung der universitären Personaldatenbank (`th_personal.db`) sowie die automatisierte Erstellung und Aktualisierung detaillierter Personen-Steckbriefe basierend auf dem E-Mail-Verlauf und dem Wissensgraphen.

---

## 1. Die Personaldatenbank (`th_personal.db`)

Die Personaldatenbank bildet die Grundlage für das Verständnis der Organisationsstruktur und Zuständigkeiten der TH Köln im System. Sie enthält Informationen über Personen (Lehrende, Mitarbeiter), Module, Prüfungsordnungen (POs) und Fakultäten/Institute.

### Skripte zur Erstellung und Aktualisierung der Datenbank

Die Datenbank `th_personal.db` wird über zwei zentrale Skripte aus dem Package `th_personal_graph` befüllt:

1. **TH Personal Crawler (`python -m th_personal_graph.scripts.crawl_th_koeln_persons`):**
   Crawlt das offizielle Personenverzeichnis der TH Köln nach Namen, Kontaktdaten, Fakultäten, Instituten und akademischen Graden und speichert sie sowohl in der lokalen SQLite-Datenbank `th_personal.db` als auch als Markdown-Dateien in `data/th_koeln/`.

   *Beispiel-Aufruf:*
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
   ```

2. **MOCOGI Extraktor (`python -m th_personal_graph.scripts.extract_mocogi_data`):**
   Ruft über die MOCOGI-API Studiengänge, Prüfungsordnungen und Modulbeschreibungen ab. Das Skript extrahiert Modulverantwortliche sowie Erst- und Zweitprüfer und verknüpft sie über ein robustes Fuzzy-Name-Matching automatisch mit den Personen-Knoten in `th_personal.db`.

   *Beispiel-Aufruf:*
   ```bash
   python -m th_personal_graph.scripts.extract_mocogi_data
   ```

### Visualisierung der Personaldatenbank

Zur interaktiven Erkundung der importierten Beziehungen und Datenstrukturen dient das Visualisierungsskript:

*   **Wissensgraph-Visualisierung (`python -m th_personal_graph.scripts.visualize_knowledge_graph`):**
    Generiert eine interaktive 2D-Netzwerk-Visualisierung des Graphen als HTML-Datei (`knowledge_graph.html`). Sie können Knoten filtern oder den gesamten Graphen im Browser erforschen.

    *Beispiel-Aufruf (gefiltert nach Name):*
    ```bash
    python -m th_personal_graph.scripts.visualize_knowledge_graph --filter "Informatik" "Mustermann"
    ```

Detaillierte Beschreibungen zu diesen Prozessen finden Sie im Bereich **[TH Personal Graph (Package)](../packages/th-personal-graph/index.md)**.

---

## 2. Personen-Steckbriefe (Person Profiles)

Ein Personen-Steckbrief (Profil) fasst wichtige, individuelle Informationen über eine Person zusammen. Diese Profile werden dynamisch generiert und dienen dem LLM als wertvoller Kontext beim automatisierten Verfassen von E-Mails.

### Inhalt eines Steckbriefs
Ein Steckbrief im Markdown-Format fasst zusammen:
- **Rolle:** Studierende, Lehrende, etc.
- **Bevorzugte Anrede:** (Du oder Sie)
- **Erster Kontakt:** Datum und Kontext
- **Relevante Projekte, Thesen oder Aufgaben:** Zuordnung basierend auf dem E-Mail-Verlauf und dem Graphen.

### Bestimmung der Anrede (Du/Sie)
Die bevorzugte Anrede wird intelligent über den bisherigen E-Mail-Verlauf ermittelt:
- Es werden die letzten 4 direkt gesendeten E-Mails vom Nutzer an die Person und umgekehrt analysiert.
- "Sammelmails" (z.B. mit "Liebe Kolleg*innen" oder "Hallo zusammen") werden dabei ignoriert, um Verfälschungen zu vermeiden.
- Wenn keine direkten E-Mails gefunden werden, erfolgt ein Fallback auf die neuesten verfügbaren individuellen Mails.

### Erstellung und Aktualisierung

*   **Automatische Erstellung:** Wenn für eine E-Mail-Adresse noch kein Steckbrief existiert, wird dieser beim Versuch, eine E-Mail zu beantworten, automatisch im Hintergrund generiert. Dabei werden alle verfügbaren E-Mails der Person (maximal die 100 neuesten für optimale Performance) analysiert.
*   **Dynamische Aktualisierung:** Das System trackt in `profiles_tracking.db`, welche E-Mails bereits verarbeitet wurden. Bei Eintreffen neuer E-Mails wird der Steckbrief durch das LLM aktualisiert, indem neue Details nahtlos in das bestehende Profil integriert werden.

### Manuelle Verwaltung über das CLI

Sie können Steckbriefe auch manuell über das CLI verwalten:

```bash
# Alle existierenden Steckbriefe aktualisieren
mcp-uni profiles update

# Einen spezifischen Steckbrief aktualisieren
mcp-uni profiles update --email student@example.com
```

### Dateipfade
- **Steckbrief-Dateien:** Gespeichert unter dem in der Konfiguration definierten Pfad (z.B. `D:\Steckbriefe\`).
- **Tracking-Datenbank:** `data/profiles_tracking.db`.
