#!/usr/bin/env python3
import sys, re, json
from pathlib import Path
import yaml

REQ_FIELDS = ["title", "meta_description", "tags"]
MAX_TITLE = 60
MAX_DESC  = 155

FENCE_RE   = re.compile(r'(?m)^\s*```')
SLUG_SAFE  = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def read_frontmatter(md_text: str):
    md_text = md_text.lstrip()
    if not md_text.startswith("---"):
        return None, md_text
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return None, md_text
    _, fm_raw, rest = parts
    try:
        data = yaml.safe_load(fm_raw) or {}
    except Exception:
        data = None
    return data, rest

def fail(msg):
    print(f"ERROR: {msg}")
    return 1

def warn(msg):
    print(f"WARNING: {msg}")

def validate_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")

    fm, body = read_frontmatter(text)
    if fm is None:
        return fail(f"{path}: Missing or invalid frontmatter block")

    # Required fields present
    missing = [k for k in REQ_FIELDS if k not in fm or fm[k] in (None, "", [])]
    if missing:
        return fail(f"{path}: Missing required fields: {', '.join(missing)}")

    # Types & lengths
    title = str(fm["title"]).strip()
    desc  = str(fm["meta_description"]).strip()
    tags  = fm["tags"]
    if not isinstance(tags, list) or not tags:
        return fail(f"{path}: 'tags' must be a non-empty array")

    if len(title) > MAX_TITLE:
        warn(f"{path}: title length {len(title)} > {MAX_TITLE}")
    if len(desc) > MAX_DESC:
        warn(f"{path}: meta_description length {len(desc)} > {MAX_DESC}")

    # slug rules (optional): if provided, enforce kebab-case + match filename
    slug = fm.get("slug")
    stem = path.stem
    if slug:
        if " " in slug or not SLUG_SAFE.match(slug):
            return fail(f"{path}: slug must be kebab-case (got '{slug}')")
        if slug != stem:
            warn(f"{path}: slug ('{slug}') != filename ('{stem}'); build will still use filename path")

    # No stray fenced code blocks at column 0 (common generation artifact)
    # Allow inline fences inside code examples if they start indented (4 spaces or tab).
    for m in FENCE_RE.finditer(body):
        # Check if that fence line is indented
        start = m.start()
        line_start = body.rfind("\n", 0, start) + 1
        fence_line = body[line_start: body.find("\n", line_start) if body.find("\n", line_start) != -1 else len(body)]
        if fence_line.startswith("```"):  # no indentation
            return fail(f"{path}: top-level fenced code block found; strip outer ``` from generated content")

    return 0

def main():
    if len(sys.argv) != 2:
        print("Usage: frontmatter_check.py <posts_dir>")
        sys.exit(2)
    posts_dir = Path(sys.argv[1])
    if not posts_dir.exists():
        print(f"Directory not found: {posts_dir}")
        sys.exit(2)

    errors = 0
    for md in sorted(posts_dir.glob("*.md")):
        errors += validate_file(md)

    if errors:
        print(f"\nFAILED: {errors} file(s) with errors.")
        sys.exit(1)
    print("Frontmatter & content checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()