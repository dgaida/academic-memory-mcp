# Personen-Steckbriefe (Person Profiles)

Das System ermöglicht die automatische Erstellung und Aktualisierung von Personen-Steckbriefen basierend auf dem E-Mail-Verlauf und Informationen aus dem Wissensgraphen.

## Übersicht

Ein Steckbrief (Profil) fasst wichtige Informationen über eine Person zusammen, wie z.B.:  
- Rolle (Studierende, Lehrende, etc.)  
- Bevorzugte Anrede  
- Erster Kontakt  
- Relevante Projekte, Thesen oder Aufgaben  

Diese Steckbriefe werden im Markdown-Format gespeichert und dienen als zusätzlicher Kontext für das LLM, wenn eine E-Mail beantwortet werden soll.

## Funktionsweise

### Erstellung
Wenn für eine E-Mail-Adresse noch kein Steckbrief existiert, wird dieser beim Versuch, eine E-Mail zu beantworten (oder manuell via CLI), automatisch erstellt. Dabei werden alle verfügbaren E-Mails dieser Person analysiert.

### Automatische Aktualisierung
Steckbriefe sind dynamisch. Das System verfolgt in einer separaten Datenbank (`profiles_tracking.db`), welche E-Mails bereits für die Erstellung eines Steckbriefs verwendet wurden. 

Wenn neue E-Mails für eine Person im System gefunden werden, wird der bestehende Steckbrief automatisch durch das LLM aktualisiert, wobei das alte Profil als Basis dient und nur die neuen Informationen integriert werden.

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
