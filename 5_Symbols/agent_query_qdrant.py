#!/usr/bin/env python3
"""
AI Agent Query Tool for Qdrant Second Brain.

Provides functions that AI agents (Copilot, Claude, GPT, etc.) can call
to search, count, inspect, and manage the Qdrant vector database.

Can be used as:
  1. Imported as a module:    from agent_query_qdrant import search, get_stats
  2. CLI with natural query:  python agent_query_qdrant.py "how to set up docker"
  3. CLI interactive mode:    python agent_query_qdrant.py --interactive

Requires: pip install qdrant-client sentence-transformers
"""

import os
import sys
import json
import hashlib
import argparse
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────────
LXC_IP       = "192.168.2.227"
QDRANT_PORT  = 6333
COLLECTION   = "mac_repo_index"
MODEL_NAME   = "all-MiniLM-L6-v2"
MAX_TEXT_LEN = 8000
# ───────────────────────────────────────────────────────────────────────────────

_client = None
_model  = None


def _get_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        _client = QdrantClient(host=LXC_IP, port=QDRANT_PORT, timeout=10)
    return _client


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


# ═══════════════════════════════════════════════════════════════════════════════
#  QUERY FUNCTIONS — for AI agents to call
# ═══════════════════════════════════════════════════════════════════════════════

def search(query: str, limit: int = 10, collection: str = COLLECTION) -> list[dict]:
    """
    Semantic search across the second brain.

    Args:
        query:      Natural language search query
        limit:      Max results to return (default 10)
        collection: Qdrant collection name

    Returns:
        List of dicts with keys: id, score, filename, path, text
    """
    model  = _get_model()
    client = _get_client()

    vector = model.encode(query[:MAX_TEXT_LEN]).tolist()

    hits = client.search(
        collection_name=collection,
        query_vector=vector,
        limit=limit,
        with_payload=True,
    )

    results = []
    for hit in hits:
        p = hit.payload or {}
        results.append({
            "id":       hit.id,
            "score":    round(hit.score, 4),
            "filename": p.get("filename", ""),
            "path":     p.get("path", ""),
            "text":     (p.get("text", "") or p.get("content", ""))[:500],
        })
    return results


