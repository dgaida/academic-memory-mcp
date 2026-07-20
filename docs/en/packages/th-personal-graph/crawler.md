# TH Personal Crawler

The TH Personal Crawler is a specialized CLI script that crawls the official personnel directory of TH Köln and extracts structured profile data of employees.

## Purpose
The script `crawl_th_koeln_persons.py` (invoked as an executable module `python -m th_personal_graph.scripts.crawl_th_koeln_persons`) is used to automatically build and update the local personnel database. Extracted profile data is saved as structured Markdown files in the `data/th_koeln/` directory and is also imported directly into the SQLite-based knowledge graph (`th_personal.db`).

---

## What information is extracted?

The crawler iterates through the personnel overview and visits the individual profile pages of the persons found. The following details are extracted:

* **Basic Information:**
    * Full name
    * Academic degree (e.g., Dr., Prof. Dr.)
    * Email address
    * URL of the personal profile page on the TH Köln website
* **Organizational Assignment:**
    * Faculty (e.g., "Fakultät für Informatik und Ingenieurwissenschaften")
    * Institute (e.g., "Institut für Informatik") or other institutions (e.g., "Campus IT")
* **Roles & Functions (if available):**
    * Examination Committee Chair (`is_pa_vorsitz`)
    * Dean (`is_dekan`)
    * Senate Member (`is_senat`)
    * Institute Director (`is_institutsdirektor`)
    * Presidential Board Member (`is_praesidium`)
    * Study Program Director (Name of the assigned study program, if mentioned in the profile text)

---

## Data Source: Which websites are crawled?

The extraction is performed directly from the official TH Köln web presence:
1. **Overview Page (A-Z Search):**
   `https://www.th-koeln.de/hochschule/personen_3850.php`
   This page is used to find basic contact details (name, email) and links to individual profiles using filter parameters (initial letters, faculties, or institutions).
2. **Individual Profile Pages:**
   The individual detail pages of persons (e.g., `https://www.th-koeln.de/personen/[name]/`) to extract academic degrees, faculty/institute assignments, as well as functions and responsibilities.

---

## Execution and Parameter Options

The script offers flexible parameters to limit the crawling process or to rebuild the database:

### 1. Build Entire Knowledge Graph (A-Z Crawl)
Crawls the entire personnel directory from A to Z.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons
```

### 2. Filter by Specific Faculty
Extracts only persons belonging to a specific faculty.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
```

### 3. Filter by Specific Institution
Limits the crawl to a specific central operating or administrative unit.
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --institution "Campus IT"
```

### 4. List Filter Options
Outputs all available names of faculties and institutions from the website. This is useful to find the exact strings for filtering.
```bash
# List faculties
python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties

# List institutions
python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-institutions
```

### 5. Rebuild Database from Markdown Files
If the Markdown reports in `data/th_koeln/` already exist, the SQLite database `th_personal.db` can be completely rebuilt without making new requests to the TH Köln website (very fast and resource-friendly).
```bash
python -m th_personal_graph.scripts.crawl_th_koeln_persons --rebuild
```

---

## Step-by-Step Example (Use Case)

If you want to run the crawler for a specific faculty:

1. **Query Available Faculties:**
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --list-faculties
   ```
   *Output (excerpt):*
   ```
   Available Faculties:
     - Fakultät für Angewandte Naturwissenschaften
     - Fakultät für Informatik und Ingenieurwissenschaften
     ...
   ```

2. **Start Crawling for the Desired Faculty:**
   ```bash
   python -m th_personal_graph.scripts.crawl_th_koeln_persons --faculty "Fakultät für Informatik und Ingenieurwissenschaften"
   ```
   *Console Output:*
   ```
   Filter specified, crawling A-Z for this filter.
   Crawling character: A (Faculty: Fakultät für Informatik und Ingenieurwissenschaften)
     Fetching details for: ...
   ```

3. **Verify Results:**
   - A file named `persons_Fakult_t_f_r_Informatik_und_Ingenieurwissenschaften.md` with a table of all crawled persons and their roles is created in the `data/th_koeln/` folder.
   - The SQLite knowledge graph in `th_personal.db` is automatically updated with the new persons, their faculty/institute associations, and functions.
