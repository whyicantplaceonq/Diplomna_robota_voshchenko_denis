#!/usr/bin/env python3
"""
verse_doc.py — Генератор HTML-документації з Verse-коду (UEFN)

Читає doc-коментарі (## ... ##) з .verse файлів та генерує
структуровану HTML-документацію.

Використання:
    python scripts/verse_doc.py Verse/ -o docs/generated/
"""

import os, re, sys, argparse, shutil
from dataclasses import dataclass, field
from typing import List, Optional

# ── Типи даних ───────────────────────────────────────────────────────────────

@dataclass
class DocTag:
    name: str
    value: str

@dataclass
class DocEntry:
    kind: str           # class | func | field
    name: str
    brief: str = ""
    description: str = ""
    tags: List[DocTag] = field(default_factory=list)
    source_line: int = 0

    def get_tags(self, tag_name):
        return [t for t in self.tags if t.name == tag_name]

    def get_tag(self, tag_name) -> Optional[str]:
        found = self.get_tags(tag_name)
        return found[0].value if found else None

@dataclass
class DocFile:
    filename: str
    filepath: str
    entries: List[DocEntry] = field(default_factory=list)

# ── Парсер doc-коментарів ─────────────────────────────────────────────────────

def parse_doc_comment(block: str) -> dict:
    """Парсить вміст ## ... ## блоку в структуровані дані."""
    result = {"brief": "", "description": [], "tags": []}
    lines = [l.strip().lstrip("# ").rstrip() for l in block.strip().splitlines()]
    lines = [l for l in lines if l != "##"]

    i = 0
    # Перший рядок з @brief або просто текст
    while i < len(lines):
        line = lines[i]
        if line.startswith("@"):
            break
        if line:
            if not result["brief"]:
                result["brief"] = line.lstrip("@brief").strip() if line.startswith("@brief") else line
            else:
                result["description"].append(line)
        i += 1

    # Парсимо теги
    while i < len(lines):
        line = lines[i]
        if line.startswith("@"):
            parts = line[1:].split(None, 1)
            tag_name = parts[0]
            tag_val = parts[1] if len(parts) > 1 else ""
            # Багаторядкові теги
            i += 1
            while i < len(lines) and lines[i] and not lines[i].startswith("@"):
                tag_val += " " + lines[i]
                i += 1
            result["tags"].append(DocTag(name=tag_name, value=tag_val.strip()))
        else:
            if line:
                result["description"].append(line)
            i += 1

    return result


def parse_verse_file(filepath: str) -> DocFile:
    """Читає .verse файл та витягує всі задокументовані елементи."""
    doc_file = DocFile(
        filename=os.path.basename(filepath),
        filepath=filepath
    )

    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()

    # Знаходимо всі блоки ## ... ##
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "##":
            # Збираємо блок до закриваючого ##
            block_lines = [line]
            i += 1
            while i < len(lines):
                bl = lines[i].strip()
                block_lines.append(bl)
                if bl == "##":
                    break
                i += 1

            block_text = "\n".join(block_lines)
            parsed = parse_doc_comment(block_text)

            # Наступний значущий рядок — це сама декларація
            i += 1
            decl_line = ""
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                decl_line = lines[i].strip()

            # Визначаємо тип та ім'я
            kind, name = detect_kind_and_name(parsed, decl_line)

            entry = DocEntry(
                kind=kind,
                name=name,
                brief=parsed["brief"],
                description="\n".join(parsed["description"]),
                tags=parsed["tags"],
                source_line=i + 1,
            )
            doc_file.entries.append(entry)

        i += 1

    return doc_file


def detect_kind_and_name(parsed: dict, decl_line: str) -> tuple:
    """Визначає тип (class/func/field) та ім'я з тегів або декларації."""
    # Пробуємо з тегів
    for tag in parsed["tags"]:
        if tag.name in ("class", "func", "field"):
            return tag.name, tag.value.split()[0] if tag.value else "unknown"

    # Fallback: аналізуємо рядок декларації
    if ":= class" in decl_line:
        m = re.match(r"(\w+)", decl_line)
        return "class", m.group(1) if m else "unknown"
    if "():void=" in decl_line.replace(" ", "") or ")<suspends>:void=" in decl_line.replace(" ", ""):
        m = re.match(r"(\w+)", decl_line)
        return "func", m.group(1) if m else "unknown"
    if "<localizes>" in decl_line:
        m = re.match(r"(\w+)", decl_line)
        return "func", m.group(1) if m else "unknown"

    m = re.match(r"(\w+)", decl_line)
    return "func", m.group(1) if m else "unknown"

# ── HTML генератор ────────────────────────────────────────────────────────────

