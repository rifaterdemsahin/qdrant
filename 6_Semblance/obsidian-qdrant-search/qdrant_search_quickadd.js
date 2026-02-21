// _scripts/qdrant_search.js  — QuickAdd macro for Qdrant semantic search
//
// Place this file in your Obsidian vault root at: _scripts/qdrant_search.js
// Then create a QuickAdd macro that points to it.
//
// Requires:
//   1. The local search server running:
//      cd /Users/rifaterdemsahin/projects/qdrant && source venv/bin/activate
//      python 5_Symbols/qdrant_search_server.py
//
//   2. QuickAdd community plugin installed in Obsidian

module.exports = async (params) => {
  const { quickAddApi, app } = params;
  const SERVER = "http://localhost:8111";

  // 1. Prompt for query
  const query = await quickAddApi.inputPrompt("🔍 Semantic search your second brain");
  if (!query) return;

  // 2. Call the search server
  let results;
  try {
    const res = await fetch(`${SERVER}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 10 }),
    });

    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    results = await res.json();
  } catch (err) {
    new Notice(`⚠️ Qdrant search failed: ${err.message}\nIs the server running?`);
    return;
  }

  if (!results.length) {
    new Notice("No results found");
    return;
  }

  // 3. Build markdown results
  const now = new Date().toLocaleString();
  let md = `# 🔍 Search: ${query}\n\n`;
  md += `> ${results.length} results from Qdrant · ${now}\n\n`;

  for (const r of results) {
    const name = (r.filename || "Untitled").replace(/\.md$/, "");
    const score = (r.score * 100).toFixed(1);
    const snippet = (r.text || "").substring(0, 200).replace(/\n/g, " ");
    const link = `[[${name}]]`;

    md += `### ${link}  — ${score}%\n`;
    if (snippet) md += `${snippet}...\n`;
    md += `\n---\n\n`;
  }

  // 4. Write to a scratch note
  const fileName = "Qdrant Search Results.md";
  const existing = app.vault.getAbstractFileByPath(fileName);
  if (existing) {
    await app.vault.modify(existing, md);
  } else {
    await app.vault.create(fileName, md);
  }

  // 5. Open the results note
  const file = app.vault.getAbstractFileByPath(fileName);
  if (file) {
    const leaf = app.workspace.getLeaf(false);
    await leaf.openFile(file);
  }
};
