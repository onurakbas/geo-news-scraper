"""
Embedding-based deduplication for news articles.

Algorithm:
  1. Fetch all news documents that have no similarity_group_id yet (or all, on
     a full re-run).
  2. Generate / reuse embeddings for each document.
  3. For each pair of documents published within SAME_DAY_WINDOW days of each
     other, compute cosine similarity.
  4. If similarity >= SIMILARITY_THRESHOLD, assign them the same
     similarity_group_id (the ObjectId of the earliest article in the group).
  5. Persist the updated similarity_group_id and embedding back to MongoDB.

Designed to run synchronously (pymongo) so it can be invoked from a plain
Python script without an async event loop.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pymongo
from loguru import logger

from app.services.nlp.embedder import embed_batch

# ── Constants ────────────────────────────────────────────────────────────────

SIMILARITY_THRESHOLD: float = 0.90
"""Cosine similarity at or above which two articles are considered duplicates."""

SAME_DAY_WINDOW: int = 3
"""Two articles must be published within this many days of each other to be
compared.  Prevents distant articles from being incorrectly grouped."""

BATCH_SIZE: int = 256
"""Number of documents to process per embedding batch."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cosine_similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    """
    Compute pairwise cosine similarities for an (N, D) matrix of already
    unit-normalised vectors.  Since ||v|| == 1, dot product == cosine sim.
    """
    return np.dot(vectors, vectors.T)


def _group_id_for(doc: dict) -> str:
    """Return the group seed: prefer existing group id, else use the doc's _id."""
    return str(doc.get("similarity_group_id") or doc["_id"])


# ── Core deduplication logic ─────────────────────────────────────────────────

