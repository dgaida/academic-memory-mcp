"""Kommandozeilen-Schnittstelle (CLI) für das MCP University System."""
import typer
import logging
from ..crawler.crawler import Crawler
from ..config import get_config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..retrieval.index import SearchIndex
from ..mcp_server.server import create_server

app = typer.Typer(help="MCP University Memory System CLI")

def setup_logging(debug: bool):
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@app.command()
def index(debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging")) -> None:
    """Startet den vollständigen Indexierungsprozess aller konfigurierten Ordner."""
    setup_logging(debug)
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)

    crawler = Crawler(cfg, store, parser, summarizer, idx)
    crawler.crawl()

@app.command()
def search(
    query: str,
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging")
) -> None:
    """Führt eine hybride Suche über die indexierten Dokumente aus.

    Args:
        query: Der Suchbegriff oder die Frage.
    """
    setup_logging(debug)
    cfg = get_config()
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    results = idx.search(query)
    for res in results:
        print(f"[{res['score']:.2f}] {res['filename']} ({res['path']})")
        print(f"  {res['content']}\n")

@app.command()
def watch(debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging")) -> None:
    """Startet den Watchdog zur Echtzeit-Überwachung von Ordnern."""
    setup_logging(debug)
    from ..crawler.watcher import Watcher
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)

    crawler = Crawler(cfg, store, parser, summarizer, idx)
    watcher = Watcher(crawler)
    watcher.start()

@app.command()
def serve_mcp(debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging")) -> None:
    """Startet den FastMCP-Server zur Integration in KI-Agenten."""
    setup_logging(debug)
    server = create_server()
    server.run()

if __name__ == "__main__":
    app()
