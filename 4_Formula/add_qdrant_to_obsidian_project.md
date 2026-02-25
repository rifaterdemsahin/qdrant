[[vector db]] [[ai keys]]

# How to Add Vector Search to Any New Project

> Copy-paste the prompts below into Claude Code (or any AI assistant) inside your new project folder. Each prompt is self-contained and builds on the previous step.

---

## What This Skill Does

Adds a **local semantic search engine** to any project:
- Qdrant vector database (stores embeddings)
- sentence-transformers (fast local CPU embedding, no API key needed)
- Indexes all your markdown/text files in ~1 minute
- Returns the most semantically relevant files for any natural language query

**Stack**: Docker + Qdrant + Python sentence-transformers + all-MiniLM-L6-v2

---

## Prompt 1 — Create the Docker Compose File

```
Create a docker-compose.yaml file in the root of this project that runs:
- Qdrant vector database on ports 6333 (REST) and 6334 (gRPC) with a named volume for persistence
- Ollama on port 11434 with a named volume for models
Both with restart: unless-stopped and a healthcheck on Qdrant.
Then run: docker compose up -d
If port 6333 is already in use by a standalone qdrant container, stop it first with: docker stop qdrant
Verify both are healthy with docker compose ps and curl http://localhost:6333/healthz
```

---

## Prompt 2 — Create the Indexer Script

```
Create index_vault.py in the root of this project.
It should:
- Use sentence-transformers with model "all-MiniLM-L6-v2" (384-dim, no API key needed)
- Scan all .md files under [YOUR_FOLDER_PATH] recursively, skipping sidecar and empty files
- Embed them in batches of 64
- Upsert into Qdrant collection "projectname" (384-dim cosine) in batches of 200
- Show a verbose progress bar with: % done, file count, files/sec, ETA, current filename, error count
- Skip files matching *sidecar* and *.excalidraw.md
- Store payload: file path, filename, parent folder, indexed timestamp

Also create a requirements.txt with: sentence-transformers, qdrant-client (optional)

Then run it and show me the output.
```

---

## Prompt 3 — Create a Semantic Search Script

```
Create search_vault.py in the root of this project.
It should:
- Accept a search query as a command-line argument (or prompt if none given)
- Embed the query using sentence-transformers "all-MiniLM-L6-v2"
- Search Qdrant collection "projectname" for top 10 results
- Print results as: rank, score (2 decimal), filename, full file path
- Show a separator line between results for readability

Example usage:
  python3 search_vault.py "how to manage projects with deadlines"
```

---

## Prompt 4 — Update the Project README

```
Update the README (or create secondbrain/3_Resources_Constraints/[topic]/readme.md) with:

### Vector Search Setup
Step 1 — Start stack: docker compose up -d (stop existing qdrant if port conflict)
Step 2 — Install deps: pip3 install sentence-transformers --break-system-packages
Step 3 — Index: python3 index_vault.py
Step 4 — Search: python3 search_vault.py "your query here"

Include the confirmed run stats: files indexed, time elapsed, avg speed.
Note the known issues: port conflict fix, version warning, CPU worker limits.
Add a Teardown section: docker compose down / docker compose down -v
```

---

## Prompt 5 — Add to CLAUDE.md (Persistent Memory)

```
Add a section to CLAUDE.md called "## Vector Search" that documents:
- The docker-compose.yaml location and how to start it
- The index_vault.py command to reindex
- The search_vault.py command to query
- The Qdrant collection name used
- The embedding model name: all-MiniLM-L6-v2 (384-dim)
- Re-indexing is idempotent (safe to re-run, overwrites same IDs)
```

---

## Reusable Files — Copy These Directly

### `docker-compose.yaml`
Reference: `/Users/rifaterdemsahin/projects/secondbrain/docker-compose.yaml`

Key settings to change per project:
- Container names: `secondbrain-qdrant` → `myproject-qdrant`
- Volume names: `qdrant_storage` → `myproject_qdrant_storage`

### `index_vault.py`
Reference: `/Users/rifaterdemsahin/projects/secondbrain/secondbrain/3_Resources_Constraints/qdrant/index_vault.py`

Key settings to change per project (top of file):
```python
VAULT       = "/path/to/your/project/content"
COLLECTION  = "your_project_name"
START_ID    = 1
```

### `embed_notes.sh` (simple bash fallback)
Reference: `/Users/rifaterdemsahin/projects/secondbrain/secondbrain/3_Resources_Constraints/qdrant/embed_notes.sh`
Use only for small vaults (<500 files). For large vaults use `index_vault.py`.

---

## Dependency Install (one-time per machine)

```bash
pip3 install sentence-transformers --break-system-packages
pip3 install einops --break-system-packages   # needed for nomic models only
```

---

## Troubleshooting Cheatsheet

| Problem | Fix |
|---------|-----|
| Port 6333 already allocated | `docker stop qdrant && docker compose up -d` |
| `version` obsolete warning | Remove `version: "3.9"` from docker-compose.yaml |
| Ollama DNS timeout on pull | Network blip — retry `docker compose up -d` |
| sentence-transformers not found | `pip3 install sentence-transformers --break-system-packages` |
| Dim mismatch on upsert | Collection was created with wrong size — script auto-detects and recreates |
| `einops` missing | `pip3 install einops --break-system-packages` (nomic models only) |
| Search returns no results | Run `index_vault.py` first — collection may be empty |

---

## What Was Learned Building This (2026-02-25)

- **Ollama embedding speed**: ~0.2 files/sec on CPU — unusable for large vaults
- **sentence-transformers speed**: ~370 files/sec on Apple Silicon CPU — 1,800x faster
- **all-MiniLM-L6-v2** needs no custom code, no extra deps, works immediately
- **nomic-embed-text** needs `einops` and `trust_remote_code=True`
- **Batch size 64** for embedding + **batch 200** for Qdrant upsert is the sweet spot
- **28,204 files** in vault — 4,293 sidecars filtered, 23,911 indexed in 64 seconds
- Port conflicts happen when a standalone `qdrant` container pre-exists the compose stack

---

## Full Prompt (Single Shot — Advanced)

Use this if you want Claude to set everything up in one go:

```
I want to add semantic vector search to this project.

Please:
1. Create docker-compose.yaml with Qdrant (port 6333/6334) and Ollama (port 11434), named volumes, healthcheck
2. Run docker compose up -d (stop any existing standalone qdrant container first if port is in use)
3. Create index_vault.py using sentence-transformers "all-MiniLM-L6-v2" (384-dim) to index all .md files under [VAULT_PATH] into a Qdrant collection called "[COLLECTION_NAME]" — batch embed 64 files, batch upsert 200 points, show verbose progress bar with %, speed, ETA and current filename, skip sidecar and empty files
4. Create search_vault.py that takes a query string, embeds it, searches Qdrant top-10 and prints ranked results with scores and file paths
5. Copy both scripts into [RESOURCES_FOLDER]
6. Update readme.md in [RESOURCES_FOLDER] with all steps, confirmed run stats, known issues and teardown instructions
7. Run the indexer and show me the verbose output

Use sentence-transformers (local, no API key) not Ollama for embedding — it's 1800x faster on CPU.
Qdrant collection dims: 384. Model: all-MiniLM-L6-v2.
```

---
