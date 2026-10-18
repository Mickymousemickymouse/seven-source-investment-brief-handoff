import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from digest.browser_bridge import import_snapshot
from digest.browser_review import complete_snapshot, verify_complete_snapshot
from digest.policy import ZSXQ_GROUPS


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BrowserReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = ZSXQ_GROUPS[0]
        self.native = f"https://wx.zsxq.com/group/{self.source}/topic/100"
        self.raw = self.root / "raw.json"
        self.raw.write_text(json.dumps({
            "captured_at": "2026-10-16T13:01:00Z",
            "url": f"https://wx.zsxq.com/group/{self.source}",
            "cards": [
                {"id": "100", "date": "2026-10-16T18:30:00+08:00",
                 "url": self.native, "text": "one window item"},
                {"id": "99", "date": "2026-10-13T20:59:00+08:00",
                 "url": f"https://wx.zsxq.com/group/{self.source}/topic/99",
                 "text": "older than the 72-hour lookback"},
            ],
        }))
        self.imported = import_snapshot(self.root, date(2026, 10, 16), "evening",
                                        self.source, self.raw, "final")
        self.image = self.root / "chart.png"
        self.image.write_bytes(b"actual saved image bytes")
        content = "价格上调15%。"
        comment = "Thanks"
        basis = "\n".join(("读者", "2026-10-16T18:45:00+08:00", comment))
        local_id = "local:" + sha(basis.encode())[:20]
        self.detail = self.root / "detail.json"
        self.detail.write_text(json.dumps({
            "item_id": "100", "url": self.native,
            "published_at": "2026-10-16T18:30:00+08:00",
            "captured_at": "2026-10-16T13:01:00Z",
            "body": content,
            "body_read": {"text_sha256": sha(content.encode()),
                          "reviewed_at": "2026-10-16T13:02:00Z",
                          "notes": "原文称板料调价15%，未证明全行业成交价。"},
            "comment_enumeration": {"complete": True, "unique_count": 1},
            "comment_pages": [{"cursor": "start", "next_cursor": None,
                               "terminal": True, "comment_ids": [local_id]}],
            "comments": [{"local_id": local_id, "author": "读者",
                          "published_at": "2026-10-16T18:45:00+08:00",
                          "content": comment,
                          "body_read": {"text_sha256": sha(comment.encode()),
                                        "reviewed_at": "2026-10-16T13:03:00Z",
                                        "notes": "仅致谢，没有新增事实。"},
                          "attachment_enumeration": {"complete": True, "count": 0},
                          "attachments": []}],
            "attachment_count": 1,
            "attachments": [{"id": "image-1", "filename": "chart.png",
                             "kind": "image",
                             "file": {"path": str(self.image), "sha256": sha(self.image.read_bytes())},
                             "read": {"reviewed_at": "2026-10-16T13:03:00Z",
                                      "unit_count": 1,
                                      "units": [{"number": 1, "notes": "图上显示单价提幅15%。"}]}}],
        }, ensure_ascii=False))
        self.manifest = self.root / "review.json"
        self.write_manifest()

    def write_manifest(self):
        page = {"lane": "timeline", "cursor": "start", "next_cursor": None,
                "item_ids": ["100", "99"], "stop_reason": "older_than_lookback"}
        observation = self.root / "browser-page.json"
        observation.write_text(json.dumps({**page, "source": self.source,
                                           "url": f"https://wx.zsxq.com/group/{self.source}",
                                           "captured_at": "2026-10-16T13:01:00Z"}))
        self.manifest.write_text(json.dumps({
            "source": self.source,
            "list_sha256": sha(self.raw.read_bytes()),
            "completed_at": "2026-10-16T13:04:00Z",
            "list_pages": [{**page, "browser_page": {"path": str(observation),
                                                   "sha256": sha(observation.read_bytes())}}],
            "details": {"100": {"path": str(self.detail),
                                "sha256": sha(self.detail.read_bytes())}},
        }, ensure_ascii=False))

    def test_complete_requires_matching_detail_comment_and_attachment_hashes(self):
        complete_snapshot(self.root, self.imported, self.manifest)
        record = verify_complete_snapshot(self.root, self.imported)
        self.assertTrue(record["complete"])
        self.assertEqual(record["reviewed_lookback_items"], 1)
        self.assertEqual(len(record["evidence_files"]), 5)
        self.image.write_bytes(b"later changed")
        with self.assertRaisesRegex(ValueError, "hash changed"):
            verify_complete_snapshot(self.root, self.imported)

    def test_missing_detail_or_comment_endpoint_cannot_promote_list(self):
        detail = json.loads(self.detail.read_text())
        detail["comment_pages"][0]["terminal"] = False
        self.detail.write_text(json.dumps(detail))
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "no visible endpoint"):
            complete_snapshot(self.root, self.imported, self.manifest)
        self.assertFalse(json.loads(self.imported.read_text())["complete"])

    def test_manifest_cannot_skip_a_visible_window_topic(self):
        manifest = json.loads(self.manifest.read_text())
        manifest["details"] = {}
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "lack opened-detail"):
            complete_snapshot(self.root, self.imported, self.manifest)

    def test_list_requires_native_ids_and_real_lower_boundary(self):
        manifest = json.loads(self.manifest.read_text())
        manifest["list_pages"][0]["item_ids"] = ["100"]
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "not bound to the browser observation"):
            complete_snapshot(self.root, self.imported, self.manifest)

    def test_pdf_pages_cannot_be_marked_read_with_one_note(self):
        pdf = self.root / "two-pages.pdf"
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
        ]
        contents = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, item in enumerate(objects, 1):
            offsets.append(len(contents))
            contents += f"{number} 0 obj\n".encode() + item + b"\nendobj\n"
        xref_at = len(contents)
        contents += b"xref\n0 5\n0000000000 65535 f \n"
        for offset in offsets[1:]:
            contents += f"{offset:010d} 00000 n \n".encode()
        contents += (b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
                     + str(xref_at).encode() + b"\n%%EOF\n")
        pdf.write_bytes(contents)
        detail = json.loads(self.detail.read_text())
        attachment = detail["attachments"][0]
        attachment.update(kind="pdf", filename=pdf.name,
                          file={"path": str(pdf), "sha256": sha(pdf.read_bytes())})
        self.detail.write_text(json.dumps(detail))
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "PDF pages were not all reviewed"):
            complete_snapshot(self.root, self.imported, self.manifest)


if __name__ == "__main__":
    unittest.main()
