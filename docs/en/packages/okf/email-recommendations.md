# Recommendations for Email Replying using OKF

This documentation describes how a Large Language Model (LLM) or AI agent deployed for automated or semi-automated email answering should optimally leverage the Open Knowledge Format (OKF). The recommendations are based on the core principles of the [Open Knowledge Format v0.2 Specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf).

---

## Core Concepts of OKF-Based Email Replying

An OKF bundle is not just a collection of static Markdown files. It is a structured, provenance-aware, and highly interconnected knowledge base. When utilizing OKF for email processing and replying, the LLM should follow these primary guidelines:

### 1. Progressive Disclosure
To preserve the LLM's context size and avoid introducing irrelevant noise, the system must apply the principle of *Progressive Disclosure*:  
- The system navigates the directory structure incrementally using `index.md` files.  
- Instead of loading the entire OKF knowledge bundle into the prompt at once, the agent first reads the top-level or subdirectory `index.md` (e.g., in `concepts/` or `tables/`) to get an overview of available topics.  
- Only when a specific concept or document is identified as highly relevant is that file read and ingested into the context.  

### 2. Concept-Centric RAG
In traditional RAG, unstructured text chunks are often loaded, breaking the logical cohesion of the source material. With OKF, RAG becomes *concept-centric*:  
- Every OKF artifact (concepts, entities, definitions, tables) represents a self-contained unit of knowledge.  
- The LLM should be instructed to search for complete concepts (e.g., `/concepts/examination-supervision.md`) and ingest them as atomic units.  
- This guarantees that regulations and definitions are always presented in their exact logical context.  

### 3. Graph-Linking Navigation
OKF concepts are linked together using standard Markdown links (e.g., `[Examination Regulations](/documents/examination-guidelines.md)`). An intelligent email agent should actively traverse these links:  
- When an email triggers a discussion about a specific concept, the agent can follow internal links to retrieve related concepts, definitions, or tables (e.g., navigating from an abstract concept to a concrete module catalog table).  
- This enables multi-hop reasoning to answer complex administrative inquiries accurately.  

### 4. Honoring Trust Tiers
When answering sensitive emails (e.g., legal inquiries regarding examination rules), the LLM must inspect the `verified` field in the OKF frontmatter:  
- **Human-Reviewed:** The highest trust tier. Concepts verified by a `human:<id>` actor can be treated as absolute truth.  
- **Machine-Confirmed:** Medium trust tier. Verified by automated validation workflows. Use with appropriate care.  
- **Unverified:** Lowest trust tier. Information without a `verified` key should be handled with caution in the email draft, potentially prompting a disclaimer recommending manual verification.  

### 5. Checking Freshness & Staleness
An email agent must not distribute outdated information. In OKF, temporal freshness is controlled via two frontmatter fields:  
- **`stale_after`:** The agent must compare the current date with the `stale_after` field. If the current date is greater than or equal to `stale_after`, the concept is stale. The agent should refrain from using this knowledge for direct answers or explicitly notify the user that the information might be outdated.  
- **`status`:** If a document has the status `deprecated` or `draft`, the agent should adapt its response strategy accordingly (e.g., not citing drafts as final regulatory agreements).  

### 6. Provenance & Footnotes
Every administrative claim made in a generated email should be fully backtracked to its source. OKF v0.2 implements a standardized citation scheme using Markdown footnotes:  
- The agent should cite the precise source of knowledge in the generated email draft (e.g., pointing back to `/documents/regulations.md`).  
- When OKF concepts use footnotes mapped to the `sources` array in the frontmatter, the LLM should resolve these references and present them as solid evidence (e.g., "According to Section 12 of the Examination Guidelines...").  

### 7. Utilizing Attested Computations
For mathematical or rule-based calculations (e.g., calculating deadlines, GPA thresholds, or ECTS barriers), the LLM should never perform the arithmetic itself ("hallucinate"). Instead, it uses the OKF `Attested Computation` concept:  
- The agent identifies a concept of type `Attested Computation` (e.g., calculating medical certificate deadlines).  
- Instead of computing inside the text block, the agent passes the required parameters to the specified `executor` (e.g., a Python script or database query).  
- The agent extracts the computed value from the `receipt` and incorporates this mathematically proven value into the email draft. This completely eliminates LLM calculation errors.  

