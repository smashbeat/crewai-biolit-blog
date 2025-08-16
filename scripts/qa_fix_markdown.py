#!/usr/bin/env python3
import sys, re
from pathlib import Path

def split_frontmatter(text: str):
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) == 3:
            # ['', fm, body]
            return f"---{parts[1]}---\n", parts[2]
    return "", text

def join_frontmatter(fm: str, body: str) -> str:
    return (fm or "") + body

def strip_trailing_spaces(body: str) -> str:
    return re.sub(r"[ \t]+$", "", body, flags=re.M)

def ensure_single_trailing_newline(s: str) -> str:
    s = s.rstrip("\r\n") + "\n"
    return s

def collapse_blank_lines_outside_code(body: str) -> str:
    lines = body.splitlines()
    out = []
    in_code = False
    blank_streak = 0
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append(ln)
            blank_streak = 0
            continue
        if not in_code:
            if ln.strip() == "":
                blank_streak += 1
                if blank_streak <= 1:
                    out.append("")
                # else skip extra blanks
            else:
                blank_streak = 0
                out.append(ln)
        else:
            out.append(ln)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")

def ensure_blank_around_headings(body: str) -> str:
    lines = body.splitlines()
    out = []
    in_code = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append(ln)
            continue
        if not in_code and re.match(r"^#{1,6}\s+\S", ln):
            # ensure blank before (if not at top and previous non-blank)
            if len(out) > 0 and out[-1].strip() != "":
                out.append("")
            out.append(ln)
            # ensure blank after (peek next non-empty)
            nxt = lines[i+1] if i+1 < len(lines) else ""
            if nxt.strip() != "":
                out.append("")
        else:
            out.append(ln)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")

def demote_first_h1(body: str) -> str:
    """Change the first '# ' to '## ' so layout H1 + content H2 passes MD025."""
    lines = body.splitlines()
    in_code = False
    changed = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code and not changed and re.match(r"^#\s+\S", ln):
            lines[i] = re.sub(r"^#(\s+)", r"##\1", ln)
            changed = True
            break
    return "\n".join(lines) + ("\n" if body.endswith("\n") else "")

def fix_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(raw)

    # Normalize line endings
    body = body.replace("\r\n", "\n").replace("\r", "\n")

    # 1) trailing spaces
    body2 = strip_trailing_spaces(body)
    # 2) blank lines collapse (outside code)
    body2 = collapse_blank_lines_outside_code(body2)
    # 3) ensure blank lines around headings (outside code)
    body2 = ensure_blank_around_headings(body2)
    # 4) demote first H1 -> H2 (avoid MD025 with layout H1)
    body2 = demote_first_h1(body2)
    # 5) ensure single trailing newline
    body2 = ensure_single_trailing_newline(body2)

    fixed = join_frontmatter(fm, body2)
    if fixed != raw:
        path.write_text(fixed, encoding="utf-8")
        return True
    return False

def main(files):
    changed = 0
    for f in files:
        p = Path(f)
        if p.suffix.lower() != ".md":
            continue
        if fix_file(p):
            print("fixed", p)
            changed += 1
    if changed == 0:
        print("no changes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/qa_fix_markdown.py <files...>")
        sys.exit(1)
    main(sys.argv[1:])
