# Architecture

The MCP University Memory System is modularly designed to ensure flexibility in models and robustness in data processing.

## System Overview

The following diagram shows the interaction between the core components:

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
        S --> LLM[Ollama / gemma4:e2b]
        CL[Email Classifier] --> P3
    end

    subgraph "Storage & Index Layer"
        C --> IDX[Search Index]
        C --> DB[Metadata Store / SQLite]
    end

    subgraph "Interface Layer"
        DB --> MCP[FastMCP Server]
        IDX --> MCP
        MCP --> CLI[CLI / mcp-uni]
        MCP --> AGENT[AI Agent]
    end
```

## Data Flow

1.  **Crawling:** The crawler scans directories and compares file hashes with the SQLite DB.  
2.  **Parsing:** New or modified files are passed through the factory to the appropriate parser.  
3.  **Classification:** The `EmailClassifier` can optionally be used to categorize emails before or after indexing.  
4.  **Summarization:** The extracted text is sent (truncated to the context window) to Ollama to obtain a structured summary.  
5.  **Indexing:** The full text is stored in the Search Index for BM25 and vector search.  
6.  **Delivery:** Tools are defined via FastMCP that access the DB and index to answer queries from agents.  

## Process Lifecycle

```mermaid
sequenceDiagram
    participant FS as File System
    participant CR as Crawler
    participant CL as Email Classifier
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
            opt If Email
                CR->>CL: Classify Email
                CL-->>CR: Label
            end
            CR->>SM: Generate Summary
            SM-->>CR: Markdown Summary
            CR->>IX: Add to Index
            CR->>DB: Update Metadata & Summary
        end
    end
```
