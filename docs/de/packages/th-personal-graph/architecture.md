# Architektur und Logik

Die Architektur des `th_personal_graph`-Packages kombiniert Web-Crawling, API-Integration und ontologiebasiertes Graph-Datenmanagement.

## Datenmodell & Knoten-Typen

Der Wissensgraph unterscheidet mehrere Knotentypen, um die universitäre Hierarchie präzise abzubilden:  
- **Person:** Hochschulmitarbeiter (Farbe: Blau).  
- **Modul:** Lehrfächer und Prüfungsmodule (Farbe: Gelb).  
- **Fakultät / Einrichtung / Institut:** Organisationseinheiten der Hochschule (Farben: Orange/Orchidee/Hellgrün).  
- **Studiengang & Prüfungsordnung:** Zuordnungsknoten für PO-Strukturen.  

## Modulzuordnungen & MOCOGI API

Der `extract_mocogi_data`-Prozess nutzt folgende Pipeline:  
1. **API-Abruf:** Ruft `/studyPrograms` und `/modules` ab.  
2. **Personen-Auflösung:** Nutzt `/identities` der MOCOGI-API, um IDs in Klarnamen aufzulösen.  
3. **Titel-Stripping:** Entfernt akademische Grade ("Prof", "Dr", "M.Sc") für einen sauberen Namensabgleich.  
4. **Fuzzy Name Matching:** Gleicht bereinigte Namen gegen die `Person`-Knoten in der SQLite-Datenbank ab. Bei Übereinstimmung wird die Rolle ("ist Modulverantwortlicher", "ist Erstprüfer", "ist Zweitprüfer") als gerichtete Kante im Graphen hinterlegt.  
