# Troubleshooting

Find solutions for common issues here.

## Ollama Connection Failed

**Symptom:** Error message during indexing or search regarding the connection to the LLM.
**Solution:**  
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`  
2. Ensure the model is pulled: `ollama pull gemma4:e2b`  
3. Check the `base_url` in `config/models.yaml`.  

## PDF Parsing Errors

**Symptom:** PDFs are skipped or contain no text.
**Solution:**  
1. Docling needs internet access during the first start to download models.  
2. Check if the PDF is read-only or corrupted.  
3. Reinstall Docling: `pip install --upgrade "docling"`.  

## Search Returns No Results

**Symptom:** Search is empty even though documents are present.
**Solution:**  
1. Run `mcp-uni index` again.  
2. Check if `search index` is available in the system path.  
3. Verify the paths in `config/folders.yaml`.  

## SQLite Database Locked

**Symptom:** `sqlite3.OperationalError: database is locked`
**Solution:**
This happens when multiple processes try to write to the database simultaneously. Terminate all instances of `mcp-uni watch` or `serve-mcp` and try again.

## Missing Metrics in Dashboard

**Symptom:** The `metrics.md` page shows no data.
**Solution:**
Metrics are generated during the CI run. Locally, you need to run the metrics script manually (see Developer Guide).

## Missing Path Configuration for Email Classes

**Symptom:** A warning in the log like:
`2026-07-14 10:30:22,637 - WARNING - Keine Pfad-Konfiguration für 'XY' gefunden. Überspringe 20250826_093612 - Mail.msg`

**Meaning:**
The email classifier classified an email into the class `'XY'` (e.g., `BachelorThesis`, `MasterThesis`, `Other` etc.). However, in the configuration file (e.g., `config/folders.yaml` or `config/classifier_paths.yaml`), under `class_paths`, there is no mapping to a destination folder for class `'XY'`. As a result, the corresponding email file is skipped and not sorted.

**Solution:**  
1. **Configure destination folder:** Open the configuration file (by default `config/folders.yaml` or the configuration file specified in your command like `config/classifier_paths.yaml`) and check the `class_paths` section.  
2. **Add the class:** Add the missing entry for class `'XY'`. For example:  
   ```yaml
   class_paths:
     # ... other classes ...
     XY: "D:/path/to/XY"
   ```
3. **Verify classification:** If the email was incorrectly classified as class `'XY'`, check the training data of the classifier or correct the classification in the manual step (e.g., via the Gradio web interface).  
4. **Re-run the script:** Start the email sorting script again to process the skipped emails.  
