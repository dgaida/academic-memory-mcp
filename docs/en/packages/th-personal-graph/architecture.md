# Architecture and Logic

The architecture of the `th_personal_graph` package combines web crawling, API integration, and ontology-based graph data management.

## Data Model & Node Types

The knowledge graph distinguishes several node types to accurately represent the university hierarchy:

- **Person:** University staff (Color: Blue).  
- **Module:** Lectures and exam modules (Color: Yellow).  
- **Faculty / Institution / Institute:** Organizational units of the university (Colors: Orange/Orchid/LimeGreen).  
- **Study Program & Exam Regulation:** Association nodes for curriculum structures.  

## Module Assignments & MOCOGI API

The `extract_mocogi_data` process utilizes the following pipeline:

1. **API Call:** Fetches `/studyPrograms` and `/modules`.  
2. **Person Resolution:** Uses the MOCOGI `/identities` endpoint to resolve IDs to full names.  
3. **Title Stripping:** Removes academic titles ("Prof", "Dr", "M.Sc") to facilitate clean name matching.  
4. **Fuzzy Name Matching:** Matches cleaned names against `Person` nodes in the SQLite database. Upon matching, roles ("is module coordinator", "is first examiner", "is second examiner") are recorded as directed edges in the graph of `th_personal.db`.  
