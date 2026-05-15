"""Schnittstelle zum hybriden Suchindex (qmd oder native Qdrant+BM25)."""
import logging
import json
import pickle
import subprocess
import os
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

try:
    from qdrant_client import QdrantClient, models
    from sentence_transformers import SentenceTransformer
    from rank_bm25 import BM25Okapi
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False

logger = logging.getLogger(__name__)

class SearchIndex:
    """Schnittstelle zum Suchindex.

    Nutzt vorrangig das 'qmd' CLI-Tool. Falls nicht vorhanden, wird eine native
    Python-Implementierung als Fallback verwendet.
    """

    def __init__(self, location: str, embedding_model_name: str = "BAAI/bge-m3", store: Any = None):
        """Initialisiert den SearchIndex.

        Args:
            location (str): Pfad zum Speicherort des Index.
            embedding_model_name (str): Name des Embedding-Modells.
            store (MetadataStore, optional): Metadaten-Speicher zur Anreicherung der Ergebnisse.
        """
        self.location = Path(location)
        self.store = store
        self.location.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model_name

        self.use_shell = os.name == 'nt'
        self._qmd_available = self._check_qmd()

        if self._qmd_available:
            logger.info("Using qmd CLI as primary search backend.")
        else:
            logger.warning("qmd CLI not found. Falling back to native Python implementation. Install with: npm install -g @tobilu/qmd")
            if not NATIVE_AVAILABLE:
                logger.error("Native search dependencies missing. Search will be unavailable.")

        # Initialize native components anyway as fallback
        if NATIVE_AVAILABLE:
            self._init_native()

    def _check_qmd(self) -> bool:
        """Prüft, ob das qmd-Tool verfügbar ist."""
        try:
            logger.debug("Checking for qmd CLI availability...")
            result = subprocess.run(["qmd", "--version"],
                           capture_output=True,
                           shell=self.use_shell,
                           check=True,
                           text=True)
            logger.debug(f"qmd version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"qmd check failed: {e}")
            return False

    def _init_native(self) -> None:
        """Initialisiert die native Fallback-Suche."""
        logger.info(f"Initializing native search with model: {self.embedding_model_name}")
        self.client = QdrantClient(path=str(self.location))
        self.collection_name = "university_documents"

        logger.debug(f"Loading SentenceTransformer model: {self.embedding_model_name}")
        self.model = SentenceTransformer(self.embedding_model_name)

        self.bm25_path = self.location / "bm25_index.pkl"
        self.corpus_path = self.location / "corpus.json"

        self._ensure_collection()
        self._load_bm25()

    def _ensure_collection(self) -> None:
        """Stellt sicher, dass die Qdrant-Collection existiert."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            dummy_vector = self.model.encode("dummy")
            vector_size = len(dummy_vector)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )

    def _load_bm25(self) -> None:
        """Loads the BM25 index and corpus."""
        self.corpus = []
        self.bm25 = None
        if self.corpus_path.exists():
            logger.debug(f"Loading corpus from {self.corpus_path}")
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)
            if self.bm25_path.exists():
                logger.debug(f"Loading BM25 index from {self.bm25_path}")
                with open(self.bm25_path, "rb") as f:
                    self.bm25 = pickle.load(f)
            else:
                self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        """Rebuilds the BM25 index from corpus."""
        if not self.corpus:
            return
        logger.info(f"Rebuilding BM25 index for {len(self.corpus)} documents")
        tokenized_corpus = [doc["content"].lower().split() for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        with open(self.bm25_path, "wb") as f:
            pickle.dump(self.bm25, f)

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Fügt ein Dokument zum Index hinzu (Native Implementierung)."""
        if not NATIVE_AVAILABLE:
            return

        logger.debug(f"Adding document to native index: {doc_id}")
        vector = self.model.encode(content).tolist()
        doc_hash = int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (2**63 - 1)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=doc_hash,
                    vector=vector,
                    payload={"doc_id": doc_id, "content": content, **metadata}
                )
            ]
        )

        self.corpus = [doc for doc in self.corpus if doc["doc_id"] != doc_id]
        self.corpus.append({"doc_id": doc_id, "content": content, "metadata": metadata})
        with open(self.corpus_path, "w", encoding="utf-8") as f:
            json.dump(self.corpus, f, ensure_ascii=False, indent=2)
        self._rebuild_bm25()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Führt eine Suche aus, bevorzugt via qmd."""
        logger.info(f"Searching for: '{query}' (top_k={top_k})")

        if self._qmd_available:
            logger.debug("Attempting search via qmd CLI")
            qmd_results = self._search_qmd(query, top_k)
            if qmd_results:
                logger.debug(f"qmd returned {len(qmd_results)} results")
                return qmd_results
            logger.debug("qmd search returned no results, falling back to native")

        if NATIVE_AVAILABLE:
            logger.debug("Executing native search (Qdrant + BM25)")
            return self._search_native(query, top_k)

        logger.error("No search implementation available.")
        return []

    def _enrich_with_summary(self, path: str, default_content: str) -> str:
        """Versucht, den Inhalt durch die gespeicherte Zusammenfassung zu ersetzen."""
        if not self.store:
            return default_content

        try:
            file_data = self.store.get_file(path)
            if file_data:
                # file_data: (id, path, hash, mtime, type, last_indexed, folder_id)
                file_id = file_data[0]
                summary = self.store.get_summary("file", file_id)
                if summary:
                    return summary
        except Exception as e:
            logger.warning(f"Failed to fetch summary for {path}: {e}")

        return default_content

    def _search_qmd(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Sucht mittels qmd CLI."""
        try:
            # Try 'query' (hybrid) first
            logger.debug("Executing 'qmd query'...")
            result = subprocess.run([
                "qmd", "query", query, "--json", "-n", str(top_k)
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode != 0:
                logger.debug(f"'qmd query' failed (rc={result.returncode}), trying 'qmd search'...")
                # Fallback to simple 'search'
                result = subprocess.run([
                    "qmd", "search", query, "--json", "-n", str(top_k)
                ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode == 0:
                stdout = result.stdout
                match = re.search(r'\[\s*\{.*\}\s*\]', stdout, re.DOTALL)
                if match:
                    json_results = json.loads(match.group(0))
                    formatted = []
                    for res in json_results:
                        path = res.get("file", res.get("path", ""))
                        content = res.get("snippet", "")
                        # Immer die Zusammenfassung bevorzugen, falls vorhanden
                        content = self._enrich_with_summary(path, content)

                        formatted.append({
                            "path": path,
                            "content": content,
                            "filename": res.get("title", ""),
                            "score": res.get("score", 0),
                            "metadata": res
                        })
                    return formatted
                else:
                    logger.debug("No JSON array found in qmd output.")
            else:
                logger.debug(f"qmd CLI returned error: {result.stderr}")
        except Exception as e:
            logger.error(f"qmd search failed: {e}")
        return []

    def _search_native(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Sucht mittels nativer Python-Implementierung."""
        logger.debug("Encoding query vector...")
        query_vector = self.model.encode(query).tolist()

        logger.debug("Querying Qdrant...")
        dense_results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k * 2
        ).points

        results_map = {}
        for res in dense_results:
            path = res.payload["doc_id"]
            content = self._enrich_with_summary(path, res.payload["content"])
            results_map[path] = {
                "path": path,
                "content": content,
                "filename": res.payload.get("filename", ""),
                "score": res.score,
                "metadata": res.payload
            }

        if self.bm25:
            logger.debug("Executing BM25 scoring...")
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_n = np.argsort(scores)[::-1][:top_k * 2]
            for idx in top_n:
                if scores[idx] > 0:
                    doc = self.corpus[idx]
                    path = doc["doc_id"]
                    if path in results_map:
                        results_map[path]["score"] += float(scores[idx]) * 0.1
                    else:
                        content = self._enrich_with_summary(path, doc["content"])
                        results_map[path] = {
                            "path": path,
                            "content": content,
                            "score": float(scores[idx]),
                            "metadata": doc["metadata"],
                            "filename": doc["metadata"].get("filename", "")
                        }

        sorted_results = sorted(results_map.values(), key=lambda x: x["score"], reverse=True)
        logger.debug(f"Native search found {len(sorted_results)} candidates.")
        return sorted_results[:top_k]
