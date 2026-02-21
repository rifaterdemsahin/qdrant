import {
  App,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
  debounce,
} from "obsidian";

// ── Settings ──────────────────────────────────────────────────────────────────

interface QdrantSearchSettings {
  qdrantUrl: string;
  collection: string;
  searchServerUrl: string;
  useLocalServer: boolean; // true = use Python server, false = use Qdrant REST directly
  resultLimit: number;
}

const DEFAULT_SETTINGS: QdrantSearchSettings = {
  qdrantUrl: "http://192.168.2.227:6333",
  collection: "mac_repo_index",
  searchServerUrl: "http://localhost:8111",
  useLocalServer: true,
  resultLimit: 10,
};

// ── Plugin ────────────────────────────────────────────────────────────────────

export default class QdrantSearchPlugin extends Plugin {
  settings: QdrantSearchSettings = DEFAULT_SETTINGS;

  async onload() {
    await this.loadSettings();

    // Command: open search modal
    this.addCommand({
      id: "open-qdrant-search",
      name: "Semantic search (Qdrant)",
      hotkeys: [{ modifiers: ["Ctrl", "Shift"], key: "q" }],
      callback: () => new QdrantSearchModal(this.app, this).open(),
    });

    // Ribbon icon
    this.addRibbonIcon("search", "Qdrant Search", () => {
      new QdrantSearchModal(this.app, this).open();
    });

    // Settings tab
    this.addSettingTab(new QdrantSettingTab(this.app, this));

    console.log("Qdrant Semantic Search plugin loaded");
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

// ── Search Result Type ────────────────────────────────────────────────────────

interface SearchResult {
  id: number;
  score: number;
  filename: string;
  path: string;
  text: string;
}

// ── Search Modal ──────────────────────────────────────────────────────────────

class QdrantSearchModal extends Modal {
  plugin: QdrantSearchPlugin;
  inputEl: HTMLInputElement;
  resultsEl: HTMLElement;
  statusEl: HTMLElement;

  constructor(app: App, plugin: QdrantSearchPlugin) {
    super(app);
    this.plugin = plugin;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.addClass("qdrant-search-modal");

    // Title
    contentEl.createEl("h2", { text: "🔍 Qdrant Semantic Search" });

    // Status line
    this.statusEl = contentEl.createEl("div", {
      cls: "qdrant-status",
      text: "Type a query and press Enter",
    });

    // Search input
    const inputContainer = contentEl.createDiv({ cls: "qdrant-input-row" });
    this.inputEl = inputContainer.createEl("input", {
      type: "text",
      placeholder: "Search your second brain...",
      cls: "qdrant-search-input",
    });
    this.inputEl.focus();

    const searchBtn = inputContainer.createEl("button", {
      text: "Search",
      cls: "qdrant-search-btn",
    });

    // Results container
    this.resultsEl = contentEl.createDiv({ cls: "qdrant-results" });

    // Event listeners
    this.inputEl.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter") this.doSearch();
    });
    searchBtn.addEventListener("click", () => this.doSearch());
  }

  async doSearch() {
    const query = this.inputEl.value.trim();
    if (!query) return;

    this.statusEl.setText("Searching...");
    this.resultsEl.empty();

    try {
      const results = await this.fetchResults(query);
      this.displayResults(results, query);
    } catch (err: any) {
      this.statusEl.setText(`Error: ${err.message}`);
      new Notice(`Qdrant search failed: ${err.message}`);
    }
  }

  async fetchResults(query: string): Promise<SearchResult[]> {
    const s = this.plugin.settings;

    if (s.useLocalServer) {
      // ── Option B: call the local Python search server ───────────────
      const res = await fetch(`${s.searchServerUrl}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          limit: s.resultLimit,
          collection: s.collection,
        }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      return await res.json();
    } else {
      // ── Direct Qdrant REST (needs Transformers.js or pre-embedded) ──
      // Since Obsidian can't easily run Transformers.js, we use the
      // server for embedding.  If you want fully direct, switch to the
      // local server mode in settings.
      throw new Error(
        "Direct Qdrant mode requires the local search server for embedding. " +
        "Enable 'Use local search server' in settings."
      );
    }
  }

  displayResults(results: SearchResult[], query: string) {
    this.resultsEl.empty();

    if (results.length === 0) {
      this.statusEl.setText("No results found");
      this.resultsEl.createEl("p", {
        text: "Try different keywords or a broader query.",
        cls: "qdrant-empty",
      });
      return;
    }

    this.statusEl.setText(`${results.length} results for "${query}"`);

    for (const r of results) {
      const card = this.resultsEl.createDiv({ cls: "qdrant-result-card" });

      // Title row: filename + score badge
      const titleRow = card.createDiv({ cls: "qdrant-result-title" });
      const nameEl = titleRow.createEl("span", {
        text: r.filename || "Untitled",
        cls: "qdrant-result-name",
      });
      titleRow.createEl("span", {
        text: `${(r.score * 100).toFixed(1)}%`,
        cls: "qdrant-score-badge",
      });

      // Path
      if (r.path) {
        card.createEl("div", {
          text: r.path,
          cls: "qdrant-result-path",
        });
      }

      // Snippet
      if (r.text) {
        const snippet = r.text.length > 250 ? r.text.substring(0, 250) + "..." : r.text;
        card.createEl("div", {
          text: snippet,
          cls: "qdrant-result-snippet",
        });
      }

      // Click to open the file in Obsidian
      card.addEventListener("click", () => this.openResult(r));
    }
  }

  async openResult(result: SearchResult) {
    // Try to find the file in the vault by filename
    const filename = result.filename;
    if (!filename) return;

    // Search for files with matching name
    const files = this.app.vault.getFiles();
    const match = files.find(
      (f: TFile) =>
        f.name === filename || f.path.endsWith(filename)
    );

    if (match) {
      await this.app.workspace.openLinkText(match.path, "", false);
      this.close();
    } else {
      new Notice(`File not found in vault: ${filename}`);
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}

// ── Settings Tab ──────────────────────────────────────────────────────────────

class QdrantSettingTab extends PluginSettingTab {
  plugin: QdrantSearchPlugin;

  constructor(app: App, plugin: QdrantSearchPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "Qdrant Semantic Search Settings" });

    new Setting(containerEl)
      .setName("Qdrant URL")
      .setDesc("Full URL to your Qdrant instance (e.g. http://192.168.2.227:6333)")
      .addText((text) =>
        text
          .setPlaceholder("http://192.168.2.227:6333")
          .setValue(this.plugin.settings.qdrantUrl)
          .onChange(async (value) => {
            this.plugin.settings.qdrantUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Collection name")
      .setDesc("Qdrant collection to search")
      .addText((text) =>
        text
          .setPlaceholder("mac_repo_index")
          .setValue(this.plugin.settings.collection)
          .onChange(async (value) => {
            this.plugin.settings.collection = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Use local search server")
      .setDesc(
        "Use the Python search server (localhost:8111) for embedding. " +
        "Required because Obsidian can't run Transformers.js natively."
      )
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useLocalServer)
          .onChange(async (value) => {
            this.plugin.settings.useLocalServer = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Search server URL")
      .setDesc("URL to the local Python search server")
      .addText((text) =>
        text
          .setPlaceholder("http://localhost:8111")
          .setValue(this.plugin.settings.searchServerUrl)
          .onChange(async (value) => {
            this.plugin.settings.searchServerUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Result limit")
      .setDesc("Maximum number of search results to show")
      .addSlider((slider) =>
        slider
          .setLimits(5, 50, 5)
          .setValue(this.plugin.settings.resultLimit)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.resultLimit = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
