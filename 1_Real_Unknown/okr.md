# OKR — Objectives and Key Results

> Qdrant on Proxmox for Second Brain Semantic Search

---

## Objective 1: Deploy a production-ready Qdrant vector database on Proxmox

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 1.1 | Qdrant LXC container running on Proxmox | Healthy API on `192.168.2.227:6333` | ✅ Done |
| 1.2 | Docker + Qdrant installed inside LXC | `docker run qdrant/qdrant` with `--restart always` | ✅ Done |
| 1.3 | Persistent storage volume mounted | `/root/qdrant_storage` survives restarts | ✅ Done |
| 1.4 | Firewall rules allow ports 6333 (REST) and 6334 (gRPC) | Workstations can reach the API | ✅ Done |
| 1.5 | DNS resolution fixed in minimal Ubuntu template | `apt update` succeeds, packages installable | ✅ Done |

---

## Objective 2: Ingest the entire 25 GB second brain into Qdrant

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 2.1 | `mac_repo_index` collection created | 384-dim vectors, Cosine distance | ✅ Done |
| 2.2 | Embedding model runs locally (no API key) | `all-MiniLM-L6-v2` on Mac CPU | ✅ Done |
| 2.3 | Full ingestion completes | All `.md` files indexed | ✅ Done — **28,003 files indexed, 2 errors** |
| 2.4 | Deterministic point IDs via MD5 hash | Re-runs upsert (update) instead of duplicate | ✅ Done |
| 2.5 | Payload stores filename and path | Enables result display in search UI | ✅ Done |

---

## Objective 3: Enable semantic search from any workstation

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 3.1 | Browser-based search page (`search.html`) | Client-side embedding via Transformers.js, queries Qdrant REST | ✅ Done |
| 3.2 | Dashboard page (`dashboard.html`) | Live health, collection stats, telemetry from Qdrant | ✅ Done |
| 3.3 | Project home page (`index.html`) | Navigation menu linking Home / Search / Dashboard | ✅ Done |
| 3.4 | Query latency | < 1 second for top-10 results | ✅ Done |
| 3.5 | Collection selector and result limit in search UI | Dynamic dropdown populated from Qdrant `/collections` | ✅ Done |

---

## Objective 4: Automate daily incremental ingestion

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 4.1 | macOS daily ingest script (`daily_ingest_macos.py`) | Only processes files modified since last run | ✅ Done |
| 4.2 | Windows daily ingest script (`daily_ingest_windows.py`) | Same logic, Windows paths | ✅ Done |
| 4.3 | macOS automation via `launchd` | Plist runs daily at 02:00 | 📄 Documented |
| 4.4 | Windows automation via Task Scheduler | Scheduled task runs daily at 02:00 | 📄 Documented |
| 4.5 | Last-run timestamp persisted to file | `last_run_macos.txt` / `last_run_windows.txt` | ✅ Done |

---

## Objective 5: Document the full environment and workflow

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 5.1 | Proxmox environment guide (`env_proxmox.md`) | LXC creation, Docker, Qdrant config, firewall, snapshots | ✅ Done |
| 5.2 | Windows environment guide (`env_windows.md`) | Python setup, `.env`, ingestion, Task Scheduler | ✅ Done |
| 5.3 | macOS environment guide (`env_macos.md`) | Homebrew, venv, MPS acceleration, launchd | ✅ Done |
| 5.4 | Populate formula (`populate_qdrant.md`) | Step-by-step Mac → Proxmox ingest walkthrough | ✅ Done |
| 5.5 | Simulation install logs documented | AI-assisted planning conversation preserved | ✅ Done |

---

## Objective 6: Maintain project quality and best practices

| # | Key Result | Target | Status |
|---|-----------|--------|--------|
| 6.1 | `.gitignore` covers venvs, caches, storage, `.env` | No secrets or large data committed | ✅ Done |
| 6.2 | `robots.txt` in place | Allows crawlers | ✅ Done |
| 6.3 | MIT License | Open-source friendly | ✅ Done |
| 6.4 | Smoke test script (`ingest_test.py`) | Ingest 50 files + run 3 search queries | ✅ Done |
| 6.5 | Simulation screenshots in `3_Simulation/` | Visual proof of working setup | ✅ Done |

---

## Summary

| Metric | Value |
|--------|-------|
| **Total files indexed** | 28,003 |
| **Indexing errors** | 2 |
| **Vector dimensions** | 384 (all-MiniLM-L6-v2) |
| **Distance metric** | Cosine |
| **Collection name** | `mac_repo_index` |
| **Qdrant endpoint** | `http://192.168.2.227:6333` |
| **Proxmox LXC** | ID 103, 4 cores, 12 GB RAM, 50 GB disk |
| **Workstation platforms** | macOS, Windows |
| **Web UI pages** | index.html, search.html, dashboard.html |

---

## Project Structure

```
1_Real_Unknown/     → This OKR file (objectives & key results)
2_Environment/      → Environment guides: Proxmox, Windows, macOS
3_Simulation/       → Screenshots of working Qdrant console & DB
4_Formula/          → Step-by-step populate guide
5_Symbols/          → Source code: ingest, daily ingest, search, dashboard
6_Semblance/        → Error logs and solutions (to be populated)
7_Testing_Known/    → Validation and acceptance criteria (to be populated)
```
