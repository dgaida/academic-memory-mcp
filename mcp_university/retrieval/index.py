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

    def __init__(self, location: str, embedding_model_name: str = "BAAI/bge-m3"):
        """Initialisiert den SearchIndex.

        Args:
            location (str): Pfad zum Speicherort des Index.
            embedding_model_name (str): Name des Embedding-Modells.
        """
        self.location = Path(location)
        self.location.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model_name

        self.use_shell = os.name == 'nt'
        self._qmd_available = self._check_qmd()

        if not self._qmd_available:
            logger.warning("qmd CLI not found. Falling back to native Python implementation. Install with: npm install -g @tobilu/qmd")
            if not NATIVE_AVAILABLE:
                logger.error("Native search dependencies missing. Search will be unavailable.")

        # Initialize native components anyway as fallback
        if NATIVE_AVAILABLE:
            self._init_native()

    def _check_qmd(self) -> bool:
        """Prüft, ob das qmd-Tool verfügbar ist."""
        try:
            subprocess.run(["qmd", "--version"],
                           capture_output=True,
                           shell=self.use_shell,
                           check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _init_native(self) -> None:
        """Initialisiert die native Fallback-Suche."""
        self.client = QdrantClient(path=str(self.location))
        self.collection_name = "university_documents"
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
        self.corpus = []
        self.bm25 = None
        if self.corpus_path.exists():
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)
            if self.bm25_path.exists():
                with open(self.bm25_path, "rb") as f:
                    self.bm25 = pickle.load(f)
            else:
                self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        if not self.corpus:
            return
        tokenized_corpus = [doc["content"].lower().split() for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        with open(self.bm25_path, "wb") as f:
            pickle.dump(self.bm25, f)

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Fügt ein Dokument zum Index hinzu (Native Implementierung)."""
        if not NATIVE_AVAILABLE:
            return

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
        if self._qmd_available:
            qmd_results = self._search_qmd(query, top_k)
            if qmd_results:
                return qmd_results

        if NATIVE_AVAILABLE:
            return self._search_native(query, top_k)

        return []

    def _search_qmd(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Sucht mittels qmd CLI."""
        try:
            # Try 'query' (hybrid) first
            result = subprocess.run([
                "qmd", "query", query, "--json", "-n", str(top_k)
            ], capture_output=True, text=True, shell=self.use_shell)

            if result.returncode != 0:
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
                        formatted.append({
                            "path": res.get("file", res.get("path", "")),
                            "content": res.get("snippet", ""),
                            "filename": res.get("title", ""),
                            "score": res.get("score", 0),
                            "metadata": res
                        })
                    return formatted
        except Exception as e:
            logger.error(f"qmd search failed: {e}")
        return []

    def _search_native(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Sucht mittels nativer Python-Implementierung."""
        query_vector = self.model.encode(query).tolist()
        dense_results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k * 2
        ).points

        results_map = {}
        for res in dense_results:
            path = res.payload["doc_id"]
            results_map[path] = {
                "path": path,
                "content": res.payload["content"],
                "filename": res.payload.get("filename", ""),
                "score": res.score,
                "metadata": res.payload
            }

        if self.bm25:
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
                        results_map[path] = {
                            "path": path,
                            "content": doc["content"],
                            "score": float(scores[idx]),
                            "metadata": doc["metadata"],
                            "filename": doc["metadata"].get("filename", "")
                        }

        sorted_results = sorted(results_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:top_k]
