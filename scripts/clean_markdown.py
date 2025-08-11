#!/usr/bin/env python3
import re, sys
from pathlib import Path

FM_LINE = re.compile(r'^---\s*$', re.M)
HLINE = re.compile(r'^\s*#{1,6}\s', re.M)

def split_front_matter(text: str):
    if not text.startswith('---'):
        return None, text
    matches = list(FM_LINE.finditer(text))
    if len(matches) < 2:
        return None, text
    start = matches[0].end()
    end = matches[1].start()
    fm = text[start:end].strip('\n')
    body = text[matches[1].end():]
    return fm, body

def remove_outer_fence(body: str) -> str:
    s = body.strip()
    m = re.match(r'^\s*```[^\n]*\n(.*?)\n\s*```\s*$', s, re.S)
    return m.group(1).strip() if m else body

def deindent_if_codeish(body: str) -> str:
    lines = body.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    if not nonempty:
        return body
    codeish = sum(1 for ln in nonempty if ln.startswith('    ') or ln.startswith('\t'))
    if codeish / len(nonempty) >= 0.5:
        def undent(ln: str) -> str:
            if ln.startswith('    '): return ln[4:]
            if ln.startswith('\t'):   return ln[1:]
            return ln
        lines = [undent(ln) for ln in lines]
        body = '\n'.join(lines)
    # ensure headings start at column 0
    body = re.sub(r'(?m)^[ \t]+(#)+', r'\1', body)
    return body

def find_faq_region(body: str):
    m = re.search(r'^\s*##\s*FAQ[s]?\s*$', body, re.I | re.M)
    if not m:
        return None
    start = m.start()
    # find the next heading after FAQs
    m2 = HLINE.search(body, m.end())
    end = m2.start() if m2 else len(body)
    return (start, end)

def strip_fences_in_region(body: str, region):
    if not region: return body
    start, end = region
    prefix = body[:start]
    middle = body[start:end]
    suffix = body[end:]
    # Remove any lines that are just ``` or ```lang in the FAQ block
    middle = re.sub(r'(?m)^\s*```[^\n]*\n?', '', middle)
    middle = re.sub(r'(?m)^\s*```\s*$', '', middle)
    return prefix + middle + suffix

def balance_code_fences(body: str) -> str:
    lines = body.splitlines()
    in_code = False
    for ln in lines:
        if re.match(r'^\s*```', ln):
            in_code = not in_code
    if in_code:
        # add a closing fence at the end if we ended inside a code block
        lines.append('```')
    return '\n'.join(lines)

def clean_text(t: str) -> str:
    fm, body = split_front_matter(t)
    # 1) remove outer fence around whole body (if any)
    body = remove_outer_fence(body)
    # 2) strip fences inside FAQs block specifically
    region = find_faq_region(body)
    body = strip_fences_in_region(body, region)
    # 3) balance any lingering unclosed fences
    body = balance_code_fences(body)
    # 4) deindent if it still looks like code
    body = deindent_if_codeish(body)
    return (fm, body)

def write_back(fp: Path, fm, body):
    if fm is not None:
        out = f"---\n{fm}\n---\n{body}"
    else:
        out = body
    fp.write_text(out, encoding='utf-8')

def clean_file(fp: str):
    p = Path(fp)
    t = p.read_text(encoding='utf-8')
    fm, body_new = clean_text(t)
    if fm is None:
        body_old = t
    else:
        # for comparison, reconstruct original body
        _, body_old = split_front_matter(t)
    if body_new != body_old:
        write_back(p, fm, body_new)
        print("fixed", fp)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_markdown.py <files...>")
        sys.exit(1)
    for arg in sys.argv[1:]:
        for p in Path().glob(arg) if any(ch in arg for ch in "*?[]") else [Path(arg)]:
            clean_file(str(p))

def remove_all_fence_lines(body: str) -> str:
    # delete any line that is just a triple-backtick fence (with or without a language tag)
    return re.sub(r'(?m)^\s*```[^\n]*\s*$', '', body)
def clean_text(t: str) -> str:
    fm, body = split_front_matter(t)
    body = remove_outer_fence(body)
    region = find_faq_region(body)
    body = strip_fences_in_region(body, region)
    body = remove_all_fence_lines(body)   # <-- add this line
    body = balance_code_fences(body)
    body = deindent_if_codeish(body)
    return (fm, body)

