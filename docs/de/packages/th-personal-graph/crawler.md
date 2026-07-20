# TH Personal Crawler

Der TH Personal Crawler ist ein spezialisiertes CLI-Skript, das das offizielle Personalverzeichnis der TH Köln durchsucht und strukturierte Profildaten der Mitarbeiter extrahiert.

## Zweck
Das Skript `crawl_th_koeln_persons.py` (aufgerufen als ausführbares Modul `python -m th_personal_graph.scripts.crawl_th_koeln_persons`) dient dem automatisierten Aufbau und der Aktualisierung der lokalen Personen-Datenbank. Die extrahierten Profildaten werden sowohl als strukturierte Markdown-Dateien im Verzeichnis `data/th_koeln/` abgelegt als auch direkt in den SQLite-basierten Wissensgraphen (`th_personal.db`) importiert.

---

## Welche Informationen werden extrahiert?

Der Crawler durchläuft die Personenübersicht und besucht die individuellen Profilseiten der gefundenen Personen. Dabei werden folgende Detailinformationen extrahiert:

* **Stammdaten:**
    * Voller Name
    * Akademischer Grad (z. B. Dr., Prof. Dr.)
    * E-Mail-Adresse
    * URL der persönlichen Profilseite bei der TH Köln
* **Organisatorische Zuordnung:**
    * Fakultät (z. B. "Fakultät für Informatik und Ingenieurwissenschaften")
    * Institut (z. B. "Institut für Informatik") oder andere Einrichtungen (z. B. "Campus IT")
* **Rollen & Funktionen (falls vorhanden):**
    * Prüfungsausschussvorsitz (`is_pa_vorsitz`)
    * DekanIn (`is_dekan`)
    * Senatsmitglied (`is_senat`)
    * InstitutsdirektorIn (`is_institutsdirektor`)
    * Präsidiumsmitglied (`is_praesidium`)
    * Studiengangsleitung (Name des zugeordneten Studiengangs, falls im Profiltext hinterlegt)

---

## Datenquelle: Von welchen Webseiten wird extrahiert?

Die Extraktion erfolgt direkt aus dem offiziellen Webauftritt der TH Köln:
1. **Übersichtsseite (A-Z Suche):**
   `https://www.th-koeln.de/hochschule/personen_3850.php`
   Hier werden die initialen Kontaktdaten (Name, E-Mail-Adresse) sowie die Links zu den Detailprofilen über Filterparameter (Anfangsbuchstaben, Fakultäten oder Einrichtungen) ermittelt.
2. **Individuelle Profilseiten:**
   Die Detailseiten der Personen (z. B. `https://www.th-koeln.de/personen/[name]/`), um akademische Grade, Fakultäts-/Institutszugehörigkeiten sowie Funktionen und Verantwortlichkeiten auszulesen.

---

## Aufruf- und Parametermöglichkeiten

Das Skript bietet flexible Parameter zur Einschränkung des Crawling-Prozesses oder zur Wiederherstellung der Datenbank:

### 1. Gesamten Wissensgraphen aufbauen (A-Z Crawl)
Durchsucht das gesamte Personalverzeichnis von A bis Z.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons
```

### 2. Nach einer bestimmten Fakultät filtern
Extrahiert nur Personen einer bestimmten Fakultät.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
```

### 3. Nach einer bestimmten Einrichtung filtern
Crawl eingeschränkt auf eine bestimmte zentrale Betriebseinheit oder Verwaltungseinrichtung.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --institution "Campus IT"
```

### 4. Filteroptionen auflisten
Gibt alle auf der Webseite verfügbaren Namen von Fakultäten und Einrichtungen aus. Dies ist nützlich, um die korrekten Strings für die Filterung zu ermitteln.
```bash
# Fakultäten auflisten
python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties

# Einrichtungen auflisten
python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-institutions
```

### 5. Datenbank aus Markdown-Dateien rekonstruieren
Falls die Markdown-Berichte in `data/th_koeln/` bereits existieren, kann die SQLite-Datenbank `th_personal.db` komplett neu aufgebaut werden, ohne die TH-Webseite erneut anfragen zu müssen (sehr schnell und ressourcenschonend).
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --rebuild
```

---

## Beispielhafter Ablauf (Anwendungsbeispiel)

Wenn Sie den Crawler für eine spezifische Fakultät starten möchten:

1. **Verfügbare Fakultäten abfragen:**
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties
   ```
   *Ausgabe (Auszug):*
   ```
   Available Faculties:
     - Fakultät für Angewandte Naturwissenschaften
     - Fakultät für Informatik und Ingenieurwissenschaften
     ...
   ```

2. **Crawl für die gewünschte Fakultät starten:**
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
   ```
   *Konsolen-Ausgabe:*
   ```
   Filter specified, crawling A-Z for this filter.
   Crawling character: A (Faculty: Fakultät für Informatik und Ingenieurwissenschaften)
     Fetching details for: ...
   ```

3. **Ergebnis überprüfen:**
   - Im Verzeichnis `data/th_koeln/` wird eine Datei namens `persons_Fakult_t_f_r_Informatik_und_Ingenieurwissenschaften.md` mit einer Tabelle aller Personen und deren extrahierten Rollen angelegt.
   - Der SQLite-Wissensgraph in `th_personal.db` wird automatisch um die neuen Personen, deren Fakultäts- und Institutszugehörigkeiten sowie Funktionen erweitert.
