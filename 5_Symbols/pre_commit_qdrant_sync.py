#!/usr/bin/env python3
"""
Pre-commit hook script: Sync staged .md files to Qdrant on Proxmox.

Called from the git pre-commit hook in the second brain repo.
Only processes files that are staged (new, modified, or deleted).
Non-blocking by default — if Qdrant is unreachable, the commit still proceeds.

Usage:
    Invoked automatically by .git/hooks/pre-commit
    Or manually:  python pre_commit_qdrant_sync.py
"""

import os
import sys
import hashlib
import subprocess

# ── Configuration ──────────────────────────────────────────────────────────────
LXC_IP          = "192.168.2.227"
QDRANT_PORT     = 6333
COLLECTION      = "mac_repo_index"
MODEL_NAME      = "all-MiniLM-L6-v2"
VECTOR_DIM      = 384
MAX_TEXT_LEN    = 8000
BLOCK_ON_FAILURE = False  # Set True to abort commit if Qdrant is unreachable
# ───────────────────────────────────────────────────────────────────────────────

PREFIX = "[pre-commit-sync]"


def get_staged_files():
    """Return (added/modified, deleted) lists of staged .md file paths."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        return [], []

    changed = []
    deleted = []

    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, filepath = parts[0].strip(), parts[1].strip()

        if not filepath.endswith(".md"):
            continue

        if status.startswith("D"):
            deleted.append(filepath)
        else:
            # A (added), M (modified), R (renamed), C (copied)
            changed.append(filepath)

    return changed, deleted


def file_id(path: str) -> int:
    """Deterministic ID matching ingest.py — MD5 of full path mod 10^12."""
    full_path = os.path.join(os.getcwd(), path)
    return int(hashlib.md5(full_path.encode()).hexdigest(), 16) % (10**12)


def main():
    changed, deleted = get_staged_files()

    if not changed and not deleted:
        print(f"  {PREFIX} No staged .md files — nothing to sync")
        return 0

    # ── Import heavy deps only when needed ─────────────────────────────────
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"  {PREFIX} ⚠️  Missing dependency: {e}")
        print(f"  {PREFIX} Run: pip install qdrant-client sentence-transformers")
        return 1 if BLOCK_ON_FAILURE else 0

    # ── Connect to Qdrant ──────────────────────────────────────────────────
    try:
        client = QdrantClient(host=LXC_IP, port=QDRANT_PORT, timeout=10)
        client.get_collections()  # quick connectivity test
    except Exception as e:
        print(f"  {PREFIX} ⚠️  Qdrant unreachable at {LXC_IP}:{QDRANT_PORT} — {e}")
        if BLOCK_ON_FAILURE:
            print(f"  {PREFIX} ❌ Aborting commit (BLOCK_ON_FAILURE=True)")
            return 1
        print(f"  {PREFIX} Skipping sync (commit will proceed)")
        return 0

    # ── Handle changed/new files ───────────────────────────────────────────
    synced, errors = 0, 0

    if changed:
        print(f"  {PREFIX} {len(changed)} staged .md file(s) to process")

        # Load model once
        model = SentenceTransformer(MODEL_NAME)

        for filepath in changed:
            try:
                full_path = os.path.join(os.getcwd(), filepath)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                if not text.strip():
                    continue

                vector = model.encode(text[:MAX_TEXT_LEN]).tolist()
                pid = file_id(filepath)

                client.upsert(
                    collection_name=COLLECTION,
                    points=[PointStruct(
                        id=pid,
                        vector=vector,
                        payload={
                            "filename": os.path.basename(filepath),
                            "path": full_path,
                        }
                    )]
                )
                synced += 1
                print(f"  ✓ {filepath}")

            except Exception as e:
                errors += 1
                print(f"  ✗ {filepath}: {e}")

    # ── Handle deleted files ───────────────────────────────────────────────
    if deleted:
        print(f"  {PREFIX} {len(deleted)} deleted .md file(s) to remove from Qdrant")

        for filepath in deleted:
            try:
                pid = file_id(filepath)
                client.delete(
                    collection_name=COLLECTION,
                    points_selector=[pid],
                )
                print(f"  ✗ {filepath} (deleted from Qdrant)")
            except Exception as e:
                errors += 1
                print(f"  ✗ {filepath} delete failed: {e}")

    print(f"  {PREFIX} Done: {synced} synced, {len(deleted)} deleted, {errors} errors")

    if errors > 0 and BLOCK_ON_FAILURE:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
