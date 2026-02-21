# 6_Semblance — Error Logs and Solutions

---

## Error: `pipeline is not defined` / Model failed to load

**Symptom**
```
ReferenceError: pipeline is not defined
```
or the status bar shows: `Model failed to load`

**Root cause**
`@xenova/transformers` is an ES module. Loading it with a plain `<script src>` tag does **not** expose `pipeline` as a global variable. The old code did:

```html
<!-- WRONG — pipeline is NOT a global after this -->
<script src="https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1"></script>
<script>
  extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2'); // ReferenceError
</script>
```

**Fix**
Use `<script type="module">` and ES module `import`:

```html
<!-- CORRECT -->
<script type="module">
  import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/transformers.min.js';
  env.allowLocalModels = false;
  const extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
</script>
```

**File fixed:** `5_Symbols/search.html`

---

## Error: `client.search() AttributeError`

**Symptom**
```
AttributeError: 'QdrantClient' object has no attribute 'search'
```

**Root cause**
`qdrant-client >= 1.7` removed the `search()` method.

**Fix**
```python
# Old (removed)
results = client.search(collection_name=COLL, query_vector=vec, limit=5)

# New
resp    = client.query_points(collection_name=COLL, query=vec, limit=5, with_payload=True)
results = resp.points
```

**Files fixed:** `5_Symbols/ingest.py`, `5_Symbols/ingest_test.py`, `4_Formula/populate_qdrant.md`

---

## Error: Qdrant REST endpoint `/points/search` returns 404 or wrong format

**Symptom**
Browser fetch to `/collections/{name}/points/search` returns 404 or empty results.

**Root cause**
Qdrant ≥ 1.10 deprecated `/points/search` in favour of `/points/query`.

**Fix**
```js
// Old
fetch(`.../points/search`, { body: JSON.stringify({ vector: vec, limit: 10 }) })

// New
fetch(`.../points/query`, { body: JSON.stringify({ query: vec, limit: 10, with_payload: true }) })
// response: json.result.points  (not json.result directly)
```

---

## Error: Mixed content blocked

**Symptom**
```
Mixed Content: The page at 'https://...' was loaded over HTTPS,
but requested an insecure resource 'http://192.168.2.227:6333/...'
```

**Root cause**
GitHub Pages serves over HTTPS. Browsers block HTTP requests from HTTPS pages.

**Fix options**
1. Open `index.html` or `5_Symbols/search.html` locally via `http://localhost` (Live Server) or `file://`
2. Put Qdrant behind an HTTPS reverse proxy (nginx + Let's Encrypt)
3. Use a local tunnel: `ngrok http 6333`

---

## Error: OOM killed

**Symptom**
Qdrant process killed by Linux OOM killer during ingestion.

**Root cause**
Default config loads all vectors into RAM. 28k × 384-dim floats ≈ 43 MB for vectors alone, but HNSW graph overhead multiplies this.

**Fix**
```yaml
# config.yaml — add to Qdrant config
storage:
  on_disk_payload: true

hnsw_index:
  on_disk: true
```

Or set per-collection at creation time:
```bash
curl -X PUT http://192.168.2.227:6333/collections/mac_repo_index \
  -H 'Content-Type: application/json' \
  -d '{"vectors": {"size": 384, "distance": "Cosine", "on_disk": true}}'
```

---

## Error: Slow indexing on Proxmox ZFS

**Symptom**
Ingest throughput drops to < 5 files/sec on ZFS-backed storage.

**Root cause**
ZFS default `recordsize=128k` causes write amplification for Qdrant's small random writes.

**Fix**
```bash
# Set on the ZFS dataset that holds qdrant_storage
zfs set recordsize=16k <pool>/<dataset>
zfs set atime=off      <pool>/<dataset>
```

---

## Error: `Connection refused :6333`

**Symptom**
```
Failed to fetch http://192.168.2.227:6333/healthz
```

**Root cause**
Qdrant service not running, or Proxmox firewall blocking port 6333.

**Checklist**
```bash
# On Proxmox host
pct list                       # verify LXC is running

# Inside the LXC
systemctl status qdrant        # if installed as service
docker ps | grep qdrant        # if running via Docker

# Firewall
iptables -L INPUT | grep 6333
```
