# Formula: Populate Qdrant from Mac and Run Semantic Search

> **Target**: Proxmox LXC at `192.168.2.227`, Qdrant on port `6333`
> **Source**: `/Users/rifaterdemsahin/projects/secondbrain/` (markdown files)
> **Model**: `all-MiniLM-L6-v2` (384-dim vectors, runs locally on Mac — no API key needed)

---

## Step 1 — Prepare Your Mac

Open **Terminal** and set up an isolated Python environment.

```bash
# Move to your project folder
mkdir qdrant-sync && cd qdrant-sync

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the necessary tools
pip install qdrant-client sentence-transformers
```

> The first `pip install` will download the `all-MiniLM-L6-v2` model (~90MB) on first run.

---

## Step 2 — Verify Qdrant is Running on Proxmox

Before ingesting, confirm the Qdrant LXC is reachable:

```bash
curl http://192.168.2.227:6333/healthz
```

Expected response: `{"title":"qdrant - vector search engine","version":"..."}` with HTTP 200.

If it fails, check:
- Proxmox LXC is running: `pct list` on the Proxmox shell
- Qdrant service is up: `systemctl status qdrant` inside the LXC
- Port 6333 is open in Proxmox firewall

---

## Step 3 — The Ingest Script

The script lives at `5_Symbols/ingest.py`. It:

1. Connects to Qdrant on the Proxmox LXC
2. Creates the collection if it doesn't exist
3. Walks all `.md` files in your second brain folder
4. Encodes each file as a 384-dim vector using `all-MiniLM-L6-v2` (on your Mac CPU)
5. Pushes the vector + metadata to Proxmox

```python
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
LXC_IP    = "192.168.2.227"
REPO_PATH = "/Users/rifaterdemsahin/projects/secondbrain/"  # trailing slash required
COLLECTION = "mac_repo_index"

# 1. Connect to Qdrant on Proxmox
client = QdrantClient(host=LXC_IP, port=6333)
model  = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Create collection if missing
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

# 3. Walk and ingest all markdown files
print(f"Starting sync to Proxmox at {LXC_IP}...")
count = 0

for root, _, files in os.walk(REPO_PATH):
    for file in files:
        if file.endswith(".md"):
            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    text = f.read()

                vector = model.encode(text).tolist()

                client.upsert(
                    collection_name=COLLECTION,
                    points=[PointStruct(
                        id=count,
                        vector=vector,
                        payload={"filename": file, "path": full_path}
                    )]
                )
                count += 1
                if count % 20 == 0:
                    print(f"Indexed {count} files...")
            except Exception as e:
                print(f"Error with {file}: {e}")

print(f"Done! Total files indexed: {count}")
```

---

## Step 4 — Run the Script

```bash
# From inside qdrant-sync/ with venv active
python 5_Symbols/ingest.py
```

Expected output:

```
Starting sync to Proxmox at 192.168.2.227...
Indexed 20 files...
Indexed 40 files...
...
Done! Total files indexed: 312
```

---

## Step 5 — Verify the Collection

```bash
# Check collection info
curl http://192.168.2.227:6333/collections/mac_repo_index | python3 -m json.tool

# Check point count
curl http://192.168.2.227:6333/collections/mac_repo_index/points/count \
  -X POST -H 'Content-Type: application/json' -d '{}'
```

---

## Step 6 — Run a Semantic Search

```bash
# Encode a query on your Mac and search Qdrant
python3 - <<'EOF'
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

client = QdrantClient(host="192.168.2.227", port=6333)
model  = SentenceTransformer('all-MiniLM-L6-v2')

query  = "how to set up docker on proxmox"
vector = model.encode(query).tolist()

resp = client.query_points(
    collection_name="mac_repo_index",
    query=vector,
    limit=5,
    with_payload=True
)

for r in resp.points:
    print(f"Score: {r.score:.4f} | {r.payload['filename']}")
    print(f"  Path: {r.payload['path']}\n")
EOF
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Connection refused 6333` | Qdrant not running or firewall | `systemctl start qdrant` in LXC; open port in Proxmox |
| `OOM` during ingest | Mac RAM pressure | Process files in batches; reduce `text[:4000]` |
| Slow encoding | Large files, CPU-only | Truncate text: `text = text[:8000]` |
| Duplicate IDs | Re-running script resets `count=0` | Use `uuid` or hash of file path as ID |
| Empty results | Collection empty or wrong collection name | Re-check `curl .../collections` |

---

## Re-sync After Adding Notes

Qdrant `upsert` is idempotent for matching IDs — but since IDs here are sequential integers, re-running will overwrite existing points by position, not by file identity. For a proper delta sync, switch to content-hash IDs:

```python
import hashlib

file_id = int(hashlib.md5(full_path.encode()).hexdigest(), 16) % (10**12)
```

Replace `id=count` with `id=file_id` in `PointStruct`.
