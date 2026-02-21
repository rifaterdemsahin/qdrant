# Qdrant — Second Brain Semantic Search on Proxmox

> Vector DB setup on Proxmox for semantic search across a personal second brain (25GB of markdown + images).
> http://192.168.2.227:6333/dashboard#/welcome
> http://127.0.0.1:5500/5_Symbols/search.html
---

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `1_Real_Unknown` | Goal — the unknown problem to solve |
| `2_Environment` | Read files — roadmap, use cases, environment setup |
| `3_Simulation` | Examples — simulated installs, UI prototypes |
| `4_Formula` | Steps — guides and best practices (GPT-assisted) |
| `5_Symbols` | Code — core source files |
| `6_Semblance` | Errors — error logs and solutions |
| `7_Testing_Known` | Reach back to real proof — validation and acceptance criteria |

---

### 1_Real_Unknown — Objectives (OKRs)

Defines project objectives and key results, starting with the unknown problem.

- **Objective**: Enable fast semantic search across a 25GB second brain (markdown + images) hosted on Proxmox
- **Key Results**: Qdrant running in a Proxmox VM/LXC, embeddings ingested, sub-second query response

---

### 2_Environment — Roadmap and Use Cases

Contains the project roadmap with development phases and detailed use cases.

- Proxmox host spec: 4 cores, SSD storage, 8–16GB RAM
- Qdrant deployment target: VM or LXC container
- Use cases: semantic note search, image similarity, cross-document linking

---

### 3_Simulation — UI and Examples

User interfaces and example workflows. Technologies used: HTML5, CSS3, JavaScript.
See `simulation_install_logs.md` for AI-assisted planning conversations and install simulations.

---

### 4_Formula — Guides and Best Practices

Step-by-step guides for:

- Provisioning the Proxmox VM/LXC
- Installing and configuring Qdrant (memmap mode for RAM-limited hosts)
- Generating and ingesting embeddings
- Querying via Qdrant REST/gRPC API

---

### 5_Symbols — Core Source Code

Main application files including:

- Qdrant configuration (`config.yaml`)
- Embedding pipeline scripts
- Query interface

---

### 6_Semblance — Error Logs and Solutions

Documents common issues, causes, and solutions.
Includes debugging tips and workarounds for Proxmox/Qdrant compatibility edge cases.

---

### 7_Testing_Known — Validation

Contains test plans, validation procedures, and acceptance criteria for ensuring the setup reaches the objectives defined in `1_Real_Unknown`.

- Verify Qdrant API is reachable from the host network
- Confirm embedding ingestion completes without OOM errors
- Validate semantic search returns relevant results from second brain content

---

## Key Files

| File | Description |
|------|-------------|
| `claude.md` | Project context and constraints for AI-assisted development |
| `simulation_install_logs.md` | Simulated install logs and planning conversations |
| `index.html` | Project overview page with PrismJS syntax highlighting |

---

## TTS Cost Tracking

Track token/cost usage at start and end of each session. Run `git pull` before starting and `git push` after each session.
