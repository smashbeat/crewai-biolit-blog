#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import re
import yaml

DEFAULT_DIR = "apps/site/src/content/posts"

def parse_front_matter(text: str):
    """
    Return (fm_dict, body_str) or (None, original_text) if no frontmatter.
    """
    # frontmatter must start the file and be fenced with ---
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', text, flags=re.S)
    if not m:
        return None, text
    fm_raw, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_raw) or {}
        if not isinstance(fm, dict):
            return {"__invalid__": "Frontmatter must parse to a mapping/object"}, body
        return fm, body
    except Exception as e:
        return {"__invalid__": f"YAML parse error: {e}"}, body

def check_file(p: Path, strict_slug: bool = False):
    """
    Validate a single markdown file. Returns (errors:list[str], warnings:list[str]).
    """
    errors, warnings = []
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return [f"cannot read file: {e}"], []

    fm, _ = parse_front_matter(text)
    if fm is None:
        errors.append("missing frontmatter block (--- at top)")
        return errors, warnings

    if "__invalid__" in fm:
        errors.append(fm["__invalid__"])
        return errors, warnings

    # title: required non-empty string
    title = fm.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("frontmatter.title must be a non-empty string")

    # tags: if present, must be a list of strings
    if "tags" in fm:
        tags = fm["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, (str,)) for t in tags):
            errors.append("frontmatter.tags must be an array of strings")

    # discourage slug in FM (Astro generates it); warn by default, error in strict mode
    if "slug" in fm:
        msg = "frontmatter.slug is not allowed (Astro collection generates slugs). Remove it."
        if strict_slug:
            errors.append(msg)
        else:
            warnings.append(msg)

    return errors, warnings

def main():
    ap = argparse.ArgumentParser(description="Frontmatter QA for posts")
    ap.add_argument("posts_dir", nargs="?", default=DEFAULT_DIR, help="Directory with Markdown posts")
    ap.add_argument("--strict-slug", action="store_true", help="Treat presence of slug in frontmatter as an error")
    args = ap.parse_args()

    root = Path(args.posts_dir)
    if not root.exists():
        print(f"ERROR: directory not found: {root}", file=sys.stderr)
        sys.exit(2)

    md_files = sorted([p for p in root.rglob("*.md") if p.is_file()])
    if not md_files:
        print(f"No markdown files found under {root}")
        sys.exit(0)

    any_errors = False
    total_warnings = 0

    for p in md_files:
        errs, warns = check_file(p, strict_slug=args.strict_slug)
        if errs or warns:
            rel = p.as_posix()
            for e in errs:
                print(f"[ERROR] {rel}: {e}")
            for w in warns:
                print(f"[WARN ] {rel}: {w}")
        if errs:
            any_errors = True
        total_warnings += len(warns)

    if any_errors:
        print("Frontmatter check: FAILED")
        sys.exit(1)
    else:
        print(f"Frontmatter check: OK ({len(md_files)} files, {total_warnings} warnings)")
        sys.exit(0)

if __name__ == "__main__":
    main()
