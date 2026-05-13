# GitHub Repository Review: MCP University

## 1. High-Level Summary
MCP University is a well-structured, offline-first knowledge management system. It effectively leverages local LLMs (Ollama) and vector databases (Qdrant) to provide an agentic experience for university-related documents. The recent restructuring to a top-level package layout improves standard Python project conventions.

### Top Improvement Priorities:
1.  **CI/CD Implementation**: Add automated testing, linting, and security scanning.
2.  **LLM Abstraction**: Transition from direct Ollama calls to a unified LLM client for better provider flexibility.
3.  **Enhanced Testing**: Increase test coverage, especially for the crawler and MCP server.
4.  **MinerU Integration**: Deepen the integration with magic-pdf for more robust document parsing.

---

## 2. Detailed Findings

### 1. Repository Structure
- **Key Issues**: The package was previously nested under `src/mcp_university`.
- **Improvement**: Successfully moved to the root (`./mcp_university`) to simplify imports and follow common practices for application-oriented repos.
- **Dead Code**: None identified.

### 2. Code Quality & Maintainability
- **Key Issues**: The `Summarizer` class is tightly coupled with the `ollama` library.
- **Improvement**: Wrap LLM calls in a client abstraction (see Section 7).
- **Naming**: Consistent and descriptive naming conventions are used throughout.

### 3. Documentation
- **Key Issues**: README is concise but missing detailed developer onboarding steps (e.g., setting up Ollama models).
- **Improvement**: Added `AGENTS.md` for AI assistant guidance. Recommend adding a "Developer Guide" to README.

### 4. Type Safety & Interfaces
- **Key Issues**: Most internal methods have type hints, but some complex types in `metadata/store.py` could be more specific.
- **Improvement**: Uses Pydantic for configuration, which is excellent.

### 5. Testing & Test Coverage
- **Key Issues**: Only 3 basic test files. Crawler and Watcher logic are largely untested in CI.
- **Improvement**: Implement integration tests that mock the filesystem and Ollama API.

### 6. Tooling & Automation
- **Key Issues**: Missing CI/CD, linting (Ruff/Flake8), and formatting (Black/Ruff).
- **Improvement**: Added GitHub Actions for Tests, Coverage (Codecov), CodeQL, and Auto-versioning.

### 7. LLM Integration
- **Key Issues**: Direct dependency on `ollama` in `mcp_university/summarizer/engine.py`.
- **Improvement**: Replace `ollama.Client` with `dgaida/llm_client` to allow users to switch between local and (optionally) cloud providers without code changes.

### 8. Security & Reliability
- **Key Issues**: SQLite and Qdrant use local paths; ensure these paths are configurable and handled safely.
- **Improvement**: Configurable via `config.py`. No hardcoded secrets found.

---

## 3. Refactoring & Improvement Roadmap

| Horizon | Timeframe | Focus |
|---|---|---|
| Short-term | Days | Implement CI/CD, add `AGENTS.md`, and cleanup. |
| Medium-term | Weeks | Migrate to `llm_client`, increase test coverage. |
| Long-term | Months | Add support for more complex university-specific data (e.g., Zotero integration). |

---

## 4. Examples

### GitHub Action: Auto-versioning
```yaml
name: Auto Versioning
on:
  push:
    branches: [main]
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dgaida/auto-version-action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

### LLM Client Migration
**Before:**
```python
self.client = ollama.Client(host=base_url)
response = self.client.generate(model=self.model, prompt=prompt)
```
**After (using llm_client):**
```python
from llm_client import LLMClient
self.client = LLMClient(provider="ollama", model=self.model, base_url=base_url)
response = self.client.generate(prompt)
```
