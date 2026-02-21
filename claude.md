# Project: Qdrant on Proxmox for Second Brain Semantic Search

## Goal
Set up a Qdrant vector database on a Proxmox host to enable semantic search across a personal second brain — a 25GB repository of mostly markdown files and images.

## Project Files

| File | Purpose |
|------|---------|
| `simulation_install_logs.md` | Simulated install logs and AI-assisted planning conversations for the Qdrant/Proxmox setup |
| `README.md` | Project overview |

## Stack
- **Hypervisor**: Proxmox (4-core host)
- **Vector DB**: Qdrant (Rust-based, efficient on modest hardware)
- **Use case**: Semantic search over a second brain (markdown notes + images)

## Key Constraints
- 4 CPU cores on the Proxmox host
- RAM is the critical resource — 8–16GB+ recommended for vector storage
- SSD/NVMe storage preferred due to Qdrant's write-heavy indexing
- Qdrant memmap (on-disk) mode needed if RAM is limited

## Workflow
1. Plan and simulate the install (see `simulation_install_logs.md`)
2. Provision a Proxmox VM or LXC container
3. Install and configure Qdrant with memmap storage
4. Ingest second brain content as vector embeddings
5. Query via Qdrant's REST or gRPC API for semantic search
