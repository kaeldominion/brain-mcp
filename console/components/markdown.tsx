/** Minimal, dependency-free markdown for vault notes: headings, emphasis,
 *  code, lists, links, wikilinks, tables. Escapes HTML first. */

function esc(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(s: string) {
  return s
    .replace(/`([^`]+)`/g, (_m, c) => `<code>${c}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\*([^*]+)\*/g, "<i>$1</i>")
    .replace(
      /\[\[([^\]]+)\]\]/g,
      (_m, t) => `<a class="wikilink" href="/vault?q=${encodeURIComponent(t)}">${t}</a>`
    )
    .replace(
      /\[([^\]]+)\]\((https?:[^)]+)\)/g,
      '<a class="wikilink" href="$2" target="_blank" rel="noreferrer">$1</a>'
    );
}

export function renderMarkdown(raw: string): string {
  let text = raw.replace(/^---\n[\s\S]*?\n---\n/, ""); // frontmatter off
  const lines = esc(text).split("\n");
  const out: string[] = [];
  let inCode = false, inList = false, inTable = false;

  const closeAll = () => {
    if (inList) { out.push("</ul>"); inList = false; }
    if (inTable) { out.push("</table>"); inTable = false; }
  };

  for (const line of lines) {
    if (line.startsWith("```")) {
      closeAll();
      out.push(inCode ? "</pre>" : "<pre>");
      inCode = !inCode;
      continue;
    }
    if (inCode) { out.push(line); continue; }

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { closeAll(); const l = h[1].length; out.push(`<h${l}>${inline(h[2])}</h${l}>`); continue; }

    if (/^\s*[-*]\s+/.test(line)) {
      if (inTable) { out.push("</table>"); inTable = false; }
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`);
      continue;
    }
    if (/^\|/.test(line)) {
      if (inList) { out.push("</ul>"); inList = false; }
      if (/^\|[\s:-]+\|/.test(line.replace(/\s/g, ""))) continue; // separator row
      if (!inTable) { out.push("<table>"); inTable = true; }
      const cells = line.split("|").slice(1, -1).map((c) => `<td>${inline(c.trim())}</td>`);
      out.push(`<tr>${cells.join("")}</tr>`);
      continue;
    }
    closeAll();
    if (/^(-{3,}|_{3,})$/.test(line.trim())) { out.push("<hr/>"); continue; }
    if (line.trim() === "") continue;
    out.push(`<p>${inline(line)}</p>`);
  }
  closeAll();
  if (inCode) out.push("</pre>");
  return out.join("\n");
}
