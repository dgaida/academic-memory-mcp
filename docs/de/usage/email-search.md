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
