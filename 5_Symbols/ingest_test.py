"""Smoke test: ingest first 50 .md files, then run a search."""
import os
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

LXC_IP     = "192.168.2.227"
REPO_PATH  = "/Users/rifaterdemsahin/projects/secondbrain/"
COLLECTION = "mac_repo_index"
LIMIT      = 50

client = QdrantClient(host=LXC_IP, port=6333)
model  = SentenceTransformer('all-MiniLM-L6-v2')

if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    print(f"Created collection: {COLLECTION}")
else:
    print(f"Collection exists: {COLLECTION}")

print(f"Ingesting first {LIMIT} files from {REPO_PATH}...")
count = 0
for root, _, files in os.walk(REPO_PATH):
    for file in files:
        if not file.endswith(".md"):
            continue
        full_path = os.path.join(root, file)
        try:
            text = open(full_path, 'r', encoding='utf-8').read()
            file_id = int(hashlib.md5(full_path.encode()).hexdigest(), 16) % (10**12)
            vector  = model.encode(text[:8000]).tolist()
            client.upsert(
                collection_name=COLLECTION,
                points=[PointStruct(
                    id=file_id,
                    vector=vector,
                    payload={"filename": file, "path": full_path}
                )]
            )
            count += 1
            print(f"  [{count:>3}] {file}")
        except Exception as e:
            print(f"  ERROR {file}: {e}")
        if count >= LIMIT:
            break
    if count >= LIMIT:
        break

print(f"\nIngested {count} files. Running search...\n")

# --- Search ---
queries = [
    "how to set up docker",
    "proxmox configuration",
    "second brain note taking",
]

for q in queries:
    vec     = model.encode(q).tolist()
    resp    = client.query_points(collection_name=COLLECTION, query=vec, limit=3, with_payload=True)
    print(f"Query: '{q}'")
    for r in resp.points:
        print(f"  score={r.score:.4f}  {r.payload['filename']}")
    print()
