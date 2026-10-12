"""Redis caching and logging utilities with graceful in-memory fallback."""

import json
import os
import hashlib
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

try:
    import redis
except ImportError:
    redis = None


class TriageCache:
    """Provides key-value caching for LLM triage reports and RAG queries."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ttl_seconds: int = 86400,
    ):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", "6379"))
        self.ttl = ttl_seconds
        self._memory_cache: dict[str, str] = {}
        self._client: Optional[Any] = None

        if redis is not None:
            try:
                client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    socket_connect_timeout=1,
                    decode_responses=True,
                )
                client.ping()
                self._client = client
            except Exception:
                self._client = None

    def _hash_key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, key_text: str) -> Optional[dict]:
        """Retrieves cached json payload by text hash."""
        h = self._hash_key(key_text)
        if self._client is not None:
            try:
                data = self._client.get(f"antigravity:triage:{h}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        if h in self._memory_cache:
            return json.loads(self._memory_cache[h])
        return None

    def set(self, key_text: str, data: dict) -> None:
        """Stores json payload into cache with TTL."""
        h = self._hash_key(key_text)
        serialized = json.dumps(data)
        if self._client is not None:
            try:
                self._client.setex(f"antigravity:triage:{h}", self.ttl, serialized)
            except Exception:
                pass
        self._memory_cache[h] = serialized
