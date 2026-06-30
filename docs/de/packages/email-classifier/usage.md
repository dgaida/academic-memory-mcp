# Nutzung der Skripte

In diesem Abschnitt wird die Nutzung der benutzerfokussierten Skripte an konkreten Beispielen erläutert.

## E-Mail Sortierung (`sort_emails.py`)

Dieses Skript sortiert E-Mails basierend auf ihrer Klassifizierung, dem Semester und dem Studentennamen in eine strukturierte Ordnerhierarchie.

**Befehl:**
```bash
python -m email_classifier.scripts.sort_emails /pfad/zu/quellordner --config config/class_paths.yaml
```

### Vorher/Nachher Beispiel

**Vorher:**
```text
/quellordner/
├── 20240115_103000 - Frage zu Projekt.msg
├── 20240220_141500 - Anmeldung Bachelorarbeit.msg
└── 20231210_090000 - Hausaufgabe.msg
```

**Nachher:**
```text
/zielordner/
├── WS_2023_24/
│   └── Müller/
│       └── Inbox/
│           └── 20231210_090000 - Hausaufgabe.msg
├── SoSe_2024/
│   ├── Schmidt/
│   │   └── Inbox/
│   │       └── 20240115_103000 - Frage zu Projekt.msg
│   └── Weber/
│       └── Inbox/
│           └── 20240220_141500 - Anmeldung Bachelorarbeit.msg
└── sorted_emails.md  # Zusammenfassungs-Bericht
```

---

## Einzelvorhersage (`predict.py`)

Klassifiziert eine einzelne E-Mail und gibt die Wahrscheinlichkeitsverteilung aus.

**Befehl:**
```bash
python -m email_classifier.scripts.predict /pfad/zur/email.msg
```

**Beispielausgabe:**
```text
Klassifizierung für: 'Frage zu Projekt.msg'
Ergebnis: InformatikProjekt (Konfidenz: 0.92)

Wahrscheinlichkeiten:
- InformatikProjekt: 0.92
- BachelorThesis: 0.05
- Other: 0.03
```

---

## Batch-Klassifizierung (`classify_folder.py`)

Verschiebt alle E-Mails eines Ordners in Unterordner, die nach den vorhergesagten Klassen benannt sind (ohne Semester/Studenten-Logik).

**Befehl:**
```bash
python -m email_classifier.scripts.classify_folder /pfad/zu/quellordner
```

**Ergebnisstruktur:**
```text
/quellordner/
├── BachelorThesis/
│   └── mail1.msg
├── InformatikProjekt/
│   └── mail2.msg
└── Other/
    └── mail3.msg
```

---

## Sortierung nach Richtung (`sort_by_direction.py`)

Ein Hilfsskript, um E-Mails innerhalb der Klassenordner konsistent in `Inbox` und `SentItems` zu trennen.

**Befehl:**
```bash
python -m email_classifier.scripts.sort_by_direction /pfad/zu/daten
```
