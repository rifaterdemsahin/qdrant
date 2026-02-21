# macOS Environment Setup for Qdrant

> Development workstation that connects to the Qdrant instance on Proxmox.  
> Qdrant endpoint: `http://192.168.2.227:6333`

---

## Prerequisites

| Component          | Requirement                     | Notes                                       |
|--------------------|---------------------------------|---------------------------------------------|
| OS                 | macOS 13+ (Ventura/Sonoma)      | Apple Silicon (M1/M2/M3) or Intel           |
| Python             | 3.10+                           | Use Homebrew or pyenv                       |
| Git                | Latest (via Xcode CLI tools)    | `xcode-select --install`                    |
| Homebrew           | Latest                          | Package manager                             |
| Network            | Same LAN as Proxmox host        | Must reach `192.168.2.227:6333`             |
| RAM                | 8 GB+ free                      | For sentence-transformers model loading     |

---

## Step 1: Install Base Tools

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install essentials
brew install python@3.11 git curl htop

# Verify
python3 --version
git --version
```

---

## Step 2: Verify Network Connectivity

```bash
# Ping the Proxmox LXC
ping -c 3 192.168.2.227

# Test Qdrant REST API
curl -s http://192.168.2.227:6333/healthz && echo " OK"

# List collections
curl -s http://192.168.2.227:6333/collections | python3 -m json.tool

# Open Dashboard in browser
open "http://192.168.2.227:6333/dashboard"
```

If ping fails, check:
- Both machines on the same subnet (`192.168.2.x`)
- Proxmox firewall allows port 6333 inbound
- macOS firewall (System Settings → Network → Firewall)

---

## Step 3: Python Virtual Environment

```bash
# Create a project directory
mkdir -p ~/projects/qdrant-client && cd ~/projects/qdrant-client

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install qdrant-client sentence-transformers python-dotenv
```

For **Apple Silicon (M1/M2/M3)** — ensure torch uses MPS acceleration:

```bash
pip install torch torchvision torchaudio
```

Verify MPS is available:

```python
import torch
print(torch.backends.mps.is_available())  # Should print True on Apple Silicon
```

---

## Step 4: Configure Environment Variables

Create a `.env` file in your project root (gitignored):

```ini
# .env — macOS workstation config
QDRANT_HOST=192.168.2.227
QDRANT_PORT=6333
QDRANT_COLLECTION=mac_repo_index
EMBEDDING_MODEL=all-MiniLM-L6-v2
SECOND_BRAIN_PATH=/Users/YourName/second-brain
```

Load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()
QDRANT_HOST = os.getenv("QDRANT_HOST", "192.168.2.227")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
```

---

## Step 5: Daily Ingestion Script

Save as `daily_ingest_macos.py`:

```python
"""
Daily ingestion script for macOS workstation.
Scans the second brain repo for new/modified markdown files
and upserts their embeddings to Qdrant on Proxmox.
"""

import os
import hashlib
import time
from pathlib import Path
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# ── Configuration ──────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "192.168.2.227")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION  = os.getenv("QDRANT_COLLECTION", "mac_repo_index")
MODEL_NAME  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
REPO_PATH   = os.getenv("SECOND_BRAIN_PATH", os.path.expanduser("~/second-brain"))
VECTOR_DIM  = 384  # all-MiniLM-L6-v2 output dimension
MAX_TEXT_LEN = 8000  # Truncate long files

# ── Setup ──────────────────────────────────────────────────
print(f"[{datetime.now()}] Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

print(f"[{datetime.now()}] Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

# Create collection if needed
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    print(f"Created collection: {COLLECTION}")

# ── Ingestion ──────────────────────────────────────────────
def file_id(path: str) -> str:
    """Deterministic ID from file path."""
    return hashlib.md5(path.encode()).hexdigest()

def ingest_file(filepath: Path):
    """Read, embed, and upsert a single file."""
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return False

    vector = model.encode(text[:MAX_TEXT_LEN]).tolist()
    point_id = file_id(str(filepath))

    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "filename": filepath.name,
                "path": str(filepath),
                "title": filepath.stem,
                "size_bytes": filepath.stat().st_size,
                "modified": filepath.stat().st_mtime,
                "ingested_at": datetime.now().isoformat(),
            }
        )]
    )
    return True

def run_ingest(only_recent: bool = True, days: int = 1):
    """Walk the repo and ingest markdown files."""
    repo = Path(REPO_PATH)
    if not repo.exists():
        print(f"ERROR: Repo path does not exist: {REPO_PATH}")
        return

    cutoff = time.time() - (days * 86400) if only_recent else 0
    extensions = {".md", ".txt", ".rst"}

    total, ingested, skipped = 0, 0, 0
    for filepath in repo.rglob("*"):
        if filepath.suffix.lower() not in extensions:
            continue
        if filepath.stat().st_size == 0:
            continue
        total += 1

        if only_recent and filepath.stat().st_mtime < cutoff:
            skipped += 1
            continue

        try:
            if ingest_file(filepath):
                ingested += 1
                print(f"  ✓ {filepath.name}")
        except Exception as e:
            print(f"  ✗ {filepath.name}: {e}")

    print(f"\nDone: {ingested} ingested, {skipped} skipped, {total} total files")

if __name__ == "__main__":
    import sys
    full = "--full" in sys.argv
    run_ingest(only_recent=not full)
```