def run_deduplication(
    mongo_uri: str | None = None,
    db_name: str | None = None,
    full_rerun: bool = False,
) -> dict[str, int]:
    """
    Run the full deduplication pipeline against the MongoDB `news` collection.

    Args:
        mongo_uri:  MongoDB connection URI. Falls back to env MONGODB_URI.
        db_name:    Database name.  Falls back to env MONGODB_DB_NAME.
        full_rerun: If True, re-process ALL documents (ignore existing groups).
                    If False (default), only process documents without an
                    embedding or without a similarity_group_id.

    Returns:
        A summary dict with counts: total, embedded, grouped, updated.
    """
    _uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    _db_name = db_name or os.getenv("MONGODB_DB_NAME", "geo_news")

    client = pymongo.MongoClient(_uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[_db_name]
        collection = db["news"]

        # ── Step 1: Fetch candidate documents ────────────────────────────────
        query: dict[str, Any] = {}
        if not full_rerun:
            # Only articles that still need processing
            query = {
                "$or": [
                    {"embedding": None},
                    {"embedding": {"$exists": False}},
                    {"similarity_group_id": None},
                    {"similarity_group_id": {"$exists": False}},
                ]
            }

        projection = {
            "_id": 1,
            "title": 1,
            "content": 1,
            "published_at": 1,
            "embedding": 1,
            "similarity_group_id": 1,
        }

        docs: list[dict] = list(collection.find(query, projection))
        total = len(docs)
        logger.info(f"Deduplication: found {total} candidate documents.")

        if total == 0:
            return {"total": 0, "embedded": 0, "grouped": 0, "updated": 0}

        # ── Step 2: Generate embeddings for docs that lack them ───────────────
        needs_embedding = [d for d in docs if not d.get("embedding")]
        embedded_count = 0

        if needs_embedding:
            logger.info(f"Generating embeddings for {len(needs_embedding)} documents…")
            # Process in batches to manage memory
            for start in range(0, len(needs_embedding), BATCH_SIZE):
                batch = needs_embedding[start : start + BATCH_SIZE]
                vectors = embed_batch(batch)
                for doc, vec in zip(batch, vectors):
                    doc["embedding"] = vec
                embedded_count += len(batch)
                logger.info(
                    f"  Embedded {min(start + BATCH_SIZE, len(needs_embedding))}"
                    f"/{len(needs_embedding)}"
                )

        # Persist newly generated embeddings to MongoDB before grouping
        if needs_embedding:
            logger.info("Saving new embeddings to MongoDB…")
            bulk_ops = []
            for doc in needs_embedding:
                bulk_ops.append(
                    pymongo.UpdateOne(
                        {"_id": doc["_id"]},
                        {"$set": {"embedding": doc["embedding"], "updated_at": datetime.now(tz=timezone.utc)}},
                    )
                )
            if bulk_ops:
                result = collection.bulk_write(bulk_ops, ordered=False)
                logger.info(f"Embeddings saved: {result.modified_count} documents updated.")

        # ── Step 3: Build similarity matrix and assign groups ─────────────────
        # Only docs with embeddings can be grouped
        docs_with_embeddings = [d for d in docs if d.get("embedding")]
        n = len(docs_with_embeddings)
        logger.info(f"Computing similarity matrix for {n} documents…")

        if n < 2:
            logger.info("Not enough documents to compare – skipping grouping.")
            return {"total": total, "embedded": embedded_count, "grouped": 0, "updated": 0}

        vectors = np.array([d["embedding"] for d in docs_with_embeddings], dtype=np.float32)
        sim_matrix = _cosine_similarity_matrix(vectors)

        # Union-Find structure for transitive grouping
        parent: dict[int, int] = {i: i for i in range(n)}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # path compression
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        grouped_pairs = 0
        for i in range(n):
            pub_i: datetime | None = docs_with_embeddings[i].get("published_at")
            for j in range(i + 1, n):
                # Fast short-circuit: skip if already in same group
                if find(i) == find(j):
                    continue

                # Date-window filter
                pub_j: datetime | None = docs_with_embeddings[j].get("published_at")
                if pub_i and pub_j:
                    # Make both timezone-aware for safe comparison
                    pi = pub_i.replace(tzinfo=timezone.utc) if pub_i.tzinfo is None else pub_i
                    pj = pub_j.replace(tzinfo=timezone.utc) if pub_j.tzinfo is None else pub_j
                    if abs((pi - pj).days) > SAME_DAY_WINDOW:
                        continue

                sim: float = float(sim_matrix[i, j])
                if sim >= SIMILARITY_THRESHOLD:
                    logger.debug(
                        f"  DUPLICATE pair ({i},{j}) sim={sim:.4f} | "
                        f"'{docs_with_embeddings[i].get('title', '')[:60]}' "
                        f"<-> '{docs_with_embeddings[j].get('title', '')[:60]}'"
                    )
                    union(i, j)
                    grouped_pairs += 1

        logger.info(f"Found {grouped_pairs} duplicate pairs.")

        # ── Step 4: Assign similarity_group_id and persist ───────────────────
        # Map each root index to the _id of the "oldest" doc in that group
        # (smallest published_at or smallest _id as tiebreaker)
        root_to_group_id: dict[int, str] = {}

        for i in range(n):
            root = find(i)
            if root not in root_to_group_id:
                # First time we see this root — use this doc's _id as the group seed
                root_to_group_id[root] = str(docs_with_embeddings[root]["_id"])

        update_ops = []
        updated_count = 0

        for i, doc in enumerate(docs_with_embeddings):
            root = find(i)
            new_group_id = root_to_group_id[root]
            old_group_id = str(doc.get("similarity_group_id") or "")

            if new_group_id != old_group_id:
                update_ops.append(
                    pymongo.UpdateOne(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "similarity_group_id": new_group_id,
                                "updated_at": datetime.now(tz=timezone.utc),
                            }
                        },
                    )
                )
                updated_count += 1

        if update_ops:
            result = collection.bulk_write(update_ops, ordered=False)
            logger.info(f"Group assignments saved: {result.modified_count} documents updated.")
        else:
            logger.info("No group assignment changes needed.")

        summary = {
            "total": total,
            "embedded": embedded_count,
            "grouped": grouped_pairs,
            "updated": updated_count,
        }
        logger.info(f"Deduplication complete: {summary}")
        return summary

    finally:
        client.close()
