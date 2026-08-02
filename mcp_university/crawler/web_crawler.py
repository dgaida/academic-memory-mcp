"""Modul für das automatisierte Crawling und Caching von Webseiten und PDFs."""

from typing import Dict, List, Any, Optional, Set
import os
import logging
import asyncio
import json
import re
import threading
from datetime import datetime
from pathlib import Path
import urllib.parse
import yaml
import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as extract_pdf_text
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Lazy import for crawl4ai to prevent startup crashes if dependency issues arise
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai is not installed or available. Using fallback requests crawler.")


def run_async_in_thread(coro) -> Any:
    """Führt eine asynchrone Coroutine in einem separaten Thread mit eigener Event-Loop aus.

    Verhindert Konflikte mit bereits laufenden Event-Loops (z.B. in FastAPI/Gradio)
    und vermeidet Deadlocks.

    Args:
        coro: Die asynchrone Coroutine.

    Returns:
        Any: Das Ergebnis der Coroutine.
    """
    result = None
    exception = None

    def target():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            try:
                loop.close()
            except Exception:
                pass

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result


class WebCrawlerManager:
    """Verwaltet das automatisierte Crawling von Webseiten und PDFs für E-Mail-Klassen.

    Nutzt crawl4ai und bietet ein robustes Fallback-System auf Basis von
    requests und BeautifulSoup, falls crawl4ai fehlschlägt oder offline gearbeitet wird.
    """

    def __init__(self, config_path: str = "config/web_sources.yaml", cache_base_dir: Optional[Path] = None) -> None:
        """Initialisiert den WebCrawlerManager.

        Args:
            config_path (str): Pfad zur Konfigurationsdatei der Web-Quellen.
            cache_base_dir (Path, optional): Basisverzeichnis für den Cache.
        """
        self.config_path = Path(config_path)
        self.cache_base_dir = cache_base_dir or Path("data/cache/web_sources")
        self.sources: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Lädt die Konfigurationsdatei, falls diese existiert."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.sources = yaml.safe_load(f) or {}
                logger.debug(f"Web sources configuration loaded: {self.sources}")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Web-Quellen-Konfiguration: {e}")
        else:
            logger.warning(f"Konfigurationsdatei {self.config_path} nicht gefunden.")

    def is_configured(self, class_name: str) -> bool:
        """Prüft, ob eine E-Mail-Klasse in den Web-Quellen konfiguriert ist.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.

        Returns:
            bool: True, wenn konfiguriert, andernfalls False.
        """
        return class_name in self.sources

    def get_url(self, class_name: str) -> Optional[str]:
        """Gibt die konfigurierte URL für eine E-Mail-Klasse zurück.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.

        Returns:
            Optional[str]: Die URL oder None, wenn nicht konfiguriert.
        """
        source = self.sources.get(class_name)
        if source and isinstance(source, dict):
            return source.get("url")
        return None

    def _get_cache_path(self, class_name: str) -> Path:
        """Gibt den Pfad zur Cache-Datei für eine E-Mail-Klasse zurück.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.

        Returns:
            Path: Der Pfad zur Cache-Datei.
        """
        return self.cache_base_dir / class_name / "cache.json"

    def has_cache(self, class_name: str) -> bool:
        """Prüft, ob ein Cache für die E-Mail-Klasse existiert.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.

        Returns:
            bool: True, wenn der Cache existiert, andernfalls False.
        """
        cache_file = self._get_cache_path(class_name)
        return cache_file.exists()

    def load_cache(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Lädt den Cache für eine E-Mail-Klasse.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.

        Returns:
            Optional[Dict[str, Any]]: Die Cache-Daten oder None bei Fehlern oder fehlendem Cache.
        """
        cache_file = self._get_cache_path(class_name)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fehler beim Laden des Cache für {class_name}: {e}")
            return None

    def save_cache(self, class_name: str, data: Dict[str, Any]) -> None:
        """Speichert die Cache-Daten für eine E-Mail-Klasse.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.
            data (Dict[str, Any]): Die zu speichernden Cache-Daten.
        """
        cache_file = self._get_cache_path(class_name)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cache für Klasse {class_name} erfolgreich unter {cache_file} gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Cache für {class_name}: {e}")

    async def _crawl_url_crawl4ai(self, url: str) -> str:
        """Versucht eine URL mit crawl4ai zu crawlen.

        Args:
            url (str): Die zu crawlende URL.

        Returns:
            str: Der gecrawlte Text oder Markdown.
        """
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai is not available.")

        logger.info(f"Crawl4AI: Crawle {url}...")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result.success:
                return result.markdown or result.extracted_content or result.html or ""
            else:
                raise RuntimeError(f"Crawl4AI failed for URL {url}: {result.error_message}")

    def _crawl_url_fallback(self, url: str) -> str:
        """Fällt auf requests und BeautifulSoup zurück, um eine URL zu crawlen.

        Args:
            url (str): Die zu crawlende URL.

        Returns:
            str: Der extrahierte Text der Webseite.
        """
        logger.info(f"Fallback-Crawler: Lade {url}...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        # Bestimme Encoding falls nicht korrekt erkannt
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(response.text, "html.parser")

        # Entferne Scripts, Styles und unwichtige Elemente
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()

        return soup.get_text(separator="\n")

    def _extract_text_from_pdf(self, pdf_url: str, class_name: str) -> str:
        """Lädt eine PDF-Datei herunter und extrahiert den Text.

        Args:
            pdf_url (str): Die URL zur PDF-Datei.
            class_name (str): Der Name der E-Mail-Klasse für temporäre Speicherung.

        Returns:
            str: Der extrahierte PDF-Text.
        """
        logger.info(f"Lade PDF herunter: {pdf_url}")
        temp_dir = self.cache_base_dir / class_name / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Sicheren Dateinamen generieren
        safe_filename = re.sub(r"[^a-zA-Z0-9_\.-]", "_", Path(urllib.parse.urlparse(pdf_url).path).name)
        if not safe_filename:
            safe_filename = "downloaded_document.pdf"

        temp_path = temp_dir / safe_filename

        try:
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            temp_path.write_bytes(response.content)

            # Text extrahieren
            text = extract_pdf_text(str(temp_path))
            return text or ""
        except Exception as e:
            logger.error(f"Fehler beim Herunterladen oder Parsen der PDF {pdf_url}: {e}")
            return ""
        finally:
            # Temporäre Datei löschen
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def crawl_and_cache(self, class_name: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """Crawlt die konfigurierte Webseite und alle gefundenen PDFs und speichert sie im Cache.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.
            force (bool): Wenn True, wird das Crawling erzwungen, selbst wenn ein Cache existiert.

        Returns:
            Optional[Dict[str, Any]]: Die neu generierten Cache-Daten oder None bei Fehlern.
        """
        if not self.is_configured(class_name):
            logger.error(f"Klasse {class_name} ist nicht für Web-Quellen konfiguriert.")
            return None

        if self.has_cache(class_name) and not force:
            logger.info(f"Cache für Klasse {class_name} existiert bereits. Überspringe Crawling.")
            return self.load_cache(class_name)

        root_url = self.get_url(class_name)
        if not root_url:
            logger.error(f"Keine URL für E-Mail-Klasse {class_name} hinterlegt.")
            return None

        parsed_root = urllib.parse.urlparse(root_url)
        root_domain = parsed_root.netloc
        root_path = parsed_root.path

        # 1. Hauptseite crawlen
        main_content = ""
        used_crawl4ai = False
        try:
            if CRAWL4AI_AVAILABLE:
                # Führe asynchrones Crawling sicher in einem separaten Thread aus,
                # um Konflikte mit laufenden Loops zu vermeiden.
                main_content = run_async_in_thread(self._crawl_url_crawl4ai(root_url))
                used_crawl4ai = True
            else:
                raise ImportError("Crawl4AI not installed.")
        except Exception as e:
            logger.warning(f"Crawl4AI fehlgeschlagen oder nicht verfügbar für {root_url}: {e}. Nutze Fallback.")
            try:
                main_content = self._crawl_url_fallback(root_url)
            except Exception as fe:
                logger.error(f"Fallback-Crawler ebenfalls fehlgeschlagen für {root_url}: {fe}")
                return None

        # 2. Links extrahieren aus der Hauptseite
        try:
            response = requests.get(root_url, timeout=15)
            # Bestimme Encoding falls nicht korrekt erkannt
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Seite zwecks Link-Extraktion: {e}")
            soup = BeautifulSoup("", "html.parser")

        links_to_crawl: Set[str] = set()
        pdf_links: Set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urllib.parse.urljoin(root_url, href)
            parsed_url = urllib.parse.urlparse(absolute_url)

            # Nur Links auf der gleichen Domain und im gleichen Verzeichnisbaum crawlen
            if parsed_url.netloc == root_domain and parsed_url.path.startswith(root_path):
                # Anker entfernen
                clean_url = urllib.parse.urlunparse(parsed_url._replace(fragment=""))
                if clean_url.lower().endswith(".pdf"):
                    pdf_links.add(clean_url)
                elif clean_url != root_url:
                    links_to_crawl.add(clean_url)

        # Begrenze die Anzahl der Unterseiten, um Overheads zu vermeiden
        subpages_list = sorted(list(links_to_crawl))[:10]
        pdfs_list = sorted(list(pdf_links))[:15]

        pages_data: List[Dict[str, str]] = [
            {
                "url": root_url,
                "title": "Hauptseite",
                "content": main_content
            }
        ]

        # 3. Unterseiten crawlen
        for sub_url in subpages_list:
            sub_content = ""
            try:
                if used_crawl4ai:
                    sub_content = run_async_in_thread(self._crawl_url_crawl4ai(sub_url))
                else:
                    sub_content = self._crawl_url_fallback(sub_url)

                pages_data.append({
                    "url": sub_url,
                    "title": Path(urllib.parse.urlparse(sub_url).path).name or "Unterseite",
                    "content": sub_content
                })
            except Exception as e:
                logger.warning(f"Fehler beim Crawlen der Unterseite {sub_url}: {e}. Versuche Fallback.")
                try:
                    sub_content = self._crawl_url_fallback(sub_url)
                    pages_data.append({
                        "url": sub_url,
                        "title": Path(urllib.parse.urlparse(sub_url).path).name or "Unterseite",
                        "content": sub_content
                    })
                except Exception as fe:
                    logger.error(f"Crawl fehlgeschlagen für Unterseite {sub_url}: {fe}")

        # 4. PDFs herunterladen und extrahieren
        pdfs_data: List[Dict[str, str]] = []
        for pdf_url in pdfs_list:
            try:
                pdf_text = self._extract_text_from_pdf(pdf_url, class_name)
                if pdf_text:
                    pdfs_data.append({
                        "url": pdf_url,
                        "filename": Path(urllib.parse.urlparse(pdf_url).path).name,
                        "content": pdf_text
                    })
            except Exception as e:
                logger.error(f"Fehler bei PDF-Verarbeitung {pdf_url}: {e}")

        # 5. Cache-Daten zusammenstellen (Standard-Datetime für absolute Sicherheit vor Event-Loop Crashs)
        cache_data = {
            "class_name": class_name,
            "root_url": root_url,
            "crawl_time": datetime.utcnow().isoformat(),
            "pages": pages_data,
            "pdfs": pdfs_data
        }

        self.save_cache(class_name, cache_data)
        return cache_data

    def get_relevant_context(self, class_name: str, email_content: str, max_results: int = 5) -> str:
        """Sucht im Cache nach relevanten Textstellen basierend auf der E-Mail.

        Wird offline verwendet, falls keine Internetverbindung vorhanden ist, oder standardmäßig
        als effiziente Retrieval-Methode.

        Args:
            class_name (str): Der Name der E-Mail-Klasse.
            email_content (str): Der Inhalt der eingehenden E-Mail.
            max_results (int): Maximale Anzahl an Textabschnitten.

        Returns:
            str: Eine formatierte Markdown-Zeichenkette mit dem relevanten Kontext.
        """
        cache_data = self.load_cache(class_name)

        # Falls kein Cache vorhanden, versuchen wir online zu crawlen
        if not cache_data:
            logger.info(f"Kein Cache für {class_name} gefunden. Starte On-Demand-Crawling...")
            try:
                cache_data = self.crawl_and_cache(class_name)
            except Exception as e:
                logger.error(f"On-Demand-Crawling fehlgeschlagen: {e}")

        if not cache_data:
            return ""

        root_url = cache_data.get("root_url", "")
        chunks: List[Dict[str, Any]] = []

        # Chunks aus Webseiten extrahieren
        for page in cache_data.get("pages", []):
            url = page.get("url", "")
            content = page.get("content", "")
            # Text in Absätze splitten
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
            for p in paragraphs:
                if len(p) > 50:  # Mindestgröße für Relevanz
                    chunks.append({
                        "source_type": "Webseite",
                        "source_name": page.get("title", "Webseite"),
                        "source_url": url,
                        "text": p
                    })

        # Chunks aus PDFs extrahieren
        for pdf in cache_data.get("pdfs", []):
            url = pdf.get("url", "")
            content = pdf.get("content", "")
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
            for p in paragraphs:
                if len(p) > 50:
                    chunks.append({
                        "source_type": "PDF-Dokument",
                        "source_name": pdf.get("filename", "PDF-Datei"),
                        "source_url": url,
                        "text": p
                    })

        if not chunks:
            return ""

        # BM25-Suche initialisieren
        def tokenize(text: str) -> List[str]:
            return [w.lower() for w in re.findall(r"\b\w+\b", text) if len(w) > 1]

        tokenized_corpus = [tokenize(c["text"]) for c in chunks]
        query_tokens = tokenize(email_content)

        if not query_tokens:
            # Fallback: Die ersten Abschnitte zurückgeben
            top_chunks = chunks[:max_results]
        else:
            try:
                bm25 = BM25Okapi(tokenized_corpus)
                scores = bm25.get_scores(query_tokens)
                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:max_results]

                # Nur Chunks mit Score > 0 nehmen, außer wir haben gar keine Treffer
                top_chunks = []
                for idx in top_indices:
                    if scores[idx] > 0.0 or not top_chunks:
                        top_chunks.append(chunks[idx])
            except Exception as e:
                logger.error(f"Fehler bei BM25-Suche im Webcrawler-Cache: {e}")
                top_chunks = chunks[:max_results]

        # Markdown-Kontext erstellen
        context_str = f"\n\n--- OFFLINE WEB-QUELLE: {root_url} ---\n"
        context_str += "Die folgenden Abschnitte wurden aus der offiziellen Webseite und den bereitgestellten PDFs gecrawlt:\n\n"

        for c in top_chunks:
            context_str += f"**Quelle:** {c['source_type']} - *{c['source_name']}* ({c['source_url']})\n"
            context_str += f"> {c['text']}\n\n"

        context_str += "-------------------------------------------------\n"
        return context_str
