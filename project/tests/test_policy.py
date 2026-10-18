import unittest
from datetime import date, datetime

from digest.policy import (
    BEIJING, report_window, is_new_event, source_note, report_issues, complete_delivery,
    SEVEN_SOURCES, HOLDING_TICKERS,
)


class PolicyTests(unittest.TestCase):
    def test_evening_window_and_boundary(self):
        start, end = report_window(date(2026, 10, 15), "evening")
        self.assertEqual((start.hour, end.hour), (9, 21))
        self.assertTrue(is_new_event(start, start, end))
        self.assertFalse(is_new_event(end, start, end))

    def test_first_morning_exception(self):
        start, end = report_window(date(2026, 10, 15), "morning")
        self.assertEqual((start.day, start.hour, start.minute, end.hour), (14, 20, 30, 9))

    def test_one_source_parenthesis(self):
        self.assertEqual(source_note(["甲", "乙", "丙"]), "（来源：甲；乙；丙）")

    def test_report_defects_are_caught(self):
        sections = "\n".join("## " + s + "\n" for s in (
            "本期最重要的5条", "一、市场复盘", "二、信息提炼", "三、重大提示",
            "四、阅读提示", "五、最终总结", "完整7源覆盖表"))
        bad = sections.replace("## 一、市场复盘\n", "## 一、市场复盘\n1. A\n3. B\n")
        bad += "\n（来源：甲）（来源：乙）\n"
        self.assertIn("一、市场复盘编号不连续", report_issues(bad))
        self.assertIn("相邻来源应合并为一个括号", report_issues(bad))

    def test_delivery_requires_reading_and_audio(self):
        sources = {key: {"list_boundary": True, "body_reviewed": True,
                         "visible_comments_reviewed": True,
                         "required_attachments_reviewed": True} for key in SEVEN_SOURCES}
        coverage = {"sources": sources, "announcements_checked": HOLDING_TICKERS,
                    "announcement_provider": "东方财富"}
        audio = {"complete": True, "matches_report": True, "file_verified": True}
        self.assertTrue(complete_delivery(coverage, audio))
        sources[SEVEN_SOURCES[0]]["visible_comments_reviewed"] = False
        self.assertFalse(complete_delivery(coverage, audio))

    def test_explicit_browser_block_can_be_excluded_without_claiming_it_read(self):
        sources = {key: {"list_boundary": True, "body_reviewed": True,
                         "visible_comments_reviewed": True,
                         "required_attachments_reviewed": True} for key in SEVEN_SOURCES}
        fy = sources[SEVEN_SOURCES[2]]
        fy.update(required_attachments_reviewed=False,
                  all_accessible_attachments_reviewed=True,
                  excluded_attachments=[{
                      "filename": "台积电：买方反馈 (1).pdf",
                      "observed_at": "2026-10-16T02:00:00+08:00",
                      "browser_error": "ERR_BLOCKED_BY_CLIENT",
                      "evidence": "browser-page-observation",
                      "user_authorized": True,
                  }])
        coverage = {"sources": sources, "announcements_checked": HOLDING_TICKERS,
                    "announcement_provider": "东方财富"}
        audio = {"complete": True, "matches_report": True, "file_verified": True}
        self.assertTrue(complete_delivery(coverage, audio))
        fy["excluded_attachments"][0]["browser_error"] = "APP_ONLY_CONTENT_PROTECTION"
        self.assertTrue(complete_delivery(coverage, audio))
        fy["excluded_attachments"][0]["browser_error"] = "unknown"
        self.assertFalse(complete_delivery(coverage, audio))


if __name__ == "__main__":
    unittest.main()
