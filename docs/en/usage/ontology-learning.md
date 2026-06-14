# Ontology & Alias Learning

The system has mechanisms to automatically learn variations of names (aliases) and consolidate them in the knowledge graph.

## Alias Table
The `MetadataStore` includes an `aliases` table that maps various names to a canonical (unified) name. This prevents duplicates in the knowledge graph (e.g., "AI" and "Artificial Intelligence" as two separate nodes).

## Ontology Learner
The `mcp_university/knowledge_graph/ontology_learner.py` module automates this process:

1.  **Email Header Analysis:** It extracts name-email pairs from the headers of processed emails. This helps to uniquely identify persons, even if they use different display names.
2.  **LLM-based Consolidation:** Existing nodes in the knowledge graph are analyzed by an LLM to find semantic variations (e.g., module abbreviations).
3.  **Canonization:** Before a new node is inserted into the knowledge graph, the system checks if a canonical alias exists for that name and uses it preferentially.

## Edge Priorities
In `ontology.yaml`, priorities can be defined for different relationship types. When the `KnowledgeGraphEngine` finds a new relationship between two nodes that are already linked, the priority decides whether the old relationship is replaced. This ensures that higher-quality information (e.g., from MOCOGI) overwrites less precise information (e.g., from an email extraction).
