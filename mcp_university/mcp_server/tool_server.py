"""Zusätzlicher Tool-Server für Datenbank-Operationen."""
import logging
from fastmcp import FastMCP
from ..config import get_config
from ..metadata.store import MetadataStore
from ..metadata.kg_store import KnowledgeGraphStore

logger = logging.getLogger(__name__)

def create_tool_server() -> FastMCP:
    """Erstellt den Tool-Server.

    Returns:
        FastMCP: Server-Instanz.
    """
    cfg = get_config()
    mcp = FastMCP("University Tools")
    store = MetadataStore(cfg.metadata_db_path)
    kg_store = KnowledgeGraphStore(cfg.kg_db_path)

    @mcp.tool()
    def list_nodes(graph_type: str = "student") -> str:
        """Listet Knoten auf. graph_type: 'student' (metadata.db) oder 'th_koeln' (knowledge_graph.db)."""
        target_store = store if graph_type == "student" else kg_store
        nodes = target_store.get_all_nodes()
        return str(nodes)

    return mcp
