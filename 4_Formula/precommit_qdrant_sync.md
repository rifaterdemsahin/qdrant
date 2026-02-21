# Formula: Pre-Commit Hook — Obsidian → Qdrant Sync

> Every time you commit in your second brain (Obsidian vault), the changed/new
> markdown files are automatically embedded and pushed to Qdrant on Proxmox.
>
> **No manual ingest step needed.** Edit in Obsidian → `git commit` → Qdrant is updated.

---

## How It Works

```
┌──────────────┐    git commit    ┌──────────────────┐    REST :6333    ┌──────────────┐
│   Obsidian   │ ──────────────▶ │  pre-commit hook  │ ──────────────▶ │  Qdrant DB   │
│  (edit .md)  │                  │  embed + upsert   │                  │  Proxmox LXC │
└──────────────┘                  └──────────────────┘                  └──────────────┘
```

1. You edit notes in Obsidian (or any editor) inside your second brain repo
2. You run `git add . && git commit -m "..."` 
3. Git fires the **pre-commit hook** before finalizing the commit
4. The hook detects which `.md` files are staged (new or modified)
5. For each changed file, it generates a 384-dim embedding using `all-MiniLM-L6-v2`
6. It upserts the vector + metadata to Qdrant at `192.168.2.227:6333`
7. The commit proceeds normally

---

## Prerequisites

The Python venv with `qdrant-client` and `sentence-transformers` must exist.
If you haven't set it up yet, run this once:

```bash
cd /Users/rifaterdemsahin/projects/qdrant
python3 -m venv venv
source venv/bin/activate
pip install qdrant-client sentence-transformers
```

Verify Qdrant is reachable:

```bash
curl -s http://192.168.2.227:6333/healthz && echo " OK"
```

---

## Step 1 — Install the Hook Script

The hook lives at `5_Symbols/pre_commit_qdrant_sync.py`. Copy it into your
second brain repo's git hooks directory:

### macOS

```bash
# Copy the Python sync script to somewhere accessible
cp /Users/rifaterdemsahin/projects/qdrant/5_Symbols/pre_commit_qdrant_sync.py \
   /Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre_commit_qdrant_sync.py
```

Then **append** the Qdrant sync call to the existing pre-commit hook
(which already handles auto-archiving):

```bash
cat >> /Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre-commit << 'HOOK'

# ── Qdrant Sync: embed changed .md files and push to Proxmox ──
echo ""
echo "🔍 Syncing changed markdown files to Qdrant..."

QDRANT_VENV="/Users/rifaterdemsahin/projects/qdrant/venv/bin/python"
SYNC_SCRIPT="/Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre_commit_qdrant_sync.py"

if [ -x "$QDRANT_VENV" ] && [ -f "$SYNC_SCRIPT" ]; then
    "$QDRANT_VENV" "$SYNC_SCRIPT"
    echo "✅ Qdrant sync complete"
else
    echo "⚠️  Qdrant sync skipped (venv or script not found)"
fi
HOOK
```

Make sure the hook is executable:

```bash
chmod +x /Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre-commit
```

### Windows (Git Bash)

```bash
# Copy script
cp /c/Users/rifaterdemsahin/projects/qdrant/5_Symbols/pre_commit_qdrant_sync.py \
   /c/Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre_commit_qdrant_sync.py

# Append to pre-commit hook
cat >> /c/Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre-commit << 'HOOK'

# ── Qdrant Sync ──
echo ""
echo "🔍 Syncing changed markdown files to Qdrant..."

QDRANT_VENV="/c/Users/rifaterdemsahin/projects/qdrant/venv/Scripts/python.exe"
SYNC_SCRIPT="/c/Users/rifaterdemsahin/projects/secondbrain/.git/hooks/pre_commit_qdrant_sync.py"

if [ -f "$QDRANT_VENV" ] && [ -f "$SYNC_SCRIPT" ]; then
    "$QDRANT_VENV" "$SYNC_SCRIPT"
    echo "✅ Qdrant sync complete"
else
    echo "⚠️  Qdrant sync skipped (venv or script not found)"
fi
HOOK
```

