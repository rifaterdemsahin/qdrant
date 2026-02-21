#!/usr/bin/env python3
"""
Local REST search server for Qdrant semantic search.

Runs on http://localhost:8111 — used by:
  • Obsidian QuickAdd macros (Option B)
  • Custom Frames plugin (Option A — via served search.html)
  • Any HTTP client (curl, fetch, etc.)

Endpoints:
  POST /search   {"query": "...", "limit": 10}  →  JSON results
  GET  /health                                   →  {"status": "ok"}
  GET  /                                         →  Redirects to search.html

Start:
  cd /Users/rifaterdemsahin/projects/qdrant
  source venv/bin/activate
  python 5_Symbols/qdrant_search_server.py
"""

import os
import json
import hashlib
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# ── Configuration ──────────────────────────────────────────────────────────────
HOST            = "0.0.0.0"
PORT            = 8111
LXC_IP          = "192.168.2.227"
QDRANT_PORT     = 6333
COLLECTION      = "mac_repo_index"
MODEL_NAME      = "all-MiniLM-L6-v2"
MAX_TEXT_LEN    = 8000
PROJECT_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ───────────────────────────────────────────────────────────────────────────────

# Lazy-loaded globals
_client = None
_model  = None


def get_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        _client = QdrantClient(host=LXC_IP, port=QDRANT_PORT, timeout=10)
    return _client


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"  Loading model {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        print("  Model ready")
    return _model


def do_search(query: str, limit: int = 10, collection: str = COLLECTION):
    """Embed the query and search Qdrant.  Returns a list of result dicts."""
    model  = get_model()
    client = get_client()

    vector = model.encode(query[:MAX_TEXT_LEN]).tolist()

    hits = client.search(
        collection_name=collection,
        query_vector=vector,
        limit=limit,
        with_payload=True,
    )

    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append({
            "id":       hit.id,
            "score":    round(hit.score, 4),
            "filename": payload.get("filename", ""),
            "path":     payload.get("path", ""),
            "text":     payload.get("text", payload.get("content", "")),
        })
    return results


class SearchHandler(SimpleHTTPRequestHandler):
    """HTTP handler with /search and /health endpoints, plus static file serving."""

    def __init__(self, *args, **kwargs):
        # Serve static files from the project root (so search.html etc. work)
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)

    # ── CORS headers (needed from Obsidian custom frames) ──────────────────
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ── GET endpoints ──────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._json_response({"status": "ok", "qdrant": f"{LXC_IP}:{QDRANT_PORT}"})
            return

        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/5_Symbols/search.html")
            self.end_headers()
            return

        # Fall through to static file serving
        super().do_GET()

    # ── POST /search ───────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/search":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}

                query      = body.get("query", "").strip()
                limit      = min(int(body.get("limit", 10)), 100)
                collection = body.get("collection", COLLECTION)

                if not query:
                    self._json_response({"error": "query is required"}, status=400)
                    return

                results = do_search(query, limit, collection)
                self._json_response(results)

            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
            return

        self.send_response(404)
        self.end_headers()

    # ── Helpers ────────────────────────────────────────────────────────────
    def _json_response(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Quieter logging — only show search requests
        msg = format % args
        if "/search" in msg or "error" in msg.lower():
            print(f"  {msg}")


def main():
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  Qdrant Search Server                       ║")
    print(f"║  http://localhost:{PORT}                      ║")
    print(f"║  Qdrant: {LXC_IP}:{QDRANT_PORT}               ║")
    print(f"║  Collection: {COLLECTION:<28s}  ║")
    print(f"╚══════════════════════════════════════════════╝")
    print()
    print("  Endpoints:")
    print(f"    GET  /health              → connectivity check")
    print(f"    POST /search              → semantic search")
    print(f"    GET  /                    → search.html UI")
    print()
    print("  Press Ctrl+C to stop")
    print()

    # Pre-load model on startup so first search is fast
    get_model()

    server = HTTPServer((HOST, PORT), SearchHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
