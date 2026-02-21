#!/usr/bin/env python3
"""
Sync daily & weekly changes from second brain to Qdrant.

Modes:
  --daily    Sync files modified in the last 24 hours (default)
  --weekly   Sync files modified in the last 7 days
  --since N  Sync files modified in the last N hours
  --dry-run  Show what would be synced without actually upserting

Also detects deleted files and removes them from Qdrant.

Usage:
  cd /Users/rifaterdemsahin/projects/qdrant
  source venv/bin/activate
  python 5_Symbols/sync_changes_qdrant.py --daily
  python 5_Symbols/sync_changes_qdrant.py --weekly
  python 5_Symbols/sync_changes_qdrant.py --since 48
  python 5_Symbols/sync_changes_qdrant.py --weekly --dry-run

Automate with cron / launchd:
  Daily  at 2:00 AM:  0 2 * * *  cd ~/projects/qdrant && venv/bin/python 5_Symbols/sync_changes_qdrant.py --daily
  Weekly on Sunday:   0 3 * * 0  cd ~/projects/qdrant && venv/bin/python 5_Symbols/sync_changes_qdrant.py --weekly
"""

import os
import sys
import time
import json
import hashlib
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
LXC_IP       = "192.168.2.227"
QDRANT_PORT  = 6333
COLLECTION   = "mac_repo_index"
MODEL_NAME   = "all-MiniLM-L6-v2"
REPO_PATH    = "/Users/rifaterdemsahin/projects/secondbrain/"
MAX_TEXT_LEN = 8000
STATE_DIR    = os.path.dirname(os.path.abspath(__file__))
STATE_FILE   = os.path.join(STATE_DIR, "sync_state.json")
LOG_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ───────────────────────────────────────────────────────────────────────────────


def file_id(full_path: str) -> int:
    """Deterministic ID matching ingest.py — MD5 of full path mod 10^12."""
    return int(hashlib.md5(full_path.encode()).hexdigest(), 16) % (10**12)


def load_state() -> dict:
    """Load previous sync state (tracked file paths & their mod times)."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_sync": 0, "files": {}}


def save_state(state: dict):
    """Persist sync state to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def discover_files(repo_path: str) -> dict[str, float]:
    """Walk the repo and return {full_path: mtime} for all .md files."""
    files = {}
    for root, _, filenames in os.walk(repo_path):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full_path = os.path.join(root, fn)
            try:
                files[full_path] = os.path.getmtime(full_path)
            except OSError:
                continue
    return files


def find_changes(current_files: dict[str, float], state: dict, cutoff: float):
    """
    Compare current files against saved state and time cutoff.

    Returns:
        new_files:      Files that didn't exist in previous state
        modified_files: Files modified since cutoff
        deleted_files:  Files in previous state but no longer on disk
    """
    prev_files = state.get("files", {})

    new_files = []
    modified_files = []
    deleted_files = []

    for path, mtime in current_files.items():
        if path not in prev_files:
            new_files.append(path)
        elif mtime > cutoff:
            modified_files.append(path)

    for path in prev_files:
        if path not in current_files:
            deleted_files.append(path)

    return new_files, modified_files, deleted_files


