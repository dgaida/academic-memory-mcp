# Open Knowledge Format (OKF) Package

Das `academic_okf` Sub-Package konvertiert PDF-Dokumentensammlungen in ein [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) Wissensbundle.

Das Ziel besteht nicht nur darin, Dokumente in Markdown zu konvertieren, sondern unstrukturierte Dokumente in eine strukturierte, herkunftsbewusste (provenance-aware) Wissensdatenbank zu verwandeln.

Das generierte OKF-Bundle enthält:

- Originale Quelldokumente  
- Extrahierte Konzepte (Concepts)  
- Extrahierte Entitäten (Entities)  
- Extrahierte Definitionen  
- Extrahierte Tabellen  
- Einen Index zur Navigation  

Die resultierende Wissensdatenbank kann als Grundlage für Retrieval Augmented Generation (RAG), KI-Agenten, semantische Suche, Wissensgraphen und institutionelles Wissensmanagement verwendet werden.

---

## Verarbeitungs-Pipeline

Der gesamte Verarbeitungs-Workflow sieht wie folgt aus:

```
PDF-Dokumente
      |
      v
+-------------+
|  LiteParse  |
+-------------+
      |
      v
Markdown-Quelldokumente
      |
      v
+-----------------+
| LLM Extraktion  |
+-----------------+
      |
      +-----------------+
      |                 |
      v                 v

 documents/       Wissens-Artefakte

                  concepts/
                  entities/
                  definitions/
                  tables/

      |
      v

 index.md
```

---

## Generierte OKF-Struktur

Beispielhafte Ausgabestruktur:

```
my_okf/

├── index.md

├── documents/
│   ├── examination-guidelines.md
│   └── regulations.md

├── concepts/
│   ├── examination-supervision.md
│   └── competency-based-learning.md

├── entities/
│   ├── th-koeln.md
│   └── examination-office.md

├── definitions/
│   └── examination-supervision.md

└── tables/
    └── examination-aids.md
```

---

## Artefakt-Typen

### documents
Der Ordner `documents` enthält die originale Markdown-Repräsentation der Quell-PDFs. Die Konvertierung wird durch `LiteParse` durchgeführt.
Diese Dateien sind die primären Quellen und weisen die Herkunft (Provenance) für alle extrahierten Wissensartefakte nach.

### concepts
Konzepte repräsentieren abstrakte Wissenseinheiten (z. B. *Prüfungsaufsicht*, *Maschinelles Lernen*, *Transformer-Architektur*).

### entities
Entitäten repräsentieren konkrete, identifizierbare Objekte (z. B. Organisationen, Personen, Softwaresysteme, Kurse, Vorschriften).

### definitions
Definitionen repräsentieren explizite Erklärungen von Begriffen, die aus Dokumenten extrahiert wurden (z. B. *Modul*, *Lernergebnis*).

### tables
Tabellen enthalten strukturierte Informationen, die aus Dokumenten extrahiert wurden (z. B. Modulkataloge, Vergleichstabellen, Zeitpläne).

---

## Konfiguration

Die Konfiguration wird über die Klasse `OKFConfig` verwaltet. Diese steuert:  
- Pfadkonfigurationen (OKF-Ausgabeverzeichnis, PDF-Quellverzeichnis, Spezifikationsdatei).  
- Laden von Anmeldedaten aus env/secrets.  
- Registrierung und Verwaltung des `LLMClient`.  

### Beispielkonfiguration

```python
from pathlib import Path
from okf.config import OKFConfig
from okf.pipeline import run_okf_pipeline

config = OKFConfig(
    okf_dir=Path("./my_okf_bundle"),
    pdf_dir=Path("./my_pdfs"),
    spec_file=Path("config/SPEC.md")
)

# Starten der vollständigen Extraktions-Pipeline
run_okf_pipeline(config)
```

---

## LLM-Wissensextraktion

Der Extraktionsprozess nutzt das `llm_client` Package. Das LLM erhält:  
- Die OKF-Spezifikation  
- Das Quell-Markdown-Dokument  
- Extraktions-Anweisungen  

und liefert strukturiertes JSON zurück, das Konzepte, Entitäten, Definitionen, Tabellen und Beziehungen enthält, um das Provenance-Mapping und die strikte Ausrichtung an der OKF v0.2-Spezifikation sicherzustellen.

