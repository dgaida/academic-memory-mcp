# Fehlerbehebung

Hier finden Sie Lösungen für häufig auftretende Probleme.

## Ollama Verbindung fehlgeschlagen

**Symptom:** Fehlermeldung beim Indexieren oder bei der Suche bezüglich der Verbindung zum LLM.
**Lösung:**  
1. Prüfen Sie, ob Ollama läuft: `curl http://localhost:11434/api/tags`  
2. Stellen Sie sicher, dass das Modell geladen ist: `ollama pull gemma2:2b`  
3. Prüfen Sie die `base_url` in `config/models.yaml`.  

## PDF-Parsing Fehler

**Symptom:** PDFs werden übersprungen oder enthalten keinen Text.
**Lösung:**  
1. Docling benötigt beim ersten Start Internetzugriff zum Laden der Modelle.  
2. Prüfen Sie, ob die PDF schreibgeschützt oder beschädigt ist.  
3. Installieren Sie Docling neu: `pip install --upgrade "docling"`.  

## Suche liefert keine Ergebnisse

**Symptom:** Die Suche bleibt leer, obwohl Dokumente vorhanden sind.
**Lösung:**  
1. Führen Sie `mcp-uni index` erneut aus.  
2. Prüfen Sie, ob `Suchindex` im Systempfad verfügbar ist.  
3. Kontrollieren Sie `config/folders.yaml` auf korrekte Pfade.  

## SQLite Datenbank gesperrt

**Symptom:** `sqlite3.OperationalError: database is locked`
**Lösung:**
Dies tritt auf, wenn mehrere Prozesse gleichzeitig schreibend auf die DB zugreifen. Beenden Sie alle Instanzen von `mcp-uni watch` oder `serve-mcp` und versuchen Sie es erneut.

## Fehlende Metriken im Dashboard

**Symptom:** Die Seite `metrics.md` zeigt keine Daten.
**Lösung:**
Die Metriken werden während des CI-Laufs generiert. Lokal müssen Sie das Metrik-Skript manuell ausführen (siehe Entwickler-Anleitung).

## Fehlende Pfad-Konfiguration für E-Mail-Klassen

**Symptom:** Eine Warnung im Log wie:
`2026-07-14 10:30:22,637 - WARNING - Keine Pfad-Konfiguration für 'XY' gefunden. Überspringe 20250826_093612 - Mail.msg`

**Bedeutung:**
Der E-Mail-Klassifizierer hat eine E-Mail als Klasse `'XY'` (z. B. `BachelorThesis`, `MasterThesis`, `Other` etc.) eingestuft. In der Konfigurationsdatei (z. B. `config/folders.yaml` oder `config/classifier_paths.yaml`) fehlt jedoch unter `class_paths` die Zuweisung eines Zielverzeichnisses für diese Klasse `'XY'`. Daher wird die entsprechende E-Mail-Datei übersprungen und nicht einsortiert.

**Fehlerbehebung:**
1. **Zielordner konfigurieren:** Öffnen Sie die Konfigurationsdatei (standardmäßig `config/folders.yaml` oder die in Ihrem Befehl angegebene Konfigurationsdatei wie `config/classifier_paths.yaml`) und prüfen Sie den Abschnitt `class_paths`.
2. **Klasse hinzufügen:** Ergänzen Sie den fehlenden Eintrag für die Klasse `'XY'`. Zum Beispiel:
   ```yaml
   class_paths:
     # ... andere Klassen ...
     XY: "D:/Pfad/zu/XY"
   ```
3. **Einstufung prüfen:** Wenn die E-Mail fälschlicherweise als Klasse `'XY'` erkannt wurde, überprüfen Sie die Trainingsdaten des Klassifizierers oder korrigieren Sie die Klassifizierung im manuellen Schritt (z. B. über das Gradio-Webinterface).
4. **Skript erneut ausführen:** Starten Sie das E-Mail-Sortier-Skript erneut, um die übersprungenen E-Mails zu verarbeiten.
