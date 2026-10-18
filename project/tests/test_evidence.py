import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from digest.evidence import audit
from digest.policy import BEIJING


class EvidenceAuditTests(unittest.TestCase):
    def test_window_excludes_end_and_does_not_claim_full_read(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "short-20261015-all-loaded.json"
            path.write_text(json.dumps({"captured_at": "2026-10-15T14:00:00Z", "cards": [
                {"date": "2026-10-15 09:00", "text": "in"},
                {"date": "2026-10-15 21:00", "text": "out"},
            ]}), encoding="utf-8")
            result = audit(Path(root), datetime(2026, 10, 15, tzinfo=BEIJING), "evening")
            entry = result["sources"]["15552822254242"]
            self.assertEqual(entry["window_list_entries"], 1)
            self.assertFalse(entry["detail_comments_attachments_verified"])
            self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
