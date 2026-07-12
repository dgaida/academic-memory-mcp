# MOCOGI Datenextraktion

Diese Seite beschreibt die Datenextraktion aus der MOCOGI-API der TH Köln und deren Integration in die `th_personal.db`.

## Zweck
Das Skript `extract_mocogi_data.py` (aufgerufen als ausführbares Modul `python -m th_personal_graph.scripts.extract_mocogi_data`) durchläuft alle aktiven Studiengänge und deren Prüfungsordnungen (POs). Für jedes Modul werden die folgenden Informationen extrahiert:
* Modulname  
* Modulverantwortliche(r) (volle Namen)  
* Erstprüfer(in)  
* Zweitprüfer(in)  

Die Daten werden in Tabellenform gruppiert nach Studiengang und PO in der Datei `data/mocogi_modules.md` gespeichert.

## Voraussetzungen  
* Ein gültiger `MOCOGI_API_TOKEN` muss in einer `.env` oder `secrets.env` Datei im Hauptverzeichnis oder im `config/` Ordner hinterlegt sein.  

## Nutzung
Führen Sie das Skript aus dem Hauptverzeichnis des Projekts aus:

```bash
python -m th_personal_graph.scripts.extract_mocogi_data
```

## Ausgabeformat
Die generierte Datei `data/mocogi_modules.md` folgt diesem Schema:

```markdown
# MOCOGI Modulübersicht

## [Studiengang Name]

### PO [Version]

| Modulname | Modulverantwortlich | Erstprüfer | Zweitprüfer |
| :--- | :--- | :--- | :--- |
| Algorithmik | Max Mustermann | Max Mustermann | Erika Musterfrau |
...
```

---

## Integration in den Knowledge Graph
Das Skript integriert die extrahierten Daten automatisch in den SQLite-basierten Knowledge Graph der Personal-Datenbank (`th_personal.db`).

### Erstellte Knoten und Kanten
Für jeden extrahierten Datensatz werden folgende Entitäten im Graphen angelegt oder aktualisiert:

- **Knoten:**  
    - `Studiengang`: Der Name des Studiengangs (z.B. "Informatik").  
    - `Prüfungsordnung`: Die spezifische PO-Version (z.B. "Informatik (PO 2024)").  
    - `Modul`: Das einzelne Fach (z.B. "Algorithmik").  
- **Kanten (Beziehungen):**  
    - `ist Element von`: Verknüpft Module mit Prüfungsordnungen und Prüfungsordnungen mit Studiengängen.  
    - `ist Modulverantwortlicher`: Verknüpft eine Person mit einem Modul.  
    - `ist Erstprüfer` / `ist Zweitprüfer`: Verknüpft Prüfer mit Modulen.  

### Studiengangsleitung
Ein besonderer Prozess identifiziert Personen, die als **Studiengangsleitung** markiert sind (basierend auf den Daten aus dem Personen-Crawler). Falls eine Übereinstimmung zwischen der im Profil hinterlegten Studiengangsleitung und einem existierenden Studiengang-Knoten gefunden wird, wird automatisch eine Kante vom Typ `hat Studiengangsleitung` erstellt.
