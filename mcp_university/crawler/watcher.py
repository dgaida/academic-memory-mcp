"""Watcher module."""
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .crawler import Crawler

logger = logging.getLogger(__name__)

class IndexingHandler(FileSystemEventHandler):
    """Handler for indexing."""
    def __init__(self, crawler: Crawler):
        """Init."""
        self.crawler = crawler

    def on_modified(self, event) -> None:
        """Modified."""
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() in self.crawler.config.folders.supported_extensions:
                logger.info(f"File modified: {path}")
                self.crawler._process_file(path, 0)

    def on_created(self, event) -> None:
        """Created."""
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() in self.crawler.config.folders.supported_extensions:
                logger.info(f"File created: {path}")
                self.crawler._process_file(path, 0)

class Watcher:
    """Watcher class."""
    def __init__(self, crawler: Crawler):
        """Init."""
        self.crawler = crawler
        self.observer = Observer()

    def start(self) -> None:
        """Start."""
        handler = IndexingHandler(self.crawler)
        for folder in self.crawler.config.folders.folders:
            path = Path(folder)
            if path.exists():
                self.observer.schedule(handler, str(path), recursive=True)

        self.observer.start()
        logger.info("Watcher started.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
