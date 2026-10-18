import hashlib
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from digest.audio import narration_text
from digest.browser_bridge import import_snapshot
from digest.browser_review import complete_snapshot
from digest.policy import BEIJING, HOLDING_TICKERS, SEVEN_SOURCES, X_ACCOUNTS
from digest.staging import checkpoint_path, finalize, save_preparation


DAY = date(2026, 10, 16)
PREP = datetime(2026, 10, 16, 20, 15, tzinfo=BEIJING)
FINAL = datetime(2026, 10, 16, 21, 5, tzinfo=BEIJING)


def complete_coverage():
    return {
        "sources": {source: {
            "list_boundary": True, "body_reviewed": True,
            "visible_comments_reviewed": True,
            "required_attachments_reviewed": True,
        } for source in SEVEN_SOURCES},
        "announcements_checked": HOLDING_TICKERS,
        "announcement_provider": "东方财富",
    }


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_file = self.root / "evidence" / "early.json"
        self.source_file.parent.mkdir()
        self.source_file.write_text('{"captured_at":"2026-10-16T12:10:00Z"}')
        self.report = self.root / "reports" / "evening.md"
        self.report.parent.mkdir()
        self.report.write_text("\n".join("## " + section for section in (
            "本期最重要的5条", "一、市场复盘", "二、信息提炼",
            "三、重大提示", "四、阅读提示", "五、最终总结",
            "完整7源覆盖表")), encoding="utf-8")
        self.audio_file = self.root / "audio" / "evening.wav"
        self.audio_file.parent.mkdir()
        self.audio_file.write_bytes(b"verified audio test fixture")
        self.audio = {"complete": True, "matches_report": True,
                      "file_verified": True,
                      "narration_sha256": hashlib.sha256(narration_text(
                          self.report.read_text(encoding="utf-8")).encode("utf-8")).hexdigest(),
                      "audio_sha256": hashlib.sha256(self.audio_file.read_bytes()).hexdigest()}

    def refreshes(self, captured="2026-10-16T13:01:00Z"):
        records = {}
        for index, source in enumerate(SEVEN_SOURCES):
            raw = self.root / "evidence" / f"raw-final-{index}.json"
            url = (f"https://x.com/{source}" if source in X_ACCOUNTS else
                   f"https://wx.zsxq.com/group/{source}")
            raw.write_text(json.dumps({"captured_at": "2026-10-16T13:01:00Z",
                                       "url": url, "cards": []}))
            path = import_snapshot(self.root, DAY, "evening", source, raw, "final")
            manifest = self.root / "evidence" / f"review-{index}.json"
            lanes = ("posts", "replies", "reposts") if source in X_ACCOUNTS else ("timeline",)
            pages = []
            for lane in lanes:
                page = {"lane": lane, "cursor": "start", "next_cursor": None,
                        "item_ids": [], "stop_reason": "source_end", "terminal": True}
                observation = self.root / "evidence" / f"browser-page-{index}-{lane}.json"
                observation.write_text(json.dumps({**page, "source": source, "url": url,
                                                   "captured_at": "2026-10-16T13:01:00Z",
                                                   "endpoint_text": "No more items"}))
                pages.append({**page, "browser_page": {"path": str(observation),
                                                         "sha256": hashlib.sha256(
                                                             observation.read_bytes()).hexdigest()}})
            manifest.write_text(json.dumps({
                "source": source,
                "list_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "completed_at": "2026-10-16T13:04:00Z",
                "list_pages": pages,
                "details": {},
            }))
            complete_snapshot(self.root, path, manifest)
            if captured != "2026-10-16T13:01:00Z":
                data = json.loads(path.read_text())
                data["captured_at"] = captured
                path.write_text(json.dumps(data))
            records[source] = {
                "list_snapshot": path,
                "previous_items_rechecked": True,
                "comments_rechecked": True,
                "attachments_rechecked": True,
            }
        return records

    def test_preparation_is_durable_but_not_delivery(self):
        path = save_preparation(self.root, DAY, "evening", PREP,
                                {SEVEN_SOURCES[0]: [self.source_file]}, self.report)
        data = json.loads(path.read_text())
        self.assertEqual(data["phase"], "preparation_not_delivery")
        self.assertEqual(len(data["missing_sources"]), 6)
        self.assertEqual(data["prep_start"], "2026-10-16T20:00:00+08:00")
        self.assertEqual(len(data["evidence"][SEVEN_SOURCES[0]][0]["sha256"]), 64)

        # A resumed preparation keeps prior source evidence instead of losing it.
        save_preparation(self.root, DAY, "evening",
                         datetime(2026, 10, 16, 20, 40, tzinfo=BEIJING), {}, None)
        resumed = json.loads(path.read_text())
        self.assertEqual(resumed["evidence"], data["evidence"])

    def test_final_requires_post_cutoff_refresh_and_rechecks(self):
        save_preparation(self.root, DAY, "evening", PREP,
                         {SEVEN_SOURCES[0]: [self.source_file]})
        refreshes = self.refreshes("2026-10-16T12:59:00Z")
        with self.assertRaisesRegex(ValueError, "report cutoff"):
            finalize(self.root, DAY, "evening", FINAL, refreshes,
                     complete_coverage(), self.audio, self.report, self.audio_file)
        self.assertFalse(checkpoint_path(self.root, DAY, "evening", "final").exists())

        refreshes = self.refreshes()
        refreshes[SEVEN_SOURCES[0]]["comments_rechecked"] = False
        with self.assertRaisesRegex(ValueError, "comments or attachments"):
            finalize(self.root, DAY, "evening", FINAL, refreshes,
                     complete_coverage(), self.audio, self.report, self.audio_file)

    def test_changed_preparation_needs_full_final_review_and_is_recorded(self):
        save_preparation(self.root, DAY, "evening", PREP,
                         {SEVEN_SOURCES[0]: [self.source_file]})
        self.source_file.write_text('{"captured_at":"2026-10-16T12:10:00Z","changed":1}')
        refreshes = self.refreshes()
        with self.assertRaisesRegex(ValueError, "seven-source reading"):
            finalize(self.root, DAY, "evening", FINAL, refreshes,
                     complete_coverage(), {}, self.report, self.audio_file)
        path = finalize(self.root, DAY, "evening", FINAL, refreshes,
                        complete_coverage(), self.audio, self.report, self.audio_file)
        data = json.loads(path.read_text())
        self.assertEqual(data["invalidated_preparation_sources_rechecked"],
                         [SEVEN_SOURCES[0]])
        self.assertEqual(data["phase"], "final_checked")
        self.assertTrue(data["final_source_snapshots"][SEVEN_SOURCES[0]]["comments_rechecked"])

    def test_audio_receipt_must_match_saved_file(self):
        save_preparation(self.root, DAY, "evening", PREP, {})
        self.audio_file.write_bytes(b"changed after receipt")
        with self.assertRaisesRegex(ValueError, "audio file does not match"):
            finalize(self.root, DAY, "evening", FINAL, self.refreshes(),
                     complete_coverage(), self.audio, self.report, self.audio_file)

    def test_list_only_browser_capture_cannot_finalize(self):
        save_preparation(self.root, DAY, "evening", PREP, {})
        refreshes = self.refreshes()
        snapshot = refreshes[SEVEN_SOURCES[0]]["list_snapshot"]
        snapshot.write_text(json.dumps({
            "captured_at": "2026-10-16T13:01:00Z", "complete": False,
        }))
        with self.assertRaisesRegex(ValueError, "list-only browser capture"):
            finalize(self.root, DAY, "evening", FINAL, refreshes,
                     complete_coverage(), self.audio, self.report, self.audio_file)

    def test_missing_complete_field_cannot_finalize(self):
        save_preparation(self.root, DAY, "evening", PREP, {})
        refreshes = self.refreshes()
        snapshot = refreshes[SEVEN_SOURCES[0]]["list_snapshot"]
        data = json.loads(snapshot.read_text())
        data.pop("complete")
        snapshot.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "list-only browser capture"):
            finalize(self.root, DAY, "evening", FINAL, refreshes,
                     complete_coverage(), self.audio, self.report, self.audio_file)


if __name__ == "__main__":
    unittest.main()
