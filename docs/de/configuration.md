# Konfiguration

Das MCP University Memory System wird über Konfigurationsdateien im Verzeichnis `config/` sowie Umgebungsvariablen gesteuert. Diese Seite dient als zentrale Referenz für alle Einstellungen.

---

## 1. user.yaml
Definiert die persönlichen Daten des Benutzers (meist des Professors oder Institutsleiters). Diese Daten werden für die Anonymisierung (bei Cloud-LLMs), Kalenderbuchungen, E-Mail-Sortierung und Signatur-Generierung verwendet.

| Option | Beschreibung | Beispiel |
|---|---|---|
| `name` | Vollständiger Name für Signaturen | `"Daniel Gaida"` |
| `email` | Primäre Hochschul-E-Mail-Adresse | `"daniel.gaida@th-koeln.de"` |
| `emails` | Liste aller eigenen E-Mail-Adressen | `["daniel.gaida@th-koeln.de", "prof.gaida@..."]` |

**Beispiel (`config/user.yaml`):**
```yaml
name: "Daniel Gaida"
email: "daniel.gaida@th-koeln.de"
emails:
  - "daniel.gaida@th-koeln.de"
```

---

## 2. folders.yaml
Definiert, welche lokalen Verzeichnisse vom Crawler (`mcp-uni index`) überwacht und indiziert werden sollen.

| Option | Beschreibung | Standard |
|---|---|---|
| `folders` | Liste absoluter Pfade zu den indizierten Dokumenten/Ordnern. | `[]` |
| `exclude_patterns` | Glob-Muster für auszuschließende Dateien/Ordner. | `[.git, node_modules, ...]` |
| `supported_extensions` | Zu verarbeitende Dateiendungen. | `[.pdf, .docx, .md, .txt, .msg, .eml]` |

**Beispiel (`config/folders.yaml`):**
```yaml
folders:
  - "D:/TH_Koeln/Lehre/Module"
  - "D:/TH_Koeln/PAV/Studierende"
exclude_patterns:
  - "**/tmp/*"
  - "**/*.bak"
supported_extensions:
  - ".pdf"
  - ".docx"
  - ".md"
  - ".msg"
```

---

## 3. models.yaml
Konfiguriert die lokalen KI-Modelle für LLMs (via Ollama), Embeddings, Reranking und Kalender-Verhalten.

### LLM (Ollama)
| Option | Beschreibung | Standard |
|---|---|---|
| `model` | Name des verwendeten Ollama-Modells | `gemma4:e2b` |
| `temperature` | Kreativität des Modells (0 = deterministisch) | `0` |
| `base_url` | URL zum lokalen Ollama-Server | `http://localhost:11434` |
| `num_ctx` | Kontextfenster-Größe | `32768` |

### Embeddings & Reranker
| Option | Beschreibung | Standard |
|---|---|---|
| `embeddings.model` | HuggingFace Modellname für Text-Vektoren | `BAAI/bge-m3` |
| `reranker.model` | HuggingFace Modellname für Reranking | `BAAI/bge-reranker-v2-m3` |

### Kalender (Calendar)
| Option | Beschreibung | Standard |
|---|---|---|
| `send_invitations_automatically` | Bestimmt, ob Kalendereinladungen sofort an den Studenten gesendet werden (`true`) oder nur als Entwurf in Outlook gespeichert werden (`false`). | `false` |

**Beispiel (`config/models.yaml`):**
```yaml
llm:
  model: "gemma4:e2b"
  temperature: 0
  base_url: "http://localhost:11434"
  num_ctx: 32768

embeddings:
  model: "BAAI/bge-m3"

reranker:
  model: "BAAI/bge-reranker-v2-m3"

calendar:
  send_invitations_automatically: false
```

---

## 4. classifier_paths.yaml
Ordnet den E-Mail-Klassen (Kategorien aus dem ML-Klassifikator) die jeweiligen physischen Zielpfade auf der Festplatte zu, in die E-Mails einsortiert/archiviert werden sollen.

**Beispiel (`config/classifier_paths.yaml`):**
```yaml
class_paths:
  BachelorThesis: "D:/TH_Koeln/PAV/Studierende/Bachelorarbeit"
  MasterThesis: "D:/TH_Koeln/PAV/Studierende/Masterarbeit"
  PraxisProjekt: "D:/TH_Koeln/PAV/Studierende/Praxisprojekt"
  InformatikProjekt: "D:/TH_Koeln/PAV/Studierende/Informatikprojekt"
  WASP: "D:/TH_Koeln/PAV/Studierende/WASP"
  Other: "D:/TH_Koeln/PAV/Studierende/OtherMails"
```

---

## 5. train_test_folders.yaml
Konfiguriert die Quellordner für das Training und die Evaluierung des E-Mail-Klassifizierers.

**Beispiel (`config/train_test_folders.yaml`):**
```yaml
train_path: "data/classifier/train"
test_path: "data/classifier/test"
```

---

## 6. ontology.yaml
Definiert das Schema des semantischen Wissensgraphen (Knotentypen, Beziehungstypen und Kantenprioritäten). Dies steuert, wie Alias-Namen gelernt und Edge-Konflikte (z.B. Überschreiben einer "angefragt" Beziehung durch eine "schreibt" Beziehung) aufgelöst werden.

*   `node_types`: Gültige Entitätstypen (z.B. Studierende, Modul, Fakultät).  
*   `edge_types`: Gültige Beziehungstypen (z.B. schreibt Bachelorarbeit, ist Erstprüfer).  
*   `edge_priorities`: Definiert die Priorität von Kanten, sodass höherwertige Beziehungen (z.B. "hat Bachelorarbeit abgeschlossen") geringerwertige Vorgängerbeziehungen ("schreibt Bachelorarbeit") im Graphen automatisch überschreiben oder ersetzen dürfen.  

---

## 7. secrets.env und .env (Umgebungsvariablen)
Einige sensible Einstellungen und System-Schalter werden über Umgebungsvariablen gesteuert, die im Hauptverzeichnis in einer `.env` oder `secrets.env` Datei abgelegt werden können:

| Variable | Beschreibung | Beispiel |
|---|---|---|
| `HF_TOKEN` | Hugging Face Access Token für den Zugriff auf private Modelle oder zur Erhöhung von Ratelimits | `hf_xyz...` |
| `DEBUG` | Aktiviert detailliertes Logging (True/False) | `True` |
| `CONFIG_DIR` | Ändert den Pfad zum Konfigurationsverzeichnis | `./config` |

---

## Zurück zur Einrichtung
Zurück zur Installationsanleitung gelangen Sie auf der Seite **[Einrichtung der Software](setup.md)**.
