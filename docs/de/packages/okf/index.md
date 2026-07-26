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
