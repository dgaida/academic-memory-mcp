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
1. MinerU benötigt beim ersten Start Internetzugriff zum Laden der Modelle.  
2. Prüfen Sie, ob die PDF schreibgeschützt oder beschädigt ist.  
3. Installieren Sie MinerU neu: `pip install --upgrade "magic-pdf[full]"`.  

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
