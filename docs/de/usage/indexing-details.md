# Details zur Indexierung und Datenbank-Struktur

Das MCP University System verwendet drei spezialisierte SQLite-Datenbanken im Verzeichnis `data/metadata/`, um Informationen effizient zu verwalten:

### 1. Metadaten-Datenbank (`metadata.db`)
Diese Datenbank ist das Herzstück für die Verwaltung der lokalen Dateien und der studentischen Interaktionen.
- **Inhalt:**
    - Metadaten zu indexierten Dateien (Pfade, Hashes, Zeitstempel).
    - Zusammenfassungen von Ordnern und E-Mail-Konversationen.
    - **Studentischer Wissensgraph:** Speichert Verbindungen zwischen Studierenden und dem Nutzer des Tools (basierend auf `user.yaml`). Dies umfasst Rollen wie "Student", "User" und deren Interaktionen.
- **Klassen:** `MetadataStore`

### 2. Wissensgraph-Datenbank (`knowledge_graph.db`)
Hier werden institutionelle Daten der TH Köln gespeichert.
- **Inhalt:**
    - **Personal:** Daten über Lehrende, Mitarbeiter und Professoren (gecrawlt via `crawl_th_koeln_persons.py`).
    - **Module & Studiengänge:** Informationen aus dem MOCOGI-System (importiert via `extract_mocogi_data.py`).
    - **Struktur:** Abbildung von Fakultäten, Instituten und deren Beziehungen (z.B. "Professor lehrt Modul").
- **Klassen:** `KnowledgeGraphStore`

### 3. Steckbrief-Datenbank (`profiles.db`)
Verwaltet den Fortschritt der Profilerstellung.
- **Inhalt:** Trackt, welche E-Mails bereits für die Generierung von Personen-Steckbriefen (`Steckbriefe/`) verwendet wurden, um inkrementelle Updates zu ermöglichen.
- **Klassen:** `ProfileStore`

---

## Indexierungsprozess
1. **Crawling:** Das System scannt die konfigurierten Ordner.
2. **Parsing:** Dateien werden in Text umgewandelt.
3. **Speicherung:** Metadaten landen in `metadata.db`.
4. **Vektorisierung:** Texte werden in den Qdrant-Index (`data/indexes/qdrant`) geladen.