---

## Exemplary Prompt Flow for the Email LLM

When a new email is received (e.g., *"Can I reschedule my exam on August 15th due to illness, and how much time do I have to submit the medical certificate?"*), the answering system should direct the LLM as follows:

1. **Retrieve Phase:**  
   - Search the OKF vector store for keywords like "medical certificate", "exam withdrawal", "illness deadline".  
   - Find the concept `/concepts/exam-withdrawal-illness.md`.  
2. **Evaluate Phase:**  
   - Load the concept and inspect the frontmatter:  
     ```yaml
     status: stable
     stale_after: 2026-12-31
     verified: { by: human:professor-gaida, at: 2026-03-15T09:00:00Z }
     ```
   - *Result:* The document is stable, not stale, and enjoys the highest trust tier (`human-reviewed`).  
3. **Execute Phase (Attestation):**  
   - If a deadline calculation is needed, find the linked `Attested Computation` for certificate deadlines, compute the final submission date based on the exam date (August 15th) via the associated script, and use the exact calculated date.  
4. **Draft Phase:**  
   - Generate the email draft adhering to the defined tone of voice and explicitly citing the source:  
     > "... You must submit the medical certificate without delay, and no later than 3 working days after the exam (i.e., by August 18th). [1] ..."
     >
     > **Sources:**
     > [1] TH Köln Examination Regulations (Section 15 Withdrawal due to Illness), stored in `/documents/examination-guidelines.md`.

---

## Actual Implementation in the MCP University Memory System

In the **MCP University Memory System**, this theoretical model has been fully and enforceably implemented. Once an email is classified as `PAV_PO-Wechsel`, the system guides the LLM using the following concrete functionalities and mechanisms:

### 1. Progressive Disclosure via `OKF_BUNDLE_PATH`
Instead of loading the entire OKF bundle (e.g., under `D:/PAV/okf`) into the LLM's context, the controller passes the bundle's directory path via the `OKF_BUNDLE_PATH` variable in the additional context to the agent.  
- The agent first reads the index overview file `index.md` in the OKF directory using the `read_file(path="<OKF_BUNDLE_PATH>/index.md")` tool.  
- The LLM identifies the relevant concepts and retrieves them in a targeted, incremental manner (multi-hop traversal of Markdown links), e.g., calling `read_file(path="<OKF_BUNDLE_PATH>/concepts/exam-withdrawal-illness.md")`.  

### 2. Mandatory Verification Pipeline via `SKILL_okfv02.md`
The system automatically loads the `SKILL_okfv02.md` skill and appends it to the agent's instructions. When processing any retrieved concept, the agent is strictly required to execute the following 4-step check in its chain of thought:  
1. **Status Check:** Is `status: deprecated` or `draft` set in the frontmatter?  
2. **Freshness Check:** Is the current date before or after `stale_after`?  
3. **Trust Tier Check:** Is the concept `unverified`, `machine-confirmed`, or `human-reviewed` (verifying based on `verified` entries)?  
4. **Source Attribution:** Claims made in the response draft are cited and attribute precisely to original documents listed under the `sources` frontmatter field.  

### 3. Attested Calculations with `execute_okf_computation`
For mathematical or rule-based determinations (such as calculating certificate submission deadlines), the agent is provided with the `execute_okf_computation` tool:  
- **Parameters:** The tool expects `concept_path` (path to the concept file) and input values passed as `parameters`.  
- **Safety Gate:** The tool loads the concept, verifies its status and freshness (`stale_after`), and executes the computation code from the concept deterministically.  
- **Attestation:** The generated `receipt` is validated by a deterministic verifier (Attester). Only upon successful attestation is the result returned. The LLM is strictly prohibited from executing arithmetic by itself.  
