# Proxmox Environment Setup for Qdrant

> Host environment where the Qdrant vector database runs.  
> Target IP: `192.168.2.227` | Ports: `6333` (REST), `6334` (gRPC)

---

## Prerequisites

| Component       | Requirement                    | Notes                                         |
|-----------------|--------------------------------|-----------------------------------------------|
| Proxmox VE      | 7.x or 8.x                    | Type-1 hypervisor                             |
| Container Type  | LXC (preferred) or VM         | LXC has near-zero CPU overhead                |
| Template        | Ubuntu 22.04 LTS (standard)   | Minimal template — curl/git need manual install |
| CPU             | 4 cores                       | Maxed during indexing, idle during search      |
| RAM             | 12–32 GB (32 GB recommended)  | Extra RAM → OS page cache → faster queries     |
| Disk            | 50 GB+ SSD/NVMe               | ZFS: use `recordsize=16k`, disable atime       |
| Nesting         | Enabled                       | Required to run Docker inside LXC              |
| Network         | Bridge `vmbr0`, static IP     | Must resolve DNS for apt                       |

---

## Step-by-Step Installation

### 1. Create the LXC Container

In Proxmox web UI (`https://<proxmox-host>:8006`):

1. **Datacenter → local → CT Templates** → Download `ubuntu-22.04-standard`
2. **Create CT**:
   - **Hostname**: `qdrant`
   - **Password**: set a root password
   - **Template**: `ubuntu-22.04-standard_22.04-1_amd64.tar.zst`
   - **Disk**: 50 GB on local-lvm
   - **CPU**: 4 cores
   - **Memory**: 12288 MB (12 GB) — increase to 32768 later
   - **Network**: `vmbr0`, static IP `192.168.2.227/24`, gateway `192.168.2.1`
   - **DNS**: `8.8.8.8` or your local DNS
   - **Options → Features**: ✅ Nesting

3. Click **Finish** → wait for `TASK OK`

### 2. Fix DNS (if `apt update` fails)

If you see `Temporary failure resolving 'archive.ubuntu.com'`:

```bash
# Check current DNS
cat /etc/resolv.conf

# Fix it
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Verify
ping -c 2 archive.ubuntu.com
```

### 3. Install Base Packages

```bash
apt update && apt upgrade -y
apt install -y curl wget htop git nano
```

### 4. Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
docker --version
```

### 5. Launch Qdrant

```bash
mkdir -p /root/qdrant_storage

docker run -d --name qdrant \
    --restart always \
    -p 6333:6333 -p 6334:6334 \
    -v /root/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

### 6. Verify

```bash
# Health check
curl http://localhost:6333/healthz

# Dashboard (from any browser on the network)
# http://192.168.2.227:6333/dashboard

# Collections list
curl http://localhost:6333/collections | python3 -m json.tool
```

---

## Firewall Rules

If the Proxmox firewall is enabled, allow inbound on the LXC:

| Direction | Port | Protocol | Action |
|-----------|------|----------|--------|
| IN        | 6333 | TCP      | ACCEPT |
| IN        | 6334 | TCP      | ACCEPT |
| IN        | 22   | TCP      | ACCEPT |

---

## Qdrant Configuration (Memory-Optimized)

For hosts with ample RAM (32 GB+), keep vectors **in memory** for fastest queries:

```yaml
# /root/qdrant_storage/config/config.yaml
storage:
  storage_path: /qdrant/storage

  # With 64 GB host RAM, keep vectors in memory
  # on_disk_payload: false   # default

  performance:
    max_search_threads: 0    # 0 = use all available cores
```

For **low-RAM** hosts (< 16 GB), enable memmap:

```yaml
storage:
  on_disk_payload: true

hnsw_index:
  on_disk: true
```

After editing, restart:

```bash
docker restart qdrant
```

---

## Maintenance

### Update Qdrant

```bash
docker pull qdrant/qdrant
docker stop qdrant && docker rm qdrant
docker run -d --name qdrant \
    --restart always \
    -p 6333:6333 -p 6334:6334 \
    -v /root/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

### Snapshots (Proxmox)

Before major operations (re-indexing, upgrades):

```bash
# From Proxmox host shell (not inside the LXC)
pct snapshot 103 pre-reindex --description "Before full re-index"

# Rollback if needed
pct rollback 103 pre-reindex
```

### Monitor Resources

```bash
htop                              # CPU/RAM inside LXC
docker stats qdrant               # Container-level stats
du -sh /root/qdrant_storage       # Disk usage
```

---

## Networking Diagram

```
┌──────────────────────────────────────────────────┐
│                  Local Network                    │
│                                                    │
│  ┌─────────────┐         ┌──────────────────────┐ │
│  │  Workstation │ ──────▶ │  Proxmox Host        │ │
│  │  (Win/macOS) │  REST   │  ┌────────────────┐  │ │
│  │  Code + GPU  │  :6333  │  │ LXC 103: qdrant│  │ │
│  └─────────────┘         │  │ 192.168.2.227   │  │ │
│                           │  │ Docker → Qdrant │  │ │
│                           │  └────────────────┘  │ │
│                           └──────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl: command not found` | Minimal template | `apt install curl -y` |
| `Temporary failure resolving` | No DNS configured | Set `nameserver 8.8.8.8` in `/etc/resolv.conf` |
| `Connection refused :6333` | Qdrant not running or firewall | `docker ps`, check Proxmox firewall |
| `OOM killed` | Vectors exceed RAM | Enable `on_disk: true` or increase LXC memory |
| Slow indexing on ZFS | Write amplification | `zfs set recordsize=16k`, disable atime |
| `Disk Full` during ingest | Tombstones + WAL overhead | Resize disk: Proxmox → Resources → Root Disk → Resize |
