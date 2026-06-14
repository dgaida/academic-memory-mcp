# MOCOGI Datenextraktion

Dieses Skript ermöglicht den Export von Modulinformationen aus der MOCOGI-API der TH Köln in eine strukturierte Markdown-Datei.

## Zweck
Das Skript `scripts/extract_mocogi_data.py` durchläuft alle aktiven Studiengänge und deren Prüfungsordnungen (POs). Für jedes Modul werden die folgenden Informationen extrahiert:  
* Modulname  
* Modulverantwortliche(r)  
* Erstprüfer(in)  
* Zweitprüfer(in)  

Die Daten werden in Tabellenform gruppiert nach Studiengang und PO in der Datei `mocogi_modules.md` gespeichert.

## Voraussetzungen  
* Ein gültiger `MOCOGI_API_TOKEN` muss in einer `.env` oder `secrets.env` Datei im Hauptverzeichnis oder im `config/` Ordner hinterlegt sein.  

## Nutzung
Führen Sie das Skript aus dem Hauptverzeichnis des Projekts aus:

```bash
PYTHONPATH=. python3 scripts/extract_mocogi_data.py
```

## Ausgabeformat
Die generierte Datei `mocogi_modules.md` folgt diesem Schema:

```markdown
# MOCOGI Modulübersicht

## [Studiengang Name]

### PO [Version]

| Modulname | Modulverantwortlich | Erstprüfer | Zweitprüfer |
| :--- | :--- | :--- | :--- |
| Algorithmik | Max Mustermann | Max Mustermann | Erika Musterfrau |
...
```
