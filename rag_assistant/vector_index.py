"""Small local vector index backed by SQLite; no network service or model loading."""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np


class VectorIndex:
    """Persist reviewed knowledge chunks and retrieve them by cosine distance."""

    def __init__(self, persist_dir: str, name: str):
        self.path = Path(persist_dir) / "vectors.sqlite3"
        self.name = name
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS collections (name TEXT PRIMARY KEY, metadata TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS chunks (collection TEXT NOT NULL, id TEXT NOT NULL, document TEXT NOT NULL, metadata TEXT NOT NULL, embedding TEXT NOT NULL, PRIMARY KEY(collection, id))")
            db.execute("INSERT OR IGNORE INTO collections VALUES (?, '{}')", (self.name,))

    def _connect(self):
        return sqlite3.connect(str(self.path), timeout=15)

    @property
    def metadata(self) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT metadata FROM collections WHERE name = ?", (self.name,)).fetchone()
        return json.loads(row[0]) if row else {}

    def count(self) -> int:
        with self._connect() as db:
            return db.execute("SELECT COUNT(*) FROM chunks WHERE collection = ?", (self.name,)).fetchone()[0]

    @staticmethod
    def _vector(values):
        if not 1 <= len(values) <= 8192 or not all(math.isfinite(float(v)) for v in values):
            raise ValueError("Embedding must contain a bounded list of finite numbers.")
        result = np.asarray(values, dtype=np.float32)
        if result.ndim != 1 or not np.all(np.isfinite(result)):
            raise ValueError("Embedding must be a finite vector.")
        return result

    def replace(self, ids, documents, metadatas, embeddings, metadata, *, clear=True):
        if not (len(ids) == len(documents) == len(metadatas) == len(embeddings)) or len(ids) > 10000:
            raise ValueError("Knowledge chunks and embeddings must have matching, bounded lengths.")
        rows = []
        dimension = None
        for key, document, info, embedding in zip(ids, documents, metadatas, embeddings):
            vector = self._vector(embedding)
            if dimension is not None and vector.size != dimension:
                raise ValueError("Embeddings have inconsistent dimensions.")
            dimension = vector.size
            rows.append((self.name, str(key), str(document), json.dumps(info, allow_nan=False), json.dumps(vector.tolist(), allow_nan=False)))
        # Replacing the index and its fingerprint is one transaction. A failed
        # embedding request or concurrent reader never sees a half-built index.
        with self._connect() as db:
            if clear:
                db.execute("DELETE FROM chunks WHERE collection = ?", (self.name,))
            db.executemany("INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?)", rows)
            db.execute("UPDATE collections SET metadata = ? WHERE name = ?", (json.dumps(metadata, allow_nan=False), self.name))

    def query(self, query_embeddings, n_results=4, include=None):
        del include
        if not 1 <= n_results <= 20 or len(query_embeddings) != 1:
            raise ValueError("Query must request between one and twenty chunks for one vector.")
        query = self._vector(query_embeddings[0])
        norm = float(np.linalg.norm(query))
        with self._connect() as db:
            rows = db.execute("SELECT document, metadata, embedding FROM chunks WHERE collection = ? LIMIT 10001", (self.name,)).fetchall()
        if len(rows) > 10000:
            raise ValueError("Knowledge index exceeds its supported size.")
        scored = []
        for document, metadata, embedding in rows:
            vector = self._vector(json.loads(embedding))
            if vector.shape != query.shape:
                raise ValueError("Rebuild the index after changing the embedding model.")
            denominator = norm * float(np.linalg.norm(vector))
            similarity = float(np.dot(query, vector)) / denominator if denominator else 0.0
            scored.append((max(0.0, min(2.0, 1.0 - similarity)), document, json.loads(metadata)))
        selected = sorted(scored, key=lambda item: item[0])[:n_results]
        return {"documents": [[x[1] for x in selected]], "metadatas": [[x[2] for x in selected]], "distances": [[x[0] for x in selected]]}
