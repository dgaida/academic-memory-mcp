# Architektur

Das MCP University Memory System ist modular aufgebaut, um Flexibilität bei den Modellen und Robustheit bei der Datenverarbeitung zu gewährleisten.

## Systemübersicht

Das folgende Diagramm zeigt die Interaktion zwischen den Kernkomponenten:

```mermaid
graph TD
    subgraph "Ingestion Layer"
        C[Crawler] --> P[Parser Factory]
        P --> P1[PDF Parser]
        P --> P2[Text Parser]
        P --> P3[Mail Parser]
    end

    subgraph "Intelligence Layer"
        C --> S[Summarizer]
        S --> LLM[Ollama / gemma2]
    end

    subgraph "Storage & Index Layer"
        C --> IDX[Search Index / Suchindex]
        C --> DB[Metadata Store / SQLite]
    end

    subgraph "Interface Layer"
        DB --> MCP[FastMCP Server]
        IDX --> MCP
        MCP --> CLI[CLI / mcp-uni]
        MCP --> AGENT[AI Agent]
    end
```

## Datenfluss

1.  **Crawling:** Der Crawler scannt Verzeichnisse und vergleicht Dateihashes mit der SQLite-DB.  
2.  **Parsing:** Neue oder geänderte Dateien werden durch die Factory an den passenden Parser übergeben.  
3.  **Summarization:** Der extrahierte Text wird (gekürzt auf das Kontextfenster) an Ollama gesendet, um eine strukturierte Zusammenfassung zu erhalten.  
4.  **Indexierung:** Der Volltext wird im Suchindex-Index für die BM25- und Vektorsuche hinterlegt.  
5.  **Bereitstellung:** Über FastMCP werden Tools definiert, die auf die DB und den Index zugreifen, um Anfragen von Agenten zu beantworten.  

## Prozesslebenszyklus

```mermaid
sequenceDiagram
    participant FS as Dateisystem
    participant CR as Crawler
    participant SM as Summarizer
    participant DB as SQLite
    participant IX as SearchIndex

    CR->>FS: Scan Directory
    FS-->>CR: File List
    loop For each file
        CR->>DB: Check Hash
        DB-->>CR: Needs Update?
        alt Yes
            CR->>FS: Read Content
            CR->>SM: Generate Summary
            SM-->>CR: Markdown Summary
            CR->>IX: Add to Index
            CR->>DB: Update Metadata & Summary
        end
    end
```
