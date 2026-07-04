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

## Advantages of this Approach  
- **Precision:** Generating specific questions reduces the noise that could arise from a search with the raw email text.  
- **Recency:** The system always accesses the current state of the documents indexed in the `memory` folder.  
- **Transparency:** In the debug logs and prompts, it is exactly traceable which information was used as context.  

---
See also:

- [Email Classification](../packages/email-classifier/index.md)
- [Document Indexing](indexing-details.md)  
- [Configuration](../configuration.md)  
