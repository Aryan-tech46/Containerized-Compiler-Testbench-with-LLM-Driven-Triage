"""Vector Store and RAG retrieval module for compiler crashes and historical bugs.

Connects to Pinecone (or graceful in-memory cosine similarity fallback)
to index and retrieve historical compiler bug signatures and ICE traces.
"""

import json
import math
import os
import re
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional

warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv

load_dotenv()

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None
    ServerlessSpec = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class HistoricalBugVectorStore:
    """Manages Pinecone vector database indexing, embedding, and semantic retrieval for compiler crashes."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        dimension: int = 768,
        metric: str = "cosine",
    ):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY", "")
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "compiler-crashes")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.dimension = dimension
        self.metric = metric

        # Local in-memory repository for local fallback / offline execution
        self._local_records: List[Dict[str, Any]] = []

        self._pc: Optional[Any] = None
        self._index: Optional[Any] = None

        self._init_error: Optional[str] = None

        if self.gemini_api_key and genai is not None:
            try:
                genai.configure(api_key=self.gemini_api_key)
            except Exception:
                pass

        self._init_pinecone()

    def _init_pinecone(self) -> None:
        """Attempts to initialize Pinecone connection if credentials are configured."""
        if not self.api_key or Pinecone is None:
            return

        try:
            self._pc = Pinecone(api_key=self.api_key)
            indexes_info = self._pc.list_indexes()
            existing_indexes = []
            for item in indexes_info:
                if hasattr(item, "name"):
                    existing_indexes.append(item.name)
                elif isinstance(item, dict) and "name" in item:
                    existing_indexes.append(item["name"])
                else:
                    existing_indexes.append(str(item))

            if self.index_name not in existing_indexes and ServerlessSpec is not None:
                try:
                    self._pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric=self.metric,
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                    )
                except Exception as create_err:
                    self._init_error = f"Index creation error: {str(create_err)}"

            self._index = self._pc.Index(self.index_name)
        except Exception as e:
            self._init_error = str(e)
            self._index = None

    def test_connection(self) -> Dict[str, Any]:
        """Tests the Pinecone connection and returns status diagnostics."""
        if not self.api_key:
            return {
                "connected": False,
                "message": "PINECONE_API_KEY is not set in environment or .env file",
            }
        if self._index is not None:
            try:
                stats = self._index.describe_index_stats()
                vector_count = getattr(stats, "total_vector_count", None)
                if vector_count is None and isinstance(stats, dict):
                    vector_count = stats.get("total_vector_count", 0)
                dim = getattr(stats, "dimension", None)
                if dim is None and isinstance(stats, dict):
                    dim = stats.get("dimension", self.dimension)
                return {
                    "connected": True,
                    "index_name": self.index_name,
                    "total_vector_count": vector_count if vector_count is not None else 0,
                    "dimension": dim if dim is not None else self.dimension,
                    "message": "Successfully connected to Pinecone index",
                }
            except Exception as e:
                return {
                    "connected": False,
                    "message": f"Connected to client, but failed to query index: {str(e)}",
                }
        return {
            "connected": False,
            "message": f"Pinecone initialization failed: {self._init_error or 'Unknown error'}",
        }

    def _simple_text_embedding(self, text: str, dim: int = 768) -> List[float]:
        """Generates a deterministic pseudo-semantic dense vector for offline/mock embedding."""
        words = re.findall(r"\w+", text.lower())
        vec = [0.0] * dim
        if not words:
            return vec

        for word in words:
            h = hash(word)
            idx = abs(h) % dim
            sign = 1.0 if (h >> 3) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def get_embedding(self, text: str) -> List[float]:
        """Generates an embedding vector for text using Gemini API or fallback embedding."""
        if self.gemini_api_key and genai is not None:
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_query",
                )
                embedding = result.get("embedding", [])
                if embedding and len(embedding) == self.dimension:
                    return embedding
            except Exception:
                pass

        return self._simple_text_embedding(text, dim=self.dimension)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two unit vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return float(dot)

    def seed_historical_bugs(self, json_path: str = "data/historical_bugs.json") -> int:
        """Loads crash traces from JSON, computes embeddings, and upserts them to Pinecone (or local store).

        Returns:
            Number of indexed records.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Bug dataset not found at {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            bugs = json.load(f)

        records_to_upsert = []
        self._local_records = []

        for item in bugs:
            text_for_embedding = f"{item.get('category', '')} {item.get('crash_signature', '')} {item.get('root_cause', '')}"
            vec = self.get_embedding(text_for_embedding)

            record = {
                "id": item["bug_id"],
                "values": vec,
                "metadata": {
                    "bug_id": item["bug_id"],
                    "compiler": item.get("compiler", "gcc"),
                    "version": item.get("version", ""),
                    "category": item.get("category", ""),
                    "flags": item.get("flags", ""),
                    "crash_signature": item.get("crash_signature", ""),
                    "root_cause": item.get("root_cause", ""),
                    "workaround": item.get("workaround", ""),
                },
            }
            records_to_upsert.append(record)
            self._local_records.append(record)

        if self._index is not None:
            try:
                # Upsert to Pinecone in batches of 50
                batch_size = 50
                for i in range(0, len(records_to_upsert), batch_size):
                    batch = records_to_upsert[i : i + batch_size]
                    self._index.upsert(vectors=batch)
            except Exception:
                pass

        return len(records_to_upsert)

    def query_similar_bugs(self, crash_log: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Converts incoming runtime crash logs into embeddings and returns nearest matches with cosine similarity scores.

        Args:
            crash_log: Raw compiler output, segmentation fault, or ICE trace.
            top_k: Number of nearest matches to retrieve.

        Returns:
            List of matching records with metadata and similarity scores.
        """
        query_vec = self.get_embedding(crash_log)

        # 1. Try querying Pinecone index if active
        if self._index is not None:
            try:
                response = self._index.query(
                    vector=query_vec,
                    top_k=top_k,
                    include_metadata=True,
                )
                matches_list = getattr(response, "matches", None)
                if matches_list is None and isinstance(response, dict):
                    matches_list = response.get("matches", [])

                matches = []
                for match in (matches_list or []):
                    m_id = getattr(match, "id", None) or (match.get("id") if isinstance(match, dict) else str(match))
                    m_score = getattr(match, "score", None) or (match.get("score") if isinstance(match, dict) else 0.0)
                    m_meta = getattr(match, "metadata", None) or (match.get("metadata") if isinstance(match, dict) else {}) or {}

                    matches.append(
                        {
                            "bug_id": m_meta.get("bug_id", m_id),
                            "score": float(m_score),
                            "compiler": m_meta.get("compiler", ""),
                            "version": m_meta.get("version", ""),
                            "category": m_meta.get("category", ""),
                            "flags": m_meta.get("flags", ""),
                            "root_cause": m_meta.get("root_cause", ""),
                            "workaround": m_meta.get("workaround", ""),
                            "crash_signature": m_meta.get("crash_signature", ""),
                        }
                    )
                if matches:
                    return matches
            except Exception:
                pass

        # 2. Local fallback retrieval
        if not self._local_records:
            default_json = Path(__file__).parent.parent.parent / "data" / "historical_bugs.json"
            if default_json.exists():
                self.seed_historical_bugs(str(default_json))

        scored = []
        for rec in self._local_records:
            score = self._cosine_similarity(query_vec, rec["values"])
            meta = rec["metadata"]
            scored.append(
                {
                    "bug_id": meta.get("bug_id", rec["id"]),
                    "score": round(float(score), 4),
                    "compiler": meta.get("compiler", ""),
                    "version": meta.get("version", ""),
                    "category": meta.get("category", ""),
                    "flags": meta.get("flags", ""),
                    "root_cause": meta.get("root_cause", ""),
                    "workaround": meta.get("workaround", ""),
                    "crash_signature": meta.get("crash_signature", ""),
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


if __name__ == "__main__":
    store = HistoricalBugVectorStore()
    count = store.seed_historical_bugs("data/historical_bugs.json")
    print(f"Seeded {count} bugs.")
    test_query = "internal compiler error: Segmentation fault in instantiate_class_template at cp/pt.c"
    results = store.query_similar_bugs(test_query, top_k=3)
    print("Top query results:")
    for r in results:
        print(f"  [{r['score']}] {r['bug_id']} - {r['category']}")
