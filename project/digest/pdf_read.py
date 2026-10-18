"""Extract page-addressable PDF text and flag pages needing visual/OCR review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


def extract_pdf(path: Path, evidence_dir: Path) -> dict:
    reader = PdfReader(str(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append({"page": number, "characters": len(text), "text": text})
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out = evidence_dir / f"pdf-{digest[:16]}.json"
    result = {
        "source_path": str(path), "sha256": digest, "page_count": len(pages),
        "pages_needing_visual_review": [page["page"] for page in pages if page["characters"] < 80],
        "pages": pages,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"evidence_path": str(out), "sha256": digest, "page_count": len(pages),
            "pages_needing_visual_review": result["pages_needing_visual_review"]}