### Run

```bash
# Activate venv
source .venv/bin/activate

# Daily (only files modified in last 24h)
python daily_ingest_macos.py

# Full re-index
python daily_ingest_macos.py --full
```

---

## Step 6: Automated Daily Ingest (launchd)

macOS uses `launchd` instead of cron. Create a plist:

```bash
cat > ~/Library/LaunchAgents/com.qdrant.daily-ingest.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.qdrant.daily-ingest</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YourName/projects/qdrant-client/.venv/bin/python</string>
        <string>/Users/YourName/projects/qdrant-client/daily_ingest_macos.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YourName/projects/qdrant-client</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/tmp/qdrant-ingest.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/qdrant-ingest-error.log</string>
</dict>
</plist>
EOF
```

Load and enable:

```bash
launchctl load ~/Library/LaunchAgents/com.qdrant.daily-ingest.plist

# Verify it's registered
launchctl list | grep qdrant

# Manual trigger for testing
launchctl start com.qdrant.daily-ingest

# Check logs
tail -f /tmp/qdrant-ingest.log
```

To disable:

```bash
launchctl unload ~/Library/LaunchAgents/com.qdrant.daily-ingest.plist
```

---

## Step 7: Quick Search Test

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient(host="192.168.2.227", port=6333)
model = SentenceTransformer("all-MiniLM-L6-v2")

query = "How to set up Docker on Proxmox"
vector = model.encode(query).tolist()

results = client.search(
    collection_name="mac_repo_index",
    query_vector=vector,
    limit=5,
)

for r in results:
    print(f"{r.score:.4f}  {r.payload.get('filename', '?')}")
```

---

## Apple Silicon Notes

| Topic | Detail |
|-------|--------|
| **MPS Acceleration** | PyTorch 2.0+ supports Metal Performance Shaders for GPU inference on M1/M2/M3 |
| **Rosetta** | If using x86 Python via Rosetta, some packages may be slower — use native arm64 |
| **Memory Pressure** | Monitor in Activity Monitor → Memory tab; macOS swap can mask low-RAM issues |
| **Homebrew path** | Apple Silicon: `/opt/homebrew/bin`; Intel: `/usr/local/bin` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Connection refused` | Qdrant down or firewall | `curl http://192.168.2.227:6333/healthz` |
| `ModuleNotFoundError` | Not in venv | `source .venv/bin/activate` |
| Slow embedding | CPU-only inference | Ensure `torch` with MPS support is installed |
| `Permission denied` on launchd | Plist ownership | `chmod 644` on the plist file |
| `UnicodeDecodeError` | Binary files in repo | Already handled with `errors="ignore"` |
| `timeout` on upsert | Slow network or large batch | Increase `timeout=60` in QdrantClient |
