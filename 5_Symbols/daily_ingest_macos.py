import os
import hashlib
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
LXC_IP     = "192.168.2.227"
REPO_PATH  = "/Users/rifaterdemsahin/projects/secondbrain/"
COLLECTION = "mac_repo_index"
LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), "last_run_macos.txt")

# Get last run time
if os.path.exists(LAST_RUN_FILE):
    with open(LAST_RUN_FILE, 'r') as f:
        last_run = float(f.read().strip())
else:
    last_run = 0

current_time = time.time()

# 1. Connect to Qdrant on Proxmox
client = QdrantClient(host=LXC_IP, port=6333)
model  = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Create collection if missing (384-dim, cosine similarity)
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    print(f"Created collection: {COLLECTION}")
else:
    print(f"Collection exists: {COLLECTION}")

# 3. Walk and ingest markdown files modified since last run
print(f"Starting sync to Proxmox at {LXC_IP}...")
count   = 0
errors  = 0

for root, _, files in os.walk(REPO_PATH):
    for file in files:
        if not file.endswith(".md"):
            continue

        full_path = os.path.join(root, file)
        if os.path.getmtime(full_path) <= last_run:
            continue  # skip if not modified since last run

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                text = f.read()

            # Stable ID from file path so re-runs upsert correctly
            file_id = int(hashlib.md5(full_path.encode()).hexdigest(), 16) % (10**12)

            # Encode locally on Mac (no API key needed)
            vector = model.encode(text[:8000]).tolist()

            client.upsert(
                collection_name=COLLECTION,
                points=[PointStruct(
                    id=file_id,
                    vector=vector,
                    payload={"filename": file, "path": full_path}
                )]
            )
            count += 1
            if count % 20 == 0:
                print(f"Indexed {count} files...")

        except Exception as e:
            errors += 1
            print(f"Error with {file}: {e}")

print(f"Done! Indexed: {count} | Errors: {errors}")

# Update last run time
with open(LAST_RUN_FILE, 'w') as f:
    f.write(str(current_time))