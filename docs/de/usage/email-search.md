# E-Mail Suche (Email Search GUI)

Die E-Mail Schnellsuche ermöglicht es, tausende von archivierten E-Mails in Sekundenschnelle zu durchsuchen. Sie ist besonders nützlich, um schnell Kontext zu einer Anfrage zu finden, ohne Outlook öffnen zu müssen.

## Starten der GUI

Führen Sie das folgende Skript aus:

```bash
python scripts/email_search_gui.py
```

Die GUI öffnet sich automatisch in Ihrem Standardbrowser.

## Funktionen

*   **Schnellsuche:** Suchen Sie nach Namen, E-Mail-Adressen, Betreffzeilen oder Dateinamen.  
*   **Automatische Vorschläge:** Während der Eingabe werden passende Absender oder Begriffe vorgeschlagen.  
*   **Getrennte Ansichten:** Ergebnisse werden klar nach **Posteingang (Inbox)** und **Gesendeten Elementen (SentItems)** getrennt angezeigt.  
*   **Vorschau:** Klicken Sie auf eine E-Mail in der Liste, um eine HTML-Vorschau des Inhalts direkt in der GUI zu sehen.  
*   **Integration:** Öffnen Sie die gefundene E-Mail mit einem Klick direkt in Outlook oder springen Sie zum entsprechenden Ordner im Windows Explorer.  

## Funktionsweise

Die E-Mail-Schnellsuche basiert auf einem zweistufigen Caching-System, das aus zwei lokalen JSON-Dateien im Verzeichnis `data/cache/` besteht.

### 1. Der Haupt-Suchindex (`data/cache/email_search_cache.json`)

Dieser Index speichert alle indizierten E-Mails als eine JSON-Liste von Objekten. Die Quelldaten dafür sind `.msg`- und `.eml`-Dateien, die aus den in den folgenden Konfigurationsdateien definierten Pfaden stammen:
*   `config/classifier_paths.yaml` (bzw. `config/classifier_paths.yaml.example` als Fallback): Definiert die Pfade für die jeweiligen E-Mail-Klassen unter `class_paths` (z. B. `BachelorThesis`, `MasterThesis`, `PraxisProjekt` etc.).
*   `config/train_test_folders.yaml`: Definiert die Pfade `train_path` und `test_path`.

Der Cache wird beim ersten Start oder bei Vorhandensein neuer E-Mails in diesen Pfaden automatisch aktualisiert. Jedes Objekt im JSON-Array von `email_search_cache.json` besitzt die folgenden konkreten Pfade/Attribute:

*   `subject`: Der Betreff der E-Mail (String).
*   `from`: Die E-Mail-Adresse des Absenders (String).
*   `from_name`: Der Name des Absenders (String).
*   `to`: Eine Liste der Empfänger. Jedes Element in dieser Liste ist entweder:
    *   Ein JSON-Objekt mit den Pfaden:
        *   `to[].name`: Der Name des Empfängers.
        *   `to[].email`: Die E-Mail-Adresse des Empfängers.
    *   Oder direkt ein String (z. B. eine reine E-Mail-Adresse).
*   `date`: Das Datum der E-Mail im ISO-Format (String).
*   `path`: Der absolute Dateipfad zur ursprünglichen E-Mail-Datei auf der Festplatte (String).
*   `filename`: Der Dateiname der E-Mail (String).
*   `folder`: Die Klassifizierung des Ordners (String, entweder `"Inbox"` oder `"SentItems"`), ermittelt anhand der Pfad-Segmente.

Dies ermöglicht eine extrem performante Suche, da nicht bei jeder Anfrage das Dateisystem durchsucht werden muss.

### Intelligente Zuordnung und SentItems-Erkennung

Eine besondere Herausforderung bei der Suche nach gesendeten E-Mails besteht darin, dass der Absender (`From`) bei diesen E-Mails stets der Benutzer selbst (z. B. "Daniel Gaida") ist. Sucht man nun nach einem Studierenden (z. B. "Mustermann"), würde eine reine Absendersuche diese E-Mails nicht finden.

Die Schnellsuche löst dies wie folgt:  
1. **Empfänger-Indizierung:** Beim Indizieren von E-Mails werden auch die Empfänger (`To`) mit Name und E-Mail-Adresse erfasst und im Index gespeichert.  
2. **Pfad-basierte Suche:** Die Suchanfrage wird zusätzlich gegen den gesamten Dateipfad (der den Ordnernamen des Studierenden enthält) abgeglichen.  
3. **Erweiterter Abgleich:** Eine E-Mail gilt als Treffer, wenn der Suchbegriff im Betreff, im Absender, im Empfänger, im Dateinamen oder im gesamten Dateipfad vorkommt. Dadurch werden gesendete Mails an Studierende zuverlässig gefunden.  

Die Bestimmung, ob eine E-Mail in **Inbox** oder **SentItems** liegt, erfolgt anhand der Pfad-Segmente. Ordner mit Bezeichnungen wie `SentItems`, `Sent Items`, `Gesendete Elemente`, `Gesendete Objekte` oder `Sent` (case-insensitiv) werden automatisch als **SentItems** klassifiziert.

### 2. Der Vorschlags-Cache (`data/cache/suggestions_cache.json`)

Um Verzögerungen bei der Eingabe von Suchbegriffen zu vermeiden, verwendet die GUI einen dedizierten, persistierten Cache für Vorschläge (`data/cache/suggestions_cache.json`).

Diese Datei enthält ein flaches JSON-Array von Strings (z. B. `["Albert", "albert@test.com", "Informatik", ...]`), das wie folgt aufgebaut und erweitert wird:

*   **Initialisierung:** Beim ersten Start wird der Vorschlags-Cache mit einer Liste von im Hochschulkontext üblichen Standardbegriffen vorbefüllt und automatisch um alle Namen und E-Mail-Adressen aus dem Haupt-Index (`data/cache/email_search_cache.json`) erweitert. Konkret werden dafür folgende Werte herangezogen:
    *   Die Werte des Schlüssels `from_name` (Absendername).
    *   Die Werte des Schlüssels `from` (Absender-E-Mail).
    *   Die Werte aus der Empfängerliste `to`:
        *   Der Pfad/Schlüssel `to[].name` (Empfängername) von Objekten in der Empfängerliste.
        *   Der Pfad/Schlüssel `to[].email` (Empfänger-E-Mail) von Objekten in der Empfängerliste.
        *   Direkte String-Elemente der Empfängerliste.
*   **Unter-Millisekunden-Antworten:** Die Autovervollständigung sucht direkt in diesem optimierten In-Memory-Set, was eine nahezu verzögerungsfreie Anzeige von Vorschlägen ermöglicht.
*   **Präfix-Priorisierung:** Suchbegriffe, die mit der Eingabe starten, werden priorisiert vor Begriffen angezeigt, die die Eingabe an einer anderen Stelle enthalten.
*   **Dynamische Erweiterung:** Sobald Sie eine neue Suche über den "Suchen"-Button in der GUI ausführen, wird der eingegebene Suchbegriff (sofern er mindestens 2 Zeichen lang ist) automatisch in die JSON-Liste des Vorschlags-Caches übernommen und dauerhaft in `suggestions_cache.json` gespeichert. Bei zukünftigen Suchen steht dieser Begriff sofort zur Verfügung.
