# Windows Environment Setup for Qdrant

> Development workstation that connects to the Qdrant instance on Proxmox.  
> Qdrant endpoint: `http://192.168.2.227:6333`

---

## Prerequisites

| Component          | Requirement                     | Notes                                        |
|--------------------|---------------------------------|----------------------------------------------|
| OS                 | Windows 10/11                   | WSL2 optional but not required               |
| Python             | 3.10+                           | For embedding generation and ingestion       |
| Git                | Latest                          | To manage the 25 GB second brain repo        |
| Network            | Same LAN as Proxmox host        | Must reach `192.168.2.227:6333`              |
| RAM                | 8 GB+ free                      | For sentence-transformers model loading      |
| GPU (optional)     | NVIDIA CUDA-capable             | Speeds up embedding generation significantly |

---

## Step 1: Verify Network Connectivity

Open **PowerShell** or **Command Prompt**:

```powershell
# Ping the Proxmox LXC
ping 192.168.2.227

# Test Qdrant REST API
curl http://192.168.2.227:6333/healthz

# Open Dashboard in browser
Start-Process "http://192.168.2.227:6333/dashboard"
```

If ping fails, check:
- Proxmox firewall (port 6333 must be open)
- Windows Firewall (outbound is usually allowed)
- Both machines on the same subnet (`192.168.2.x`)

---

## Step 2: Install Python & Dependencies

### Option A: System Python

Download from [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install.

```powershell
python --version
```

### Option B: Conda / Miniconda

```powershell
# Download and install Miniconda
winget install Anaconda.Miniconda3

conda create -n qdrant python=3.11 -y
conda activate qdrant
```

### Install Packages

```powershell
pip install qdrant-client sentence-transformers pathlib2
```

---

## Step 3: Configure Environment Variables

Create a `.env` file in your project root (this file is gitignored):

```ini
# .env — Windows workstation config
QDRANT_HOST=192.168.2.227
QDRANT_PORT=6333
QDRANT_COLLECTION=mac_repo_index
EMBEDDING_MODEL=all-MiniLM-L6-v2
SECOND_BRAIN_PATH=C:\Users\YourName\second-brain
```

Load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()
QDRANT_HOST = os.getenv("QDRANT_HOST", "192.168.2.227")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
```

Or install python-dotenv:

```powershell
pip install python-dotenv
```

---

## Step 4: Daily Ingestion Script

Save as `daily_ingest_windows.py`:

```python
"""
Daily ingestion script for Windows workstation.
Scans the second brain repo for new/modified markdown files
and upserts their embeddings to Qdrant on Proxmox.
"""

import os
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# ── Configuration ──────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "192.168.2.227")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION  = os.getenv("QDRANT_COLLECTION", "mac_repo_index")
MODEL_NAME  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
REPO_PATH   = os.getenv("SECOND_BRAIN_PATH", r"C:\Users\YourName\second-brain")
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

```powershell
# Daily (only files modified in last 24h)
python daily_ingest_windows.py

# Full re-index
python daily_ingest_windows.py --full
```

---

## Step 5: Scheduled Task (Automatic Daily Ingest)

Open **Task Scheduler** (`taskschd.msc`):

1. **Create Basic Task** → Name: `Qdrant Daily Ingest`
2. **Trigger** → Daily, e.g., 02:00 AM
3. **Action** → Start a Program:
   - Program: `python` (or full path `C:\Users\...\python.exe`)
   - Arguments: `C:\path\to\daily_ingest_windows.py`
   - Start in: `C:\path\to\project`
4. **Finish**

Or via PowerShell:

```powershell
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "C:\path\to\daily_ingest_windows.py" `
    -WorkingDirectory "C:\path\to\project"

$trigger = New-ScheduledTaskTrigger -Daily -At 2am

Register-ScheduledTask `
    -TaskName "QdrantDailyIngest" `
    -Action $action `
    -Trigger $trigger `
    -Description "Ingest new markdown files into Qdrant"
```

---

## Step 6: Quick Search Test

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

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Connection refused` | Qdrant down or firewall | Check `curl http://192.168.2.227:6333/healthz` |
| `pip install` fails | No Python in PATH | Reinstall Python, check "Add to PATH" |
| Slow embedding | CPU-only inference | Install `pip install torch` with CUDA support |
| WSL2 RAM bloat | WSL2 takes all available RAM | Create `.wslconfig` with `memory=8GB` limit |
| `UnicodeDecodeError` | Binary files in repo | Use `errors="ignore"` in `read_text()` |
| `timeout` on upsert | Large batch or slow network | Increase `timeout=60` in QdrantClient |
