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

Die Suche basiert auf einem lokalen JSON-Index (`data/cache/email_search_cache.json`). Beim ersten Start oder wenn neue E-Mails in die konfigurierten Pfade (siehe [Konfiguration](../configuration.md)) verschoben werden, wird der Index automatisch aktualisiert.

Dies ermöglicht eine extrem performante Suche, da nicht bei jeder Anfrage das Dateisystem durchsucht werden muss.

### Intelligente Zuordnung und SentItems-Erkennung

Eine besondere Herausforderung bei der Suche nach gesendeten E-Mails besteht darin, dass der Absender (`From`) bei diesen E-Mails stets der Benutzer selbst (z. B. "Daniel Gaida") ist. Sucht man nun nach einem Studierenden (z. B. "Mustermann"), würde eine reine Absendersuche diese E-Mails nicht finden.

Die Schnellsuche löst dies wie folgt:
1. **Empfänger-Indizierung:** Beim Indizieren von E-Mails werden auch die Empfänger (`To`) mit Name und E-Mail-Adresse erfasst und im Index gespeichert.
2. **Pfad-basierte Suche:** Die Suchanfrage wird zusätzlich gegen den gesamten Dateipfad (der den Ordnernamen des Studierenden enthält) abgeglichen.
3. **Erweiterter Abgleich:** Eine E-Mail gilt als Treffer, wenn der Suchbegriff im Betreff, im Absender, im Empfänger, im Dateinamen oder im gesamten Dateipfad vorkommt. Dadurch werden gesendete Mails an Studierende zuverlässig gefunden.

Die Bestimmung, ob eine E-Mail in **Inbox** oder **SentItems** liegt, erfolgt anhand der Pfad-Segmente. Ordner mit Bezeichnungen wie `SentItems`, `Sent Items`, `Gesendete Elemente`, `Gesendete Objekte` oder `Sent` (case-insensitiv) werden automatisch als **SentItems** klassifiziert.

### Performanter Suchbegriff-Cache (Suggestions Cache)

Um Verzögerungen bei der Eingabe von Suchbegriffen zu vermeiden, verwendet die GUI einen dedizierten, persistierten Cache für Vorschläge (`data/cache/suggestions_cache.json`).

* **Initialisierung:** Beim ersten Start wird der Cache mit einer Liste von im Hochschulkontext üblichen Standardbegriffen (z. B. *Informatik*, *Bachelorarbeit*, *Masterarbeit*, *Kolloquium*, *Prüfung*, etc.) sowie allen im Index vorhandenen Namen und E-Mail-Adressen (von Absendern und Empfängern) vorbefüllt.
* **Unter-Millisekunden-Antworten:** Die Autovervollständigung sucht direkt in diesem optimierten In-Memory-Set, was eine nahezu verzögerungsfreie Anzeige von Vorschlägen ermöglicht.
* **Präfix-Priorisierung:** Suchbegriffe, die mit der Eingabe starten, werden priorisiert vor Begriffen angezeigt, die die Eingabe an einer anderen Stelle enthalten.
* **Dynamische Erweiterung:** Sobald Sie eine neue Suche über den "Suchen"-Button ausführen, wird der eingegebene Suchbegriff automatisch in den Cache übernommen und dauerhaft gespeichert. Bei zukünftigen Suchen steht dieser Begriff sofort zur Verfügung.