def render_tags_table(entry: DocEntry) -> str:
    param_tags = entry.get_tags("param")
    other_tags = [(t.name, t.value) for t in entry.tags
                  if t.name not in ("class", "func", "field", "brief", "param")]

    html = ""

    if param_tags:
        html += """<table class="params-table">
<thead><tr><th>Параметр</th><th>Опис</th></tr></thead><tbody>"""
        for t in param_tags:
            parts = t.value.split(None, 1)
            pname = parts[0] if parts else ""
            pdesc = parts[1] if len(parts) > 1 else ""
            html += f"<tr><td><code>{pname}</code></td><td>{pdesc}</td></tr>\n"
        html += "</tbody></table>\n"

    for tname, tval in other_tags:
        badge_class = {
            "suspends": "badge-blue", "returns": "badge-green",
            "algorithm": "badge-purple", "business-logic": "badge-orange",
            "architecture": "badge-teal", "flow": "badge-gray",
            "ui": "badge-pink", "error-handling": "badge-red",
            "see": "badge-gray",
        }.get(tname, "badge-gray")
        label = {
            "suspends": "⏳ Async", "returns": "↩ Returns",
            "algorithm": "⚙ Algorithm", "business-logic": "💼 Business Logic",
            "architecture": "🏗 Architecture", "flow": "🔄 Flow",
            "ui": "🖥 UI", "error-handling": "⚠ Error Handling",
            "see": "👁 See also",
        }.get(tname, f"@{tname}")
        html += f'<div class="tag-block"><span class="badge {badge_class}">{label}</span> <span class="tag-val">{tval}</span></div>\n'

    return html


def generate_html(doc_files: List[DocFile], title: str) -> str:
    classes = [e for df in doc_files for e in df.entries if e.kind == "class"]
    funcs   = [e for df in doc_files for e in df.entries if e.kind == "func"]

    # Sidebar nav
    nav_items = ""
    for df in doc_files:
        nav_items += f'<li class="nav-file">{df.filename}</li>\n'
        for e in df.entries:
            icon = "◆" if e.kind == "class" else "◇"
            nav_items += f'<li><a href="#{e.kind}-{e.name}">{icon} {e.name}</a></li>\n'

    # Stats
    stats_html = f"""
<div class="stats-bar">
  <div class="stat"><div class="stat-val">{sum(len(df.entries) for df in doc_files)}</div><div class="stat-lbl">Documented</div></div>
  <div class="stat"><div class="stat-val">{len(classes)}</div><div class="stat-lbl">Classes</div></div>
  <div class="stat"><div class="stat-val">{len(funcs)}</div><div class="stat-lbl">Functions</div></div>
  <div class="stat"><div class="stat-val">{sum(len(df.entries) for df in doc_files)}</div><div class="stat-lbl">Public APIs</div></div>
</div>"""

    # Content
    content_html = ""
    for df in doc_files:
        content_html += f'<div class="file-section"><h2 class="file-title">📄 {df.filename}</h2>\n'
        for entry in df.entries:
            kind_badge = f'<span class="kind-badge kind-{entry.kind}">{entry.kind}</span>'
            desc_html = f'<p class="entry-desc">{entry.description.replace(chr(10), "<br>")}</p>' if entry.description else ""
            tags_html = render_tags_table(entry)

            content_html += f"""
<div class="entry" id="{entry.kind}-{entry.name}">
  <div class="entry-header">
    {kind_badge}
    <span class="entry-name">{entry.name}</span>
    <span class="entry-line">line {entry.source_line}</span>
  </div>
  <p class="entry-brief">{entry.brief}</p>
  {desc_html}
  {tags_html}
</div>\n"""
        content_html += "</div>\n"

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;600&display=swap');
  :root {{
    --bg: #0a0f1a; --bg2: #101828; --surface: #131f32;
    --border: #1e3048; --accent: #00c8f0; --text: #e2eaf5;
    --muted: #5a7a9a; --green: #34d399; --orange: #fb923c;
    --purple: #a78bfa; --red: #f87171; --pink: #f472b6; --teal: #2dd4bf;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }}

  /* Sidebar */
  aside {{ width: 260px; min-width: 260px; background: var(--bg2); border-right: 1px solid var(--border); padding: 1.5rem 1rem; position: sticky; top: 0; height: 100vh; overflow-y: auto; }}
  aside h1 {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; color: var(--accent); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 1.5rem; }}
  aside ul {{ list-style: none; }}
  aside li {{ margin-bottom: 0.2rem; }}
  aside li a {{ display: block; padding: 0.3rem 0.5rem; color: var(--muted); text-decoration: none; font-size: 0.82rem; border-radius: 4px; transition: all 0.15s; font-family: 'IBM Plex Mono', monospace; }}
  aside li a:hover {{ background: var(--surface); color: var(--accent); }}
  .nav-file {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 1rem; padding: 0.2rem 0.5rem; }}

  /* Main */
  main {{ flex: 1; padding: 2rem; max-width: 900px; }}
  .page-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem; color: var(--accent); margin-bottom: 0.3rem; }}
  .page-sub {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }}

  /* Stats */
  .stats-bar {{ display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem 1.2rem; text-align: center; min-width: 90px; }}
  .stat-val {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem; color: var(--accent); font-weight: 600; }}
  .stat-lbl {{ font-size: 0.65rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }}

  /* File section */
  .file-section {{ margin-bottom: 3rem; }}
  .file-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 1rem; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 1.5rem; }}

  /* Entry */
  .entry {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; transition: border-color 0.2s; }}
  .entry:hover {{ border-color: var(--accent); }}
  .entry-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }}
  .kind-badge {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }}
  .kind-class {{ background: rgba(0,200,240,0.15); color: var(--accent); }}
  .kind-func  {{ background: rgba(52,211,153,0.15); color: var(--green); }}
  .kind-field {{ background: rgba(167,139,250,0.15); color: var(--purple); }}
  .entry-name {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 600; }}
  .entry-line {{ margin-left: auto; font-size: 0.7rem; color: var(--muted); font-family: 'IBM Plex Mono', monospace; }}
  .entry-brief {{ color: var(--text); font-size: 0.95rem; margin-bottom: 0.5rem; }}
  .entry-desc {{ color: var(--muted); font-size: 0.85rem; line-height: 1.6; margin-bottom: 0.75rem; font-weight: 300; }}

  /* Params table */
  .params-table {{ width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.82rem; }}
  .params-table th {{ background: var(--bg2); color: var(--muted); text-align: left; padding: 0.4rem 0.75rem; font-weight: 600; border-bottom: 1px solid var(--border); }}
  .params-table td {{ padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border); color: var(--text); }}
  .params-table code {{ color: var(--accent); font-family: 'IBM Plex Mono', monospace; }}

  /* Tag blocks */
  .tag-block {{ display: flex; align-items: flex-start; gap: 0.5rem; margin: 0.4rem 0; font-size: 0.82rem; }}
  .badge {{ font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 100px; white-space: nowrap; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
  .badge-blue   {{ background: rgba(0,200,240,0.15);  color: var(--accent); }}
  .badge-green  {{ background: rgba(52,211,153,0.15); color: var(--green); }}
  .badge-purple {{ background: rgba(167,139,250,0.15);color: var(--purple); }}
  .badge-orange {{ background: rgba(251,146,60,0.15); color: var(--orange); }}
  .badge-teal   {{ background: rgba(45,212,191,0.15); color: var(--teal); }}
  .badge-gray   {{ background: rgba(90,122,154,0.15); color: var(--muted); }}
  .badge-red    {{ background: rgba(248,113,113,0.15);color: var(--red); }}
  .badge-pink   {{ background: rgba(244,114,182,0.15);color: var(--pink); }}
  .tag-val {{ color: var(--muted); line-height: 1.5; }}

  /* Footer */
  footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.75rem; font-family: 'IBM Plex Mono', monospace; }}