def get_file_content(file_path: str) -> Optional[str]:
    """
    Read a file's full content from disk given its path (from search results).

    Args:
        file_path: Absolute path to the file

    Returns:
        File content as string, or None if not found
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return None


def get_stats(collection: str = COLLECTION) -> dict:
    """
    Get statistics about the Qdrant collection.

    Returns:
        Dict with: total_points, status, vector_size, distance, segments
    """
    client = _get_client()
    info = client.get_collection(collection)

    return {
        "collection":   collection,
        "total_points": info.points_count,
        "status":       str(info.status),
        "vector_size":  info.config.params.vectors.size,
        "distance":     str(info.config.params.vectors.distance),
        "segments":     info.segments_count,
    }


def list_collections() -> list[str]:
    """List all Qdrant collections."""
    client = _get_client()
    cols = client.get_collections()
    return [c.name for c in cols.collections]


def count_points(collection: str = COLLECTION) -> int:
    """Return the total number of indexed points (files) in the collection."""
    client = _get_client()
    return client.count(collection_name=collection).count


def get_point_by_path(file_path: str, collection: str = COLLECTION) -> Optional[dict]:
    """
    Look up a specific file's vector entry by its path.

    Args:
        file_path: The absolute path of the file to look up

    Returns:
        Dict with id, payload if found, None otherwise
    """
    client = _get_client()
    pid = int(hashlib.md5(file_path.encode()).hexdigest(), 16) % (10**12)

    try:
        points = client.retrieve(
            collection_name=collection,
            ids=[pid],
            with_payload=True,
            with_vectors=False,
        )
        if points:
            p = points[0]
            return {"id": p.id, "payload": p.payload}
    except Exception:
        pass
    return None


def search_by_filename(filename: str, limit: int = 20, collection: str = COLLECTION) -> list[dict]:
    """
    Filter search — find entries by filename (exact or partial match).

    Args:
        filename: Full or partial filename to filter by (e.g. "docker" or "setup.md")
        limit:    Max results

    Returns:
        List of matching point payloads
    """
    from qdrant_client.models import Filter, FieldCondition, MatchText

    client = _get_client()
    results = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="filename", match=MatchText(text=filename))]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return [
        {"id": p.id, "filename": p.payload.get("filename", ""), "path": p.payload.get("path", "")}
        for p in results[0]
    ]


def health_check() -> dict:
    """
    Check connectivity to Qdrant and return health status.

    Returns:
        Dict with: connected, url, collections, total_points
    """
    try:
        client = _get_client()
        cols = list_collections()
        points = sum(count_points(c) for c in cols)
        return {
            "connected":    True,
            "url":          f"http://{LXC_IP}:{QDRANT_PORT}",
            "collections":  cols,
            "total_points": points,
        }
    except Exception as e:
        return {
            "connected": False,
            "url":       f"http://{LXC_IP}:{QDRANT_PORT}",
            "error":     str(e),
        }


def delete_by_path(file_path: str, collection: str = COLLECTION) -> bool:
    """
    Delete a file's entry from Qdrant by its path.

    Args:
        file_path: Absolute path of the file to remove

    Returns:
        True if deletion was attempted
    """
    client = _get_client()
    pid = int(hashlib.md5(file_path.encode()).hexdigest(), 16) % (10**12)
    client.delete(collection_name=collection, points_selector=[pid])
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def _format_results(results: list[dict]) -> str:
    """Pretty-print search results for terminal output."""
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        score_pct = r["score"] * 100
        lines.append(f"\n{'─' * 60}")
        lines.append(f"  #{i}  {r['filename']}  ({score_pct:.1f}%)")
        lines.append(f"  Path: {r['path']}")
        if r.get("text"):
            snippet = r["text"][:200].replace("\n", " ")
            lines.append(f"  {snippet}...")
    lines.append(f"\n{'─' * 60}")
    lines.append(f"  {len(results)} results")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Query Tool for Qdrant Second Brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent_query_qdrant.py "docker setup guide"
  python agent_query_qdrant.py "kubernetes" --limit 5 --json
  python agent_query_qdrant.py --stats
  python agent_query_qdrant.py --health
  python agent_query_qdrant.py --find-file "README"
  python agent_query_qdrant.py --interactive
        """,
    )
    parser.add_argument("query", nargs="?", help="Natural language search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--collection", "-c", default=COLLECTION, help="Collection name")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--health", action="store_true", help="Check Qdrant connectivity")
    parser.add_argument("--count", action="store_true", help="Count indexed points")
    parser.add_argument("--find-file", metavar="NAME", help="Search by filename")
    parser.add_argument("--lookup", metavar="PATH", help="Look up a specific file path")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive search mode")

    args = parser.parse_args()

    # ── Dispatch ───────────────────────────────────────────────────────────
    if args.health:
        result = health_check()
        print(json.dumps(result, indent=2) if args.json else
              f"Connected: {result['connected']}\n"
              f"URL: {result['url']}\n"
              f"Collections: {result.get('collections', 'N/A')}\n"
              f"Total points: {result.get('total_points', 'N/A')}")
        return

    if args.stats:
        result = get_stats(args.collection)
        print(json.dumps(result, indent=2) if args.json else
              f"Collection: {result['collection']}\n"
              f"Points: {result['total_points']}\n"
              f"Status: {result['status']}\n"
              f"Vector size: {result['vector_size']}\n"
              f"Distance: {result['distance']}")
        return

    if args.count:
        n = count_points(args.collection)
        print(json.dumps({"count": n}) if args.json else f"Indexed points: {n}")
        return

    if args.find_file:
        results = search_by_filename(args.find_file, args.limit, args.collection)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['filename']}  →  {r['path']}")
            print(f"\n  {len(results)} matches")
        return

    if args.lookup:
        result = get_point_by_path(args.lookup, args.collection)
        if result:
            print(json.dumps(result, indent=2) if args.json else
                  f"ID: {result['id']}\nPayload: {result['payload']}")
        else:
            print("Not found in Qdrant")
        return

    if args.interactive:
        print("╔══════════════════════════════════════════════╗")
        print("║  Qdrant Second Brain — Interactive Search    ║")
        print("║  Type a query, or 'quit' to exit             ║")
        print("╚══════════════════════════════════════════════╝\n")
        while True:
            try:
                q = input("🔍 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if q.lower() in ("quit", "exit", "q"):
                break
            if not q:
                continue
            results = search(q, args.limit, args.collection)
            print(_format_results(results))
        return

    if args.query:
        results = search(args.query, args.limit, args.collection)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(_format_results(results))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
