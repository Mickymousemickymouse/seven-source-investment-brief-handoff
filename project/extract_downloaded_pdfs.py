"""Extract downloaded research PDFs without altering their originals."""

import json
import sys
from pathlib import Path

from digest.pdf_read import extract_pdf

ROOT = Path(__file__).resolve().parent
if len(sys.argv) < 2:
    raise SystemExit("usage: python extract_downloaded_pdfs.py PDF [PDF ...]")
results = []
for raw in sys.argv[1:]:
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise SystemExit(f"not a PDF file: {path}")
    results.append({"name": path.name, **extract_pdf(path, ROOT / "evidence" / "pdf-text")})
manifest = ROOT / "evidence" / "downloaded-pdf-manifest.json"
previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
by_hash = {item["sha256"]: item for item in previous}
by_hash.update({item["sha256"]: item for item in results})
manifest.write_text(json.dumps(list(by_hash.values()), ensure_ascii=False, indent=2), encoding="utf-8")
for item in results:
    print(item["name"], item["page_count"], "页", "待视觉核对", len(item["pages_needing_visual_review"]), "页")
print("清单：", manifest)
