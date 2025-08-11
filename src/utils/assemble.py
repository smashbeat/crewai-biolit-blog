# src/utils/assemble.py
import json
import sys
import re
import textwrap
from pathlib import Path
from datetime import date
import yaml

def _strip_outer_fence(md: str) -> str:
    s = md.strip()
    m = re.match(r"^\s*```(?:md|markdown|html|json|text)?\s*\n(.*?)\n\s*```\s*$",
                 s, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else md

def _dedent_markdown(md: str) -> str:
    md = md.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    md = textwrap.dedent(md)
    lines = md.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    if nonempty:
        # if ≥50% of lines still look indented as code, strip one level
        codeish = sum(1 for ln in nonempty if ln.startswith("    ") or ln.startswith("\t"))
        if codeish / len(nonempty) >= 0.5:
            def undent(ln: str) -> str:
                if ln.startswith("    "): return ln[4:]
                if ln.startswith("\t"):   return ln[1:]
                return ln
            lines = [undent(ln) for ln in lines]
            md = "\n".join(lines)
    # ensure headings start at column 0
    md = re.sub(r"(?m)^[ \t]+(#)+", r"\1", md)
    return md

def _normalize_markdown(md: str) -> str:
    return _dedent_markdown(_strip_outer_fence(md))

def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)
    return text

def _coerce_meta(raw_text: str) -> dict:
    t = (raw_text or "").lstrip("\ufeff").strip()
    if not t:
        return {}
    for candidate in (t, _strip_code_fences(t)):
        try:
            return json.loads(candidate)
        except Exception:
            pass
    try:
        y = yaml.safe_load(t)
        if isinstance(y, dict):
            return y
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}

def build_front_matter(title: str, slug: str, description: str, tags):
    fm = {
        "title": title or "Untitled",
        "slug": slug or "untitled",
        "description": description or "",
        "tags": list(tags or []),
    }
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"

def main(post_path: str, seo_json_path: str, out_path: str):
    post_md = Path(post_path).read_text(encoding="utf-8")
    post_md = _normalize_markdown(post_md)
# Nuke any remaining triple-backtick fence lines (e.g., ``` or ```markdown)
    post_md = re.sub(r'(?m)^\s*```[a-zA-Z0-9_-]*\s*$', '', post_md)

    raw_meta = Path(seo_json_path).read_text(encoding="utf-8", errors="ignore")
    meta = _coerce_meta(raw_meta)

    title = meta.get("title") or Path(out_path).stem.replace("-", " ").title()
    slug  = meta.get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    desc  = meta.get("meta_description") or meta.get("description") or ""
    tags  = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    json_ld = meta.get("json_ld") or meta.get("jsonLD") or meta.get("schema")
    if not json_ld:
        json_ld = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": desc,
            "datePublished": str(date.today()),
            "dateModified": str(date.today()),
            "mainEntityOfPage": {"@type":"WebPage","@id": f"https://example.com/{slug}"},
            "keywords": ", ".join(tags),
            "author": {"@type":"Organization","name":"Your Company"},
            "publisher": {"@type":"Organization","name":"Your Company"},
        }

    fm = build_front_matter(title, slug, desc, tags)
    json_ld_block = (
        '\n<script type="application/ld+json">\n'
        + json.dumps(json_ld, ensure_ascii=False, indent=2)
        + "\n</script>\n"
    )
    Path(out_path).write_text(fm + post_md + "\n" + json_ld_block, encoding="utf-8")
    print(f"✅ Assembled: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python -m src.utils.assemble <post.md> <seo.json> <out.md>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])