---

## Step 2 — The Sync Script

The script `5_Symbols/pre_commit_qdrant_sync.py` does the following:

1. Runs `git diff --cached --name-only` to find staged `.md` files
2. Reads each file and generates an embedding
3. Upserts to Qdrant with the same deterministic ID as the full ingest
4. If Qdrant is unreachable, it warns but **does not block** the commit

Key design choices:
- **Same ID formula** as `ingest.py` — so re-indexing the same file overwrites cleanly
- **Non-blocking** — if Qdrant is down, the commit still goes through
- **Fast** — only processes changed files, not the entire 28,000-file repo

---

## Step 3 — Test It

```bash
cd /Users/rifaterdemsahin/projects/secondbrain

# Edit a note in Obsidian (or via terminal)
echo "# Test Note\nThis is a pre-commit hook test." > test_hook_note.md

# Stage and commit
git add test_hook_note.md
git commit -m "test: pre-commit qdrant sync"
```

You should see output like:

```
🗂️  Auto-archiving loose files...
✅ Auto-archival complete - moved files to ...

🔍 Syncing changed markdown files to Qdrant...
  [pre-commit-sync] 1 staged .md file(s) to process
  ✓ test_hook_note.md (score: upserted)
  [pre-commit-sync] Done: 1 synced, 0 errors
✅ Qdrant sync complete

[main abc1234] test: pre-commit qdrant sync
 1 file changed, 2 insertions(+)
```

Then verify in Qdrant:

```bash
curl -s http://192.168.2.227:6333/collections/mac_repo_index | python3 -m json.tool | grep points_count
```

---

## Step 4 — Verify Deleted Files Are Handled

When you delete a markdown file and commit, the hook detects it and removes the
corresponding vector from Qdrant:

```bash
rm test_hook_note.md
git add -A
git commit -m "cleanup: remove test note"
```

Expected output:

```
🔍 Syncing changed markdown files to Qdrant...
  [pre-commit-sync] 1 deleted .md file(s) to remove from Qdrant
  ✗ test_hook_note.md (deleted from Qdrant)
```

---

## How It Fits with the Existing Hooks

Your second brain repo already has a pre-commit hook that auto-archives loose
files into `secondbrain/4_Archieve/YYYY/MM/DD/`. The Qdrant sync runs **after**
that archival step, so the flow is:

```
git commit
  │
  ├─ 1. Auto-archive loose files (existing hook)
  │     └─ moves .md/.png from root → 4_Archieve/
  │
  ├─ 2. Qdrant sync (new addition)
  │     └─ embeds staged .md files → upserts to Proxmox
  │
  └─ 3. Commit finalizes
```

---

## Configuration

All config is at the top of `pre_commit_qdrant_sync.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LXC_IP` | `192.168.2.227` | Proxmox Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant REST API port |
| `COLLECTION` | `mac_repo_index` | Target collection name |
| `MODEL_NAME` | `all-MiniLM-L6-v2` | Embedding model (384-dim) |
| `MAX_TEXT_LEN` | `8000` | Max chars per file to embed |
| `BLOCK_ON_FAILURE` | `False` | If `True`, commit fails when Qdrant is unreachable |

---

## Disabling Temporarily

To skip the Qdrant sync for a single commit:

```bash
git commit --no-verify -m "quick fix, skip hooks"
```

To disable permanently, remove the Qdrant block from the pre-commit hook or
delete the sync script.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `⚠️ Qdrant sync skipped` | venv or script not found | Check paths in the hook match your setup |
| `Connection refused` | Qdrant or Proxmox down | Start the LXC, check `docker ps` |
| Slow commit (30s+) | Model loading on first run | Normal for first commit; subsequent runs use cached model |
| `ModuleNotFoundError` | Wrong Python / missing packages | Ensure hook points to the venv Python, not system Python |
| Hook not running | Not executable | `chmod +x .git/hooks/pre-commit` |
