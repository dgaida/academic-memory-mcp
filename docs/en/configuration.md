# Configuration

The MCP University Memory System is controlled via configuration files in the `config/` directory as well as environment variables. This page serves as a central reference for all settings.

---

## 1. user.yaml
Defines the personal data of the user (typically the professor or institute director). This data is used for several core functions of the system:

- **`name`**: Full name of the user (e.g., `"Daniel Gaida"`). This name is used for:
  - Automatic creation and placement of email signatures and greetings in draft replies.
  - Anonymization of personal data if cloud-based LLMs are used.
- **`email`**: The **primary university email address** (e.g., `"daniel.gaida@th-koeln.de"`). This setting is **absolutely essential** as the Outlook macro and backend scripts use this address to locate your Outlook mailbox on the system to export and process emails from it. Without the correct primary address, the mailbox in Outlook cannot be identified.
- **`emails`**: A list of all your email addresses and aliases (e.g., `["daniel.gaida@th-koeln.de", "daniel.gaida@fh-koeln.de"]`). The system uses this list to:
  - Recognize which emails were sent by you (e.g., in the `SentItems` folder).
  - Distinguish your own sent emails from incoming emails to prevent infinite loops during processing.
  - Ensure that emails sent to alternative aliases are also correctly assigned to your profile and processed.

| Option | Description | Example |
|---|---|---|
| `name` | Full name for signatures, anonymization, and templates | `"Daniel Gaida"` |
| `email` | Primary university email address (crucial for Outlook mailbox identification) | `"daniel.gaida@th-koeln.de"` |
| `emails` | List of all your own email addresses and aliases (for sender identification) | `["daniel.gaida@th-koeln.de", "prof.gaida@..."]` |

**Example (`config/user.yaml`):**
```yaml
name: "Daniel Gaida"
email: "daniel.gaida@th-koeln.de"
emails:
  - "daniel.gaida@th-koeln.de"
```

---

## 2. folders.yaml
Defines which local directories are monitored and indexed by the crawler (`mcp-uni index` / `mcp-uni memory update`).

| Option | Description | Default |
|---|---|---|
| `folders` | List of absolute paths to the indexed documents/folders. | `[]` |
| `exclude_patterns` | Glob patterns for files/folders to exclude. | `[.git, node_modules, ...]` |
| `supported_extensions` | File extensions to process. | `[.pdf, .docx, .md, .txt, .msg, .eml]` |

**Example (`config/folders.yaml`):**
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
Configures the local AI models used for LLMs (via Ollama), embeddings, reranking, and calendar behavior.

### LLM (Ollama)
| Option | Description | Default |
|---|---|---|
| `model` | Name of the Ollama model used | `gemma4:e2b` |
| `temperature` | Creativity of the model (0 = deterministic) | `0` |
| `base_url` | URL to the local Ollama server | `http://localhost:11434` |
| `num_ctx` | Context window size | `32768` |

### Embeddings & Reranker
| Option | Description | Default |
|---|---|---|
| `embeddings.model` | HuggingFace model name for text vectors | `BAAI/bge-m3` |
| `reranker.model` | HuggingFace model name for reranking | `BAAI/bge-reranker-v2-m3` |

### Calendar
| Option | Description | Default |
|---|---|---|
| `send_invitations_automatically` | Determines whether calendar invitations are sent to students immediately (`true`) or only saved as a draft in Outlook (`false`). | `false` |

**Example (`config/models.yaml`):**
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
Maps email classes (categories from the ML classifier) to their respective physical target paths on the hard drive where emails should be filed/archived.

**Example (`config/classifier_paths.yaml`):**
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
Configures the source folders for training and evaluating the email classifier.

**Example (`config/train_test_folders.yaml`):**
```yaml
train_path: "data/classifier/train"
test_path: "data/classifier/test"
```

---

## 6. ontology.yaml
Defines the schema of the semantic knowledge graph (node types, relation types, and edge priorities). This controls how alias names are learned and how edge conflicts are resolved.

*   `node_types`: Valid entity types (e.g., Student, Module, Department).
*   `edge_types`: Valid relation types (e.g., writes BachelorThesis, is primary examiner).
*   `edge_priorities`: Defines the priority of edges, so that higher-value relationships (e.g., "completed BachelorThesis") automatically overwrite or replace preceding lower-value relationships ("writing BachelorThesis") in the graph.

---

## 7. Secrets and Environment Variables
Some sensitive settings and system switches are controlled via environment variables, which can be stored in a `.env` or `secrets.env` file in the root directory:

| Variable | Description | Example |
|---|---|---|
| `HF_TOKEN` | Hugging Face Access Token to access private models or increase rate limits | `hf_xyz...` |
| `DEBUG` | Enables detailed logging (True/False) | `True` |
| `CONFIG_DIR` | Overrides the path to the configuration directory | `./config` |

---

## Back to Setup
To return to the setup guide, please visit the **[Setting Up the Software](setup.md)** page.
