# Obsidian ↔ Qdrant Integration Guide

> Connect your Obsidian vault to the Qdrant vector database on Proxmox (`192.168.2.227:6333`) for semantic search across **28 000+ notes**.

---

## Overview — Three Integration Paths

| # | Method | Effort | Native feel | Requirements |
|---|--------|--------|-------------|--------------|
| **A** | Custom Frames plugin (embed `search.html`) | ⭐ Zero code | Medium — opens as a tab | Obsidian + Custom Frames |
| **B** | Local search server + QuickAdd macro | ⭐⭐ Small script | High — results in a note | Python venv (already set up) |
| **C** | Custom Obsidian plugin | ⭐⭐⭐ Full plugin | Best — command palette, modal | Node.js + Obsidian API |

All three talk to the same Qdrant instance and the same `mac_repo_index` collection.

---

## Option A — Custom Frames (Quickest — 2 minutes)

The **Custom Frames** community plugin lets you embed any web page inside Obsidian as a sidebar or tab.

### Steps

1. **Install the plugin**
   - Settings → Community Plugins → Browse → search **Custom Frames** → Install → Enable.

2. **Add a new frame**
   - Settings → Custom Frames → **Add Frame**
   - **Name**: `Qdrant Search`
   - **URL**: `http://localhost:8111` (local server from Option B) **or** file path to `search.html` if served locally.
   - **Icon**: `search` (optional)
   - Open style: **Sidebar** (recommended) or **Center tab**.

3. **Open it**
   - Command Palette → `Custom Frames: Open Qdrant Search`.
   - Or add a ribbon icon via the plugin settings.

> **Tip**: If you just want to open the file directly, serve it with a one-liner:
> ```bash
> cd /Users/rifaterdemsahin/projects/qdrant && python3 -m http.server 8111
> ```
> Then set the Custom Frames URL to `http://localhost:8111/5_Symbols/search.html`.

---

## Option B — Local Search Server + QuickAdd Macro

A lightweight Python server exposes a `/search` endpoint. Obsidian calls it with a QuickAdd macro and writes results into a note.

### 1. Start the search server

```bash
cd /Users/rifaterdemsahin/projects/qdrant
source venv/bin/activate
python 5_Symbols/qdrant_search_server.py
```

The server runs on `http://localhost:8111` and exposes:

| Endpoint | Method | Body | Returns |
|----------|--------|------|---------|
| `/search` | POST | `{"query": "...", "limit": 10}` | JSON array of results |
| `/health` | GET | — | `{"status": "ok"}` |

Test it:

```bash
curl -s http://localhost:8111/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "docker setup", "limit": 5}' | python3 -m json.tool
```

### 2. Install QuickAdd in Obsidian

- Settings → Community Plugins → Browse → **QuickAdd** → Install → Enable.

### 3. Create a Macro

1. Settings → QuickAdd → **Add Choice** → type `Qdrant Search` → choose **Macro** → click ⚙️.
2. In the macro editor → **Add → User Script**.
3. Create a file `_scripts/qdrant_search.js` in your vault root:

