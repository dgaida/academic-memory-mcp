# Troubleshooting

Find solutions for common issues here.

## Ollama Connection Failed

**Symptom:** Error message during indexing or search regarding the connection to the LLM.
**Solution:**  
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`  
2. Ensure the model is pulled: `ollama pull gemma2:2b`  
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
