import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from digest.browser_bridge import import_snapshot, save_browser_preparation
from digest.policy import BEIJING, ZSXQ_GROUPS


class BrowserBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = ZSXQ_GROUPS[0]
        self.snapshot = self.root / "browser.json"

    def write_snapshot(self, captured="2026-10-16T13:03:00Z", url=None):
        self.snapshot.write_text(json.dumps({
            "captured_at": captured,
            "url": url or f"https://wx.zsxq.com/group/{self.source}",
            "cards": [
                {"date": "2026-10-16 21:02", "text": "after"},
                {"date": "2026-10-16 18:30", "text": "inside"},
                {"date": "2026-10-16 08:59", "text": "before"},
            ],
        }), encoding="utf-8")

    def test_final_import_keeps_hash_and_never_claims_full_read(self):
        self.write_snapshot()
        result = import_snapshot(self.root, date(2026, 10, 16), "evening",
                                 self.source, self.snapshot, "final")
        data = json.loads(result.read_text())
        self.assertEqual(data["window_list_items"], 1)
        self.assertTrue(data["earlier_boundary_seen"])
        self.assertTrue(data["later_boundary_seen"])
        self.assertFalse(data["complete"])
        self.assertIn("列表快照不证明", data["issues"][0])
        self.assertEqual(len(data["original"]["sha256"]), 64)

    def test_rejects_wrong_source_and_early_final(self):
        self.write_snapshot(url="https://wx.zsxq.com/group/other")
        with self.assertRaisesRegex(ValueError, "does not identify"):
            import_snapshot(self.root, date(2026, 10, 16), "evening",
                            self.source, self.snapshot, "final")
        self.write_snapshot(captured="2026-10-16T12:59:00Z")
        with self.assertRaisesRegex(ValueError, "precedes"):
            import_snapshot(self.root, date(2026, 10, 16), "evening",
                            self.source, self.snapshot, "final")

    def test_preparation_links_imported_file_to_checkpoint(self):
        self.write_snapshot(captured="2026-10-16T12:15:00Z")
        checkpoint = save_browser_preparation(
            self.root, date(2026, 10, 16), "evening",
            datetime(2026, 10, 16, 20, 20, tzinfo=BEIJING),
            {self.source: self.snapshot},
        )
        data = json.loads(checkpoint.read_text())
        self.assertEqual(data["phase"], "preparation_not_delivery")
        self.assertEqual(len(data["missing_sources"]), 6)
        imported = self.root / data["evidence"][self.source][0]["path"]
        self.assertFalse(json.loads(imported.read_text())["complete"])

    def test_preparation_rejects_future_snapshot(self):
        self.write_snapshot(captured="2026-10-16T12:40:00Z")
        with self.assertRaisesRegex(ValueError, "after preparation time"):
            save_browser_preparation(
                self.root, date(2026, 10, 16), "evening",
                datetime(2026, 10, 16, 20, 20, tzinfo=BEIJING),
                {self.source: self.snapshot},
            )


if __name__ == "__main__":
    unittest.main()
