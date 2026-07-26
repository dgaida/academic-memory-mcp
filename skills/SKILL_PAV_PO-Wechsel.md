# SKILL: PAV_PO-Wechsel

This skill describes how to handle and answer student inquiries regarding changes to the Examination Regulations (Prüfungsordnung-Wechsel / PO-Wechsel).

## Knowledge Base: Open Knowledge Format (OKF)

To answer student inquiries accurately, the system MUST utilize the Open Knowledge Format (OKF) bundle specified for the `PAV_PO-Wechsel` class in `config/classifier_memory_paths.yaml`.

For example, if the path is configured as:
```yaml
class_paths:
  PAV_PO-Wechsel: "D:/PAV/okf"
```
The system will load and search the OKF knowledge bundle located at `D:/PAV/okf`.

### OKF v0.2 Structure and Usage

Following the Google Cloud Platform OKF v0.2 specification, the knowledge bundle is structured to organize unstructured regulation documents into structured, provenance-aware knowledge files:
1. **`index.md`**: Provides the entry point and navigation overview, containing `okf_version: "0.2"`.
2. **`documents/`**: Contains the source Markdown files generated from original PDFs (e.g., `examination-guidelines.md`). Use this directory to trace information back to original sections (provenance / source tracing).
3. **`concepts/`**: Holds abstract topics and process concepts (e.g., hardship cases, credit transfer, or transition rules).
4. **`entities/`**: Represents concrete identifiable objects or regulations (e.g., `examination-board.md`, `th-koeln.md`).
5. **`definitions/`**: Explains explicit terminology and definitions.
6. **`tables/`**: Houses structured comparisons, credit equivalencies, or transition schedules.

Whenever answering student emails, ensure that terms or decisions are grounded in the specific concepts, entities, definitions, or tables, verifying them against the original sources under `/documents/...` for strict alignment and truthfulness.

### Original Source Documents (Memory Folder)

Parallel to each `okf` folder, there is a `Memory` folder containing the original source PDF documents.
- Example: If the OKF folder is at `D:/PAV/okf`, the `Memory` folder is located at `D:/PAV/Memory`.
- The `Memory` folder can contain arbitrary subfolders for organizing files.

---

## Instructions for Email Responses

1. **Information Retrieval:**
   - Always query the OKF database using the retrieved context or direct vector search matching the student's questions.
   - Cross-reference retrieved artifacts with the original documents inside `/documents/` to trace exact sections and verify correctness.

2. **Härtefall (Hardship Cases):**
   - For queries concerning hardship cases or detailed process workflows, consult the specialized PDF `InfosPOWechselHärtefall.pdf`.
   - Ground specific answers regarding hardships or process requests on the contents of this PDF.
   - The PDF lies at the relative path `PO-Wechsel/InfosPOWechselHärtefall.pdf`, where this relative path has the folder `Memory` as its base path (e.g. `D:/PAV/Memory/PO-Wechsel/InfosPOWechselHärtefall.pdf`).

3. **Email Attachments:**
   - If the information in `InfosPOWechselHärtefall.pdf` is relevant to the student's inquiry, the PDF can/must be attached to the reply email.
   - In your response plan/metadata, indicate that `InfosPOWechselHärtefall.pdf` is to be included as an email attachment.