```js
// _scripts/qdrant_search.js  — QuickAdd macro for Qdrant semantic search
module.exports = async (params) => {
  const { quickAddApi } = params;

  const query = await quickAddApi.inputPrompt("🔍 Semantic search");
  if (!query) return;

  const res = await fetch("http://localhost:8111/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit: 10 }),
  });

  if (!res.ok) {
    new Notice("Qdrant search failed — is the server running?");
    return;
  }

  const results = await res.json();

  // Build a markdown note with results
  let md = `# 🔍 Search: ${query}\n\n`;
  md += `> ${results.length} results from Qdrant (${new Date().toLocaleString()})\n\n`;

  for (const r of results) {
    const name = r.filename || "Untitled";
    const score = (r.score * 100).toFixed(1);
    const snippet = (r.text || "").substring(0, 200);
    // Create an Obsidian wiki-link from the filename
    const link = `[[${name.replace(".md", "")}]]`;
    md += `### ${link}  — ${score}%\n`;
    md += `${snippet}...\n\n---\n\n`;
  }

  // Write to a scratch note
  const file = "Qdrant Search Results.md";
  const existing = app.vault.getAbstractFileByPath(file);
  if (existing) {
    await app.vault.modify(existing, md);
  } else {
    await app.vault.create(file, md);
  }
  // Open it
  const created = app.vault.getAbstractFileByPath(file);
  if (created) app.workspace.openLinkText(file, "", true);
};
```

4. Back in the macro editor → point the User Script step to `qdrant_search.js`.
5. Assign a **hotkey** (e.g. `Ctrl+Shift+Q`).

### 4. Auto-start the server (optional — launchd)

```xml
<!-- ~/Library/LaunchAgents/com.qdrant.search-server.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.qdrant.search-server</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/rifaterdemsahin/projects/qdrant/venv/bin/python</string>
    <string>/Users/rifaterdemsahin/projects/qdrant/5_Symbols/qdrant_search_server.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/qdrant-search-server.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/qdrant-search-server.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.qdrant.search-server.plist
```

---

## Option C — Custom Obsidian Plugin

A native plugin that adds a **command-palette action** and a **search modal** inside Obsidian. No external server needed — it calls Qdrant's REST API directly and runs embedding in the browser via Transformers.js.

### Install (development mode)

```bash
# Build the plugin
cd /Users/rifaterdemsahin/projects/qdrant/6_Semblance/obsidian-qdrant-search
npm install && npm run build

# Symlink into your vault
VAULT="$HOME/projects/secondbrain"
mkdir -p "$VAULT/.obsidian/plugins/obsidian-qdrant-search"
cp main.js manifest.json styles.css "$VAULT/.obsidian/plugins/obsidian-qdrant-search/"
```

Then: Settings → Community Plugins → reload → enable **Qdrant Semantic Search**.

### Usage

- **Ctrl+Shift+Q** → opens search modal
- Type a natural-language query → results appear with scores and wiki-links
- Click a result → opens the note in Obsidian

See `6_Semblance/obsidian-qdrant-search/` for the full source code.

---

## Architecture Diagram

```
┌──────────────────────┐
│  Obsidian Vault       │
│  (secondbrain/)       │
│                       │
│  Option A: iframe     │──── Custom Frames → search.html
│  Option B: macro      │──── QuickAdd JS → localhost:8111
│  Option C: plugin     │──── fetch() → Qdrant REST API
└──────────┬────────────┘
           │
     ┌─────▼─────┐      ┌────────────────┐
     │ localhost  │      │ Proxmox LXC    │
     │ :8111      │─────►│ 192.168.2.227  │
     │ (Option B) │      │ Qdrant :6333   │
     └────────────┘      │ mac_repo_index │
                         └────────────────┘
```

---

## Comparison

| Feature | A: Custom Frames | B: Local Server | C: Plugin |
|---------|------------------|-----------------|-----------|
| Setup time | 2 min | 10 min | 20 min |
| Needs server running | Optional | Yes | No |
| Offline capable | No | With Qdrant up | With Qdrant up |
| Results as Obsidian notes | No | Yes (wiki-links) | Yes (wiki-links) |
| Command palette | No | Via QuickAdd | Yes — native |
| Auto-open matched notes | No | Yes | Yes |
| Mobile support | No | No | Partial |

### Recommendation

Start with **Option A** to validate the search experience instantly, then graduate to **Option B** or **C** for a native workflow.

---

## Related Files

| File | Purpose |
|------|---------|
| `5_Symbols/qdrant_search_server.py` | Local REST search server (Option B) |
| `5_Symbols/search.html` | Browser-based search UI |
| `6_Semblance/obsidian-qdrant-search/` | Obsidian plugin source (Option C) |
| `4_Formula/populate_qdrant.md` | How to ingest data |
| `4_Formula/precommit_qdrant_sync.md` | Auto-sync on git commit |
