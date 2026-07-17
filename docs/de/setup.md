# Einrichtung der Software

Diese Seite beschreibt die notwendigen Schritte zur ersten Einrichtung des MCP University Systems nach der Installation.

Für die eigentliche Installationsanleitung und die Systemvoraussetzungen verweisen wir auf die Seite **[Installation](installation.md)**.

## Erst-Einrichtung (Initialer Setup-Ablauf)

Um das System betriebsbereit zu machen, müssen Sie die Konfigurationsdateien vorbereiten und anpassen. Es gibt drei Dateien, die Sie **zwingend** konfigurieren müssen. Konfigurationsdateien, die nicht unbedingt geändert werden müssen (wie z. B. `models.yaml` oder `ontology.yaml`), können Sie im Auslieferungszustand belassen.

### 1. Konfigurationsdateien vorbereiten

Kopieren Sie zuerst die `.example`-Vorlagen im Verzeichnis `config/`:

```bash
cp config/user.yaml.example config/user.yaml
cp config/ontology.yaml.example config/ontology.yaml
cp config/classifier_paths.yaml.example config/classifier_paths.yaml
```

### 2. Zwingend erforderliche Anpassungen

Folgende Konfigurationsdateien müssen Sie konkret anpassen, damit das System einsatzbereit ist:

1. **`config/user.yaml` (Persönliche Benutzerdaten):**  
   Öffnen Sie diese Datei und passen Sie folgende Einträge an:  
   - **`name`**: Ihr vollständiger Name (wird u. a. für die automatische Generierung von E-Mail-Signaturen verwendet).  
   - **`email`**: Ihre **primäre Hochschul-E-Mail-Adresse**. Diese ist essenziell, da das Outlook-Makro und die Backend-Skripte diese Adresse verwenden, um Ihr Outlook-Postfach auf dem System zu lokalisieren und E-Mails daraus zu exportieren.  
   - **`emails`**: Eine Liste all Ihrer E-Mail-Adressen und Aliase (z. B. falls Sie mehrere Hochschul-Adressen besitzen). Das System nutzt diese Liste, um eigene gesendete E-Mails zu identifizieren.  

   *Erklärungen & Optionen:* Siehe **[user.yaml in der Konfiguration](configuration.md#1-useryaml)**.

2. **`config/folders.yaml` (Zu überwachende Verzeichnisse):**  
   Diese Datei existiert standardmäßig nicht als Template, sondern muss von Ihnen neu angelegt werden, falls Sie die Indexierungsfunktion (`mcp-uni memory update` bzw. `python scripts/index_memory.py`) nutzen möchten. Erstellen Sie die Datei `config/folders.yaml` und tragen Sie die gewünschten Pfade ein:
   ```yaml
   folders:
     - "D:/TH_Koeln/Lehre/Module"
     - "D:/TH_Koeln/PAV/Studierende"
   ```
   - **`folders`**: Liste von absoluten Pfaden auf Ihrer Festplatte, die vom Crawler überwacht und in die Vektordatenbank indiziert werden sollen.  

   *Erklärungen & Optionen:* Siehe **[folders.yaml in der Konfiguration](configuration.md#2-foldersyaml)**.

3. **`config/classifier_paths.yaml` (Archivierungspfade):**  
   Öffnen Sie diese Datei und konfigurieren Sie die physischen Zielordner auf Ihrer Festplatte für die jeweiligen E-Mail-Klassen (z. B. `BachelorThesis`, `MasterThesis`, `Other`):
   ```yaml
   class_paths:
     BachelorThesis: "D:/TH_Koeln/PAV/Studierende/Bachelorarbeit"
     MasterThesis: "D:/TH_Koeln/PAV/Studierende/Masterarbeit"
     Other: "D:/TH_Koeln/PAV/Studierende/OtherMails"
   ```
   Hierhin sortiert der E-Mail-Klassifikator die E-Mails physisch ein.

   *Erklärungen & Optionen:* Siehe **[classifier_paths.yaml in der Konfiguration](configuration.md#4-classifier_pathsyaml)**.

### 3. Studierendendaten synchronisieren

Falls Sie bereits eine `students.yaml` (z. B. über die Outlook-Makros) erstellt haben, synchronisieren Sie diese mit der SQLite-Datenbank:

```bash
mcp-uni db sync-students
```

Eine detaillierte Beschreibung aller Konfigurationsoptionen und der verschiedenen `.yaml` Dateien finden Sie auf der Seite **[Konfiguration](configuration.md)**.
