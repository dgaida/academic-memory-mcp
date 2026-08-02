# RAG Process (Retrieval Augmented Generation)

To professionally classify and contextually answer emails, the system uses a multi-stage RAG process. This process ensures that the LLM has access to specific knowledge (such as examination regulations or module descriptions) stored in the vector databases of the respective email classes.

## Process Flow

The process in `EmailController` follows three main steps:

### 1. Search Query Generation
Instead of using the entire email text directly for the search, the system first has the LLM generate **3 precise search queries (questions)**.

- The LLM analyzes the incoming email.  
- It formulates questions aimed at extracting the necessary information to answer the request from a knowledge base.  

### 2. Vector Search (Retrieval)
The generated questions are used to search for relevant text sections (chunks) in the vector database of the associated email class (e.g., `Bachelor_Thesis` or `PAV`).

- For each of the 3 questions, the most relevant results are retrieved.  
- The system uses the `SearchIndex` for this, which is based on the embedded documents in the folder `data/memory/<Class>`.  

### 3. Context Injection (Augmentation)
The found information is filtered and prepared:

- The **Top 3 unique chunks** are selected (based on their similarity score).  
- These chunks are inserted as "Additional Context" into the prompt for action classification (Phase 3) as well as the final response generation (Phase 6).  

## Automated Web Sources Integration (Web Crawling & Caching)

For specific email classes (e.g., `BA_DL_ML_KI`), an automated web source is configured (defined in `config/web_sources.yaml`). When the LLM answers an email of this class, the `WebCrawlerManager` retrieves relevant information from the configured website (and the PDFs provided there).

### How it Works  
1. **Caching & Offline-First:** The system crawls the target page (e.g., `https://dgaida.github.io/wpf_dlml_th_public/`) and all linked PDFs (using `crawl4ai` with a robust fallback to `requests` + `BeautifulSoup` + `pdfminer`). The crawled contents are cached locally in `data/cache/web_sources/<Class>/cache.json`.  
2. **Offline Mode:** If there is no internet connection or crawling fails, the local cache is loaded directly.  
3. **Keyword & BM25 Search:** The `WebCrawlerManager` splits the crawled text and PDF content into paragraphs and searches using BM25 for sections helpful for answering the email. These are provided to the LLM as additional context, citing the website and PDFs as sources.  

## Advantages of this Approach  
- **Precision:** Generating specific questions reduces the noise that could arise from a search with the raw email text.  
- **Recency:** The system always accesses the current state of the documents indexed in the `memory` folder.  
- **Transparency:** In the debug logs and prompts, it is exactly traceable which information was used as context.  

---
See also:

- [Email Classification](../packages/email-classifier/index.md)  
- [Document Indexing](indexing-details.md)  
- [Configuration](../configuration.md)  