</style>
</head>
<body>
<aside>
  <h1>📘 Verse Docs</h1>
  <ul>{nav_items}</ul>
</aside>
<main>
  <h1 class="page-title">{title}</h1>
  <p class="page-sub">Автоматично згенеровано verse_doc.py · Tycoon Simulator (UEFN)</p>
  {stats_html}
  {content_html}
  <footer>Generated by verse_doc.py · Вощенко Денис · 2025</footer>
</main>
</body>
</html>"""


def generate_index(doc_files: List[DocFile], output_dir: str):
    """Генерує index.html — головна сторінка документації."""
    html = generate_html(doc_files, "Tycoon Simulator — API Documentation")
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

# ── Головна функція ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="verse_doc.py — генератор документації для Verse/UEFN")
    parser.add_argument("path", help="Шлях до директорії з .verse файлами")
    parser.add_argument("-o", "--output", default="docs/generated", help="Директорія для збереження HTML")
    parser.add_argument("--title", default="Tycoon Simulator — Docs", help="Заголовок документації")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Знаходимо .verse файли
    verse_files = []
    for root, _, files in os.walk(args.path):
        for f in files:
            if f.endswith(".verse") and ".digest." not in f:
                verse_files.append(os.path.join(root, f))

    if not verse_files:
        print(f"⚠ Verse файли не знайдено у: {args.path}")
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  verse_doc.py — Verse Documentation Generator")
    print(f"{'='*55}")

    doc_files = []
    total_entries = 0
    for vf in sorted(verse_files):
        df = parse_verse_file(vf)
        doc_files.append(df)
        total_entries += len(df.entries)
        print(f"  ✓ {os.path.basename(vf)} → {len(df.entries)} documented entries")

    generate_index(doc_files, args.output)

    print(f"\n  Файлів оброблено  : {len(verse_files)}")
    print(f"  Задокументовано   : {total_entries} елементів")
    print(f"  Вихідна директорія: {args.output}/")
    print(f"  Відкрийте        : {args.output}/index.html")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
