"""Kommandozeilen-Schnittstelle (CLI) für das MCP University System."""
import typer
from .crawler.crawler import Crawler
from .config import get_config
from .metadata.store import MetadataStore
from .parser.factory import ParserFactory
from .summarizer.engine import Summarizer
from .retrieval.index import SearchIndex
from .mcp_server.server import create_server

app = typer.Typer(help="MCP University Memory System CLI")

@app.command()
def index() -> None:
    """Startet den vollständigen Indexierungsprozess aller konfigurierten Ordner."""
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)

    crawler = Crawler(cfg, store, parser, summarizer, idx)
    crawler.crawl()

@app.command()
def search(query: str) -> None:
    """Führt eine hybride Suche über die indexierten Dokumente aus.

    Args:
        query: Der Suchbegriff oder die Frage.
    """
    cfg = get_config()
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    results = idx.search(query)
    for res in results:
        print(f"[{res['score']:.2f}] {res['filename']} ({res['path']})")
        print(f"  {res['content']}\n")

@app.command()
def watch() -> None:
    """Startet den Watchdog zur Echtzeit-Überwachung von Ordnern."""
    from .crawler.watcher import Watcher
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)

    crawler = Crawler(cfg, store, parser, summarizer, idx)
    watcher = Watcher(crawler)
    watcher.start()

@app.command()
def serve_mcp() -> None:
    """Startet den FastMCP-Server zur Integration in KI-Agenten."""
    server = create_server()
    server.run()

if __name__ == "__main__":
    app()
