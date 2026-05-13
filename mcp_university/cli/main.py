import typer
import logging
from pathlib import Path
from ..config import get_config
from ..metadata.store import MetadataStore
from ..retrieval.index import SearchIndex
from ..summarizer.engine import Summarizer
from ..parser.factory import ParserFactory
from ..crawler.crawler import Crawler
from ..crawler.watcher import Watcher
from ..mcp_server.server import create_server

app = typer.Typer()
logging.basicConfig(level=logging.INFO)

@app.command()
def index():
    """Crawl and index all configured folders."""
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    parser = ParserFactory(cfg.data_dir / "cache")

    crawler = Crawler(cfg, store, parser, summarizer, index)
    typer.echo("Starting crawl...")
    crawler.crawl()
    typer.echo("Crawl complete.")

@app.command()
def search(query: str):
    """Search for documents."""
    cfg = get_config()
    index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    results = index.search(query)
    for res in results:
        typer.echo(f"--- {res.get('filename', 'Unknown')} ---")
        typer.echo(res.get('content', '')[:300] + "...")
        typer.echo(f"Path: {res.get('path', '')}")

@app.command()
def watch():
    """Watch for file changes and update index."""
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    parser = ParserFactory(cfg.data_dir / "cache")

    crawler = Crawler(cfg, store, parser, summarizer, index)
    watcher = Watcher(crawler)
    typer.echo("Starting watcher...")
    watcher.start()

@app.command()
def serve_mcp():
    """Start the MCP server."""
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    app()