def main():
    parser = argparse.ArgumentParser(
        description="Sync daily/weekly changes from second brain to Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--daily", action="store_true", default=True, help="Sync last 24h changes (default)")
    mode.add_argument("--weekly", action="store_true", help="Sync last 7 days of changes")
    mode.add_argument("--since", type=float, metavar="HOURS", help="Sync changes from last N hours")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without syncing")
    parser.add_argument("--full-state-rebuild", action="store_true", help="Rebuild the state file from current disk")
    parser.add_argument("--repo", default=REPO_PATH, help=f"Path to second brain repo (default: {REPO_PATH})")
    parser.add_argument("--collection", default=COLLECTION, help=f"Qdrant collection (default: {COLLECTION})")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # ── Determine time window ──────────────────────────────────────────────
    now = time.time()
    if args.since:
        hours = args.since
    elif args.weekly:
        hours = 7 * 24
    else:
        hours = 24

    cutoff = now - (hours * 3600)
    cutoff_dt = datetime.fromtimestamp(cutoff)
    now_dt = datetime.now()

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  Qdrant Second Brain — Change Sync                  ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║  Window:     {hours:.0f}h ({cutoff_dt:%Y-%m-%d %H:%M} → {now_dt:%H:%M})       ║")
    print(f"║  Repo:       {os.path.basename(args.repo.rstrip('/')):<38s}  ║")
    print(f"║  Collection: {args.collection:<38s}  ║")
    print(f"║  Qdrant:     {LXC_IP}:{QDRANT_PORT:<30}  ║")
    if args.dry_run:
        print(f"║  Mode:       DRY RUN (no changes will be made)      ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    # ── Discover current files ─────────────────────────────────────────────
    print("  Scanning repository...")
    current_files = discover_files(args.repo)
    print(f"  Found {len(current_files)} .md files on disk\n")

    # ── Load state & find changes ──────────────────────────────────────────
    state = load_state()

    if args.full_state_rebuild:
        print("  Rebuilding state file from disk...")
        state["files"] = {p: m for p, m in current_files.items()}
        state["last_sync"] = now
        save_state(state)
        print(f"  State file saved with {len(current_files)} entries\n")
        return

    new_files, modified_files, deleted_files = find_changes(current_files, state, cutoff)

    print(f"  Changes detected:")
    print(f"    New files:      {len(new_files)}")
    print(f"    Modified files: {len(modified_files)}")
    print(f"    Deleted files:  {len(deleted_files)}")
    print()

    all_to_upsert = new_files + modified_files

    if not all_to_upsert and not deleted_files:
        print("  ✓ Nothing to sync — all up to date!")
        result = {"new": 0, "modified": 0, "deleted": 0, "errors": 0, "hours": hours}
        if args.json:
            print(json.dumps(result))
        return

    # ── Dry run — just list ────────────────────────────────────────────────
    if args.dry_run:
        if new_files:
            print("  New files:")
            for f in new_files[:20]:
                print(f"    + {os.path.relpath(f, args.repo)}")
            if len(new_files) > 20:
                print(f"    ... and {len(new_files) - 20} more")

        if modified_files:
            print("\n  Modified files:")
            for f in modified_files[:20]:
                print(f"    ~ {os.path.relpath(f, args.repo)}")
            if len(modified_files) > 20:
                print(f"    ... and {len(modified_files) - 20} more")

        if deleted_files:
            print("\n  Deleted files:")
            for f in deleted_files[:20]:
                print(f"    - {os.path.relpath(f, args.repo)}")
            if len(deleted_files) > 20:
                print(f"    ... and {len(deleted_files) - 20} more")

        print(f"\n  Dry run complete — {len(all_to_upsert)} to upsert, {len(deleted_files)} to delete")
        return

    # ── Connect to Qdrant ──────────────────────────────────────────────────
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Distance, VectorParams
    from sentence_transformers import SentenceTransformer

    try:
        client = QdrantClient(host=LXC_IP, port=QDRANT_PORT, timeout=15)
        client.get_collections()
    except Exception as e:
        print(f"  ❌ Cannot connect to Qdrant: {e}")
        sys.exit(1)

    # Ensure collection exists
    if not client.collection_exists(args.collection):
        client.create_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        print(f"  Created collection: {args.collection}")

    print(f"  Loading embedding model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)

    # ── Upsert new & modified files ────────────────────────────────────────
    upserted = 0
    errors = 0

    if all_to_upsert:
        print(f"\n  Syncing {len(all_to_upsert)} files...")

        # Batch for efficiency
        batch_points = []
        batch_size = 50

        for full_path in all_to_upsert:
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                if not text.strip():
                    continue

                vector = model.encode(text[:MAX_TEXT_LEN]).tolist()
                pid = file_id(full_path)

                batch_points.append(PointStruct(
                    id=pid,
                    vector=vector,
                    payload={
                        "filename": os.path.basename(full_path),
                        "path": full_path,
                    },
                ))

                # Flush batch
                if len(batch_points) >= batch_size:
                    client.upsert(collection_name=args.collection, points=batch_points)
                    upserted += len(batch_points)
                    print(f"    Synced {upserted} / {len(all_to_upsert)} files...")
                    batch_points = []

            except Exception as e:
                errors += 1
                print(f"    ✗ {os.path.basename(full_path)}: {e}")

        # Flush remaining
        if batch_points:
            client.upsert(collection_name=args.collection, points=batch_points)
            upserted += len(batch_points)

    # ── Delete removed files ───────────────────────────────────────────────
    deleted_count = 0
    if deleted_files:
        print(f"\n  Removing {len(deleted_files)} deleted files from Qdrant...")
        ids_to_delete = [file_id(p) for p in deleted_files]

        try:
            client.delete(collection_name=args.collection, points_selector=ids_to_delete)
            deleted_count = len(ids_to_delete)
        except Exception as e:
            errors += 1
            print(f"    ✗ Bulk delete failed: {e}")

    # ── Update state ───────────────────────────────────────────────────────
    state["files"] = {p: m for p, m in current_files.items()}
    state["last_sync"] = now
    state["last_sync_dt"] = now_dt.isoformat()
    save_state(state)

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n  ════════════════════════════════════════")
    print(f"  ✓ Sync complete!")
    print(f"    Upserted:  {upserted}")
    print(f"    Deleted:   {deleted_count}")
    print(f"    Errors:    {errors}")
    print(f"    State saved to: {STATE_FILE}")
    print(f"  ════════════════════════════════════════\n")

    # ── Write log ──────────────────────────────────────────────────────────
    log_file = os.path.join(LOG_DIR, "sync_changes.log")
    with open(log_file, "a") as lf:
        lf.write(f"{now_dt.isoformat()} | window={hours:.0f}h | "
                 f"upserted={upserted} deleted={deleted_count} errors={errors}\n")

    if args.json:
        print(json.dumps({
            "upserted": upserted,
            "deleted": deleted_count,
            "errors": errors,
            "hours": hours,
            "new_files": len(new_files),
            "modified_files": len(modified_files),
        }))


if __name__ == "__main__":
    main()
