# Personen-Steckbriefe (Person Profiles)

Das System ermöglicht die automatische Erstellung und Aktualisierung von Personen-Steckbriefen basierend auf dem E-Mail-Verlauf und Informationen aus dem Wissensgraphen.

## Übersicht

Ein Steckbrief (Profil) fasst wichtige Informationen über eine Person zusammen, wie z.B.:  
- Rolle (Studierende, Lehrende, etc.)  
- Bevorzugte Anrede  
- Erster Kontakt  
- Relevante Projekte, Thesen oder Aufgaben  

Diese Steckbriefe werden im Markdown-Format gespeichert und dienen als zusätzlicher Kontext für das LLM, wenn eine E-Mail beantwortet werden soll. Dabei wird nicht nur der Steckbrief des Absenders (z.B. Student), sondern auch der Steckbrief des Nutzers des Tools (wie in `config/user.yaml` definiert) an das LLM übergeben, um eine konsistente Tonalität und korrekten Kontext zu gewährleisten.

## Funktionsweise

### Bestimmung der Anrede (Du/Sie)
Die bevorzugte Anrede wird intelligent bestimmt:
- Es werden die letzten 4 direkt gesendeten E-Mails vom Nutzer an die Person und umgekehrt analysiert.
- "Sammelmails" (z.B. mit "Liebe Kolleg*innen" oder "Hallo zusammen") werden dabei ignoriert.
- Wenn keine direkten E-Mails gefunden werden, erfolgt ein Fallback auf die neuesten verfügbaren Mails.


### Erstellung
Wenn für eine E-Mail-Adresse noch kein Steckbrief existiert, wird dieser beim Versuch, eine E-Mail zu beantworten (oder manuell via CLI), automatisch erstellt. Dabei werden alle verfügbaren E-Mails dieser Person analysiert sowie Informationen aus dem Wissensgraphen einbezogen. Ein Steckbrief kann auch dann erstellt werden, wenn noch keine E-Mails vorhanden sind, sofern Informationen im Wissensgraphen vorliegen.

### Automatische Aktualisierung
Steckbriefe sind dynamisch. Das System verfolgt in einer separaten Datenbank (`profiles_tracking.db`), welche E-Mails bereits für die Erstellung eines Steckbriefs verwendet wurden. 

Wenn neue E-Mails für eine Person im System gefunden werden, wird der bestehende Steckbrief automatisch durch das LLM aktualisiert. Dabei werden nur E-Mails berücksichtigt, die sowohl noch nicht verarbeitet wurden als auch zeitlich nach der letzten Änderung der Steckbrief-Datei liegen. Das alte Profil dient dabei als Basis, in die nur die neuen Informationen integriert werden.

## CLI Befehle

### Steckbriefe aktualisieren
Sie können Steckbriefe manuell über die CLI aktualisieren:

```bash
# Alle existierenden Steckbriefe aktualisieren
mcp-uni profiles update

# Einen spezifischen Steckbrief aktualisieren
mcp-uni profiles update --email student@example.com
```

### Steckbrief erstellen (Legacy/Direkt)
```bash
mcp-uni index --profile student@example.com
```

## Fehlerbehebung: Kodierungsprobleme (Umlaute)

Das System verfügt über eine robuste Dekodierung für MIME-Header (RFC 2047). Dies verhindert Fehler bei der Verarbeitung von Namen mit Umlauten (z.B. `=?utf-8?Q?'Heike_Fr=C3=B6lin'?=`), die in Outlook oft vorkommen. Falls dennoch Probleme bei der Ordnererstellung auftreten, stellen Sie sicher, dass Ihr Dateisystem UTF-8 unterstützt.

## Dateipfade  
- **Steckbriefe:** Standardmäßig unter `D:\Steckbriefe\` (konfigurierbar).  
- **Tracking-Datenbank:** `data/profiles_tracking.db`.  

### Performance-Hinweis
Um eine schnelle Erstellung der Steckbriefe zu ermöglichen, berücksichtigt das System maximal die **100 neuesten E-Mails** einer Person. Dies stellt sicher, dass die Kontextgröße des LLMs optimal genutzt wird, ohne die Verarbeitungszeit unnötig zu verlängern.