### Provenance & Ausrichtung an der Spezifikation (v0.2)
Jedes generierte Artefakt verweist unter `sources` mit dem ERFORDERLICHEN Attribut `resource` und einem Bundle-relativen Pfad auf sein Quelldokument (z. B. `/documents/examination-guidelines.md`).
Die generierte Datei `index.md` ist vollständig konform mit der OKF v0.2-Spezifikation und enthält nur die zulässige Zeile `okf_version: "0.2"` in ihrem Frontmatter.

---

## Installation, Ordnererstellung & Skripte

In diesem Abschnitt wird erklärt, wie man die notwendigen Werkzeuge für OKF installiert, die Ordnerstruktur aufbaut und das Generierungsskript ausführt.

### 1. Installation von `google-okf`

Das `academic_okf` Sub-Package basiert auf der Open Knowledge Format (OKF) Spezifikation von Google. Um das zugrundeliegende Framework `google-okf` oder verwandte Bibliotheken zu installieren, können Sie pip verwenden.

Führen Sie im Stammverzeichnis oder in Ihrer virtuellen Umgebung folgenden Befehl aus:

```bash
pip install google-okf
```

*(Hinweis: Stellen Sie sicher, dass Sie alle Abhängigkeiten des Projekts mittels `pip install -e .` oder über die `environment.yml` installiert haben.)*

### 2. OKF-Ordnererstellung & Speicherpfade

Die E-Mail-Klassen nutzen eigene Wissensordner (OKF). Der OKF-Zielordner muss in einem in `classifier_memory_paths.yaml` (unter `config/classifier_memory_paths.yaml`) definierten Verzeichnis erstellt werden.

Mehrere E-Mail-Klassen können sich einen OKF-Ordner teilen, was ebenfalls in dieser Konfigurationsdatei flexibel definiert werden kann. Ein Beispiel für einen solchen Eintrag in der `classifier_memory_paths.yaml`:

```yaml
class_paths:
  PAV_PO-Wechsel: "D:/PAV/okf"
  InformatikProjekt: "D:/PAV/okf" # Teilt sich denselben OKF-Ordner mit PAV_PO-Wechsel
```

Stellen Sie sicher, dass Sie den entsprechenden Zielpfad (z. B. `D:/PAV/okf`) vor der Pipeline-Ausführung manuell oder skriptgesteuert anlegen.

### 3. Ablageort der Original-PDF-Dokumente

Damit die Pipeline die Quelldokumente einlesen und konvertieren kann, müssen die Original-PDFs an einem bestimmten Ort abgelegt werden:

- Die PDFs müssen in einem **parallelen Ordner** namens `Memory` auf derselben Ebene wie der OKF-Ordner liegen.
- Wenn der OKF-Pfad beispielsweise `D:/PAV/okf` ist, müssen die PDFs im Ordner `D:/PAV/Memory` liegen.
- Innerhalb des `Memory` Ordners können Sie auch beliebige **Unterordner** anlegen, um Ihre PDF-Sammlung thematisch zu gliedern.

Beispielhafte Verzeichnisstruktur:
```text
D:/PAV/
├── okf/       <-- Der generierte OKF-Ordner (hier entsteht das Bundle)
└── Memory/    <-- Enthält die Original-PDFs
    ├── PO-Wechsel/
    │   └── InfosPOWechselHärtefall.pdf
    └── Sonstiges/
```

### 4. Das Generierungsskript `create_okf_from_memory`

Um die Konvertierung und LLM-Wissensextraktion anzustoßen, verwenden Sie das bereitgestellte Skript `create_okf_from_memory.py`.

Das Skript liest die Quell-PDFs aus dem `Memory` Ordner, konvertiert sie mittels `LiteParse`, extrahiert strukturierte Artefakte und schreibt das fertige OKF-Bundle in den konfigurierten OKF-Pfad.

**Ausführung:**

Sie können das Skript direkt über Python aufrufen:

```bash
python packages/okf/src/okf/scripts/create_okf_from_memory.py
```

Das Skript sucht standardmäßig nach dem konfigurierten Pfad, unterstützt aber auch die Steuerung über Umgebungsvariablen wie `OKF_DIR` und `PDF_DIR`.
