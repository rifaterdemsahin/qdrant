# Embed Qdrant Search into Obsidian

> **URL**: `http://127.0.0.1:5500/5_Symbols/search.html`  
> Embed the live semantic search page directly inside Obsidian as a sidebar, tab, or inline iframe.

---

## Method 1 — Custom Frames Plugin (Recommended)

The **Custom Frames** community plugin embeds any URL as an Obsidian pane.

### Step-by-Step

1. **Open Obsidian Settings**
   - `Cmd + ,` (macOS) or `Ctrl + ,` (Windows)

2. **Install Custom Frames**
   - Settings → **Community Plugins** → **Browse**
   - Search: `Custom Frames`
   - Click **Install** → **Enable**

3. **Add the Qdrant Search Frame**
   - Settings → **Custom Frames** → scroll down → **Add Frame**
   - Fill in:

   | Field | Value |
   |-------|-------|
   | **Display Name** | `Qdrant Search` |
   | **URL** | `http://127.0.0.1:5500/5_Symbols/search.html` |
   | **Icon** | `search` |
   | **Add Ribbon Icon** | ✅ Enabled |
   | **Open In** | `Center` or `Right sidebar` |
   | **Padding** | `0` |

   ![Custom Frames Settings](../3_Simulation/qdrant_console_run.png)

4. **Open the Search Pane**
   - **Option A**: Click the 🔍 ribbon icon (left sidebar)
   - **Option B**: Command Palette (`Cmd+P`) → type `Custom Frames: Open Qdrant Search`
   - **Option C**: Assign a hotkey in Settings → Hotkeys → search `Qdrant Search`

5. **Pin it** (optional)
   - Right-click the tab → **Pin** to keep it always visible in the sidebar

### Result

The Qdrant semantic search UI loads inside Obsidian with full functionality:
- Transformers.js runs in-browser (no server needed for embedding)
- Results show filename, path, and similarity score
- Collection selector auto-populates from Qdrant

---

## Method 2 — Inline Iframe in a Note

Embed the search directly inside any Obsidian markdown note using an HTML iframe block.

### Create a Note

Create a note called `Qdrant Search.md` in your vault with this content:

```markdown
# 🔍 Qdrant Semantic Search

<iframe 
  src="http://127.0.0.1:5500/5_Symbols/search.html" 
  width="100%" 
  height="700" 
  style="border: none; border-radius: 8px;"
  allow="clipboard-write"
></iframe>
```

### Enable HTML in Obsidian

For the iframe to render:

1. Settings → **Editor** → scroll to **Security**
2. ✅ Enable: **Allow inline HTML** (may be listed under "Strict mode" — disable strict mode)

> **Note**: In Obsidian, iframes work in **Reading View** (not Live Preview / Edit mode). Switch to Reading View with `Cmd+E`.

### Pin as a Permanent Tab

- Open the note → right-click tab → **Pin**
- Or drag it to the right sidebar for always-on access

---

## Method 3 — Surfing Plugin (Built-in Browser)

The **Surfing** plugin adds a full web browser tab inside Obsidian.

1. Install: Community Plugins → Browse → `Surfing` → Install → Enable
2. Command Palette → `Surfing: Open URL`
3. Enter: `http://127.0.0.1:5500/5_Symbols/search.html`
4. Bookmark it for quick access

---

## Prerequisites

### Ensure the Live Server is Running

The URL `http://127.0.0.1:5500` requires VS Code's **Live Server** extension (or equivalent) to be running:

```bash
# Option A: VS Code Live Server
# Right-click index.html → "Open with Live Server"
# Default port: 5500

# Option B: Python simple server on port 5500
cd /Users/rifaterdemsahin/projects/qdrant
python3 -m http.server 5500

# Option C: Node.js
npx serve -p 5500 /Users/rifaterdemsahin/projects/qdrant
```

### Auto-Start on Login (launchd)

To keep the server always available:

```xml
<!-- ~/Library/LaunchAgents/com.qdrant.liveserver.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.qdrant.liveserver</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>-m</string>
    <string>http.server</string>
    <string>5500</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/rifaterdemsahin/projects/qdrant</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/qdrant-liveserver.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/qdrant-liveserver.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.qdrant.liveserver.plist
```

---

## Verify It Works

| Check | Command / Action |
|-------|------------------|
| Server running? | `curl -s http://127.0.0.1:5500/5_Symbols/search.html \| head -5` |
| Qdrant reachable? | `curl -s http://192.168.2.227:6333/healthz` |
| Obsidian iframe? | Open `Qdrant Search.md` → switch to Reading View |
| Custom Frames? | Command Palette → `Custom Frames: Open Qdrant Search` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Blank iframe in Obsidian | Switch to **Reading View** (`Cmd+E`) — iframes don't render in edit mode |
| "Refused to connect" | Server not running — start Live Server or `python3 -m http.server 5500` |
| CORS errors in console | The search.html already has CORS headers; ensure Qdrant allows cross-origin (default: yes) |
| Slow first search | Transformers.js downloads the model (~30 MB) on first use; cached after that |
| Custom Frames shows blank | Check URL is exactly `http://127.0.0.1:5500/5_Symbols/search.html` (no trailing slash issues) |
| Want to use a different port | Update the URL in Custom Frames settings and the server start command |

---

## Quick Reference

```
┌─────────────────────────────────────────────────┐
│  Obsidian                                       │
│                                                 │
│  ┌───────────┐  ┌────────────────────────────┐  │
│  │ File tree │  │ Custom Frames / iframe     │  │
│  │           │  │                            │  │
│  │ notes/    │  │  ┌──────────────────────┐  │  │
│  │ archive/  │  │  │  search.html         │  │  │
│  │ ...       │  │  │  127.0.0.1:5500      │  │  │
│  │           │  │  │                      │  │  │
│  │           │  │  │  🔍 Query box        │  │  │
│  │           │  │  │  📊 Results          │  │  │
│  │           │  │  │                      │  │  │
│  │           │  │  └──────────┬───────────┘  │  │
│  └───────────┘  └────────────┼───────────────┘  │
│                              │                  │
└──────────────────────────────┼──────────────────┘
                               │ fetch()
                    ┌──────────▼──────────┐
                    │  Qdrant             │
                    │  192.168.2.227:6333 │
                    │  mac_repo_index     │
                    └─────────────────────┘
```
