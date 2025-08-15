#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import re
import yaml
import glob

DEFAULT_DIR = "apps/site/src/content/posts"

def parse_front_matter(text: str):
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
    errors, warnings = [], []
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

    title = fm.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("frontmatter.title must be a non-empty string")

    if "tags" in fm:
        tags = fm["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            errors.append("frontmatter.tags must be an array of strings")

    if "slug" in fm:
        msg = "frontmatter.slug is not allowed (Astro generates slugs). Remove it."
        if strict_slug:
            errors.append(msg)
        else:
            warnings.append(msg)

    return errors, warnings

def collect_markdown_paths(inputs):
    """
    Accept zero or more inputs (files/dirs/globs). If none, use DEFAULT_DIR.
    Return a de-duplicated list of .md files.
    """
    paths = []
    if not inputs:
        root = Path(DEFAULT_DIR)
        if root.exists():
            paths.extend(sorted(root.rglob("*.md")))
    else:
        for s in inputs:
            # glob patterns
            if any(ch in s for ch in "*?[]"):
                for m in glob.glob(s, recursive=True):
                    mp = Path(m)
                    if mp.is_dir():
                        paths.extend(mp.rglob("*.md"))
                    elif mp.is_file() and mp.suffix.lower() == ".md":
                        paths.append(mp)
            else:
                p = Path(s)
                if p.is_dir():
                    paths.extend(p.rglob("*.md"))
                elif p.is_file() and p.suffix.lower() == ".md":
                    paths.append(p)

    # de-dup while preserving order
    seen, out = set(), []
    for p in paths:
        sp = str(Path(p).resolve())
        if sp not in seen:
            seen.add(sp)
            out.append(Path(sp))
    return out

def main():
    ap = argparse.ArgumentParser(description="Frontmatter QA for posts")
    ap.add_argument("paths", nargs="*", help="Files or directories (globs ok). Default: apps/site/src/content/posts")
    ap.add_argument("--strict-slug", action="store_true", help="Treat presence of slug in frontmatter as an error")
    args = ap.parse_args()

    md_files = collect_markdown_paths(args.paths)
    if not md_files:
        print("No markdown files found; nothing to check.")
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
