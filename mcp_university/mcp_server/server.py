"""MCP Server für den Zugriff auf Universitätsdaten."""
import logging
from fastmcp import FastMCP
from ..config import get_config
from ..metadata.store import MetadataStore
from ..metadata.kg_store import KnowledgeGraphStore
from ..retrieval.index import SearchIndex
from ..summarizer.engine import Summarizer

logger = logging.getLogger(__name__)

def create_server() -> FastMCP:
    """Erstellt den FastMCP Server.

    Returns:
        FastMCP: Die Server-Instanz.
    """
    cfg = get_config()
    mcp = FastMCP("University Memory")
    # Haupt-Metadatenstore (für studentische Verbindungen)
    store = MetadataStore(cfg.metadata_db_path)
    # TH Köln Wissensgraph
    kg_store = KnowledgeGraphStore(cfg.kg_db_path)

    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)

    @mcp.tool()
    def search_documents(query: str, top_k: int = 5) -> str:
        """Sucht in indexierten Dokumenten."""
        results = idx.search(query, top_k=top_k)
        if not results:
            return "Keine Dokumente gefunden."
        return "\n\n".join([f"Datei: {r['path']}\nInhalt: {r['content']}" for r in results])

    @mcp.tool()
    def get_student_info(name: str) -> str:
        """Holt Infos über einen Studenten."""
        students = store.get_all_students()
        for s in students:
            if name.lower() in s['name'].lower():
                return str(s)
        return "Student nicht gefunden."

    @mcp.tool()
    def get_th_koeln_info(name: str) -> str:
        """Sucht im TH Köln Wissensgraph nach Personen oder Modulen."""
        node = kg_store.get_node_by_property("name", name)
        if not node:
            # Fallback: Suche in Aliasen
            canonical = kg_store.resolve_canonical_name(name, "Person")
            node = kg_store.get_node_by_property("name", canonical)

        if node:
            return str(node)
        return "Keine TH Köln Information gefunden."

    @mcp.tool()
    def get_folder_summary(path: str) -> str:
        """Holt die Zusammenfassung eines Ordners."""
        folders = store.get_all_folders()
        folder_id = next((f['id'] for f in folders if path in f['path']), None)
        if folder_id:
            summary = store.get_summary("folder", folder_id)
            return summary or "Keine Zusammenfassung gefunden."
        return "Ordner nicht gefunden."

    @mcp.tool()
    def get_student_context(email: str) -> str:
        """Holt den Wissensgraph-Kontext eines Studenten."""
        node = store.get_node_by_property("email", email)
        if node:
            return str(store.get_outgoing_edges(node['id']))
        return "Kein Kontext gefunden."

    return mcp
