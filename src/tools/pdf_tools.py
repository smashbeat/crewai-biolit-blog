from pypdf import PdfReader

def load_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for i, p in enumerate(reader.pages, start=1):
        txt = p.extract_text() or ""
        pages.append(f"[p.{i}]\n{txt}")
    return "\n\n".join(pages)
