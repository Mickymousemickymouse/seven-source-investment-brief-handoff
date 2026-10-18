"""User-approved requirements that supersede the 2026-10-10 handoff."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


BEIJING = ZoneInfo("Asia/Shanghai")
ZSXQ_GROUPS = (
    "15552822254242",  # 短评&信息
    "28855811424141",  # 基业长青+
    "15554411815552",  # 2030FY
    "28888222154481",  # 180K Research
)
X_ACCOUNTS = ("Ariston_Macro", "RayDalio", "CryptoHayes")
SEVEN_SOURCES = ZSXQ_GROUPS + X_ACCOUNTS
HOLDING_TICKERS = (
    "01787", "600547", "03939", "06181", "00189", "300201", "000059", "601899"
)
ANNOUNCEMENT_PROVIDER = "东方财富"
AUDIO_VOICES = {"mac_zh": "Tingting", "mac_en": "Samantha", "windows_zh": "Yaoyao"}
BODY_SECTIONS = (
    "本期最重要的5条", "一、市场复盘", "二、信息提炼", "三、重大提示",
    "四、阅读提示", "五、最终总结",
)


def report_window(day: date, edition: str) -> tuple[datetime, datetime]:
    """Return [start, end) in Beijing time for the current 09:00/21:00 contract."""
    if edition not in ("morning", "evening"):
        raise ValueError("edition must be morning or evening")
    if edition == "evening":
        return (datetime.combine(day, time(9), BEIJING), datetime.combine(day, time(21), BEIJING))
    start = datetime.combine(day - timedelta(days=1), time(21), BEIJING)
    if day == date(2026, 10, 15):
        start = datetime(2026, 10, 14, 20, 30, tzinfo=BEIJING)
    return (start, datetime.combine(day, time(9), BEIJING))


def is_new_event(event_time: datetime, start: datetime, end: datetime) -> bool:
    """A share time or report fetch time cannot stand in for the event time."""
    if event_time.tzinfo is None:
        raise ValueError("event time needs a timezone")
    return start <= event_time.astimezone(BEIJING) < end


def source_note(sources: list[str]) -> str:
    """Use one parenthesis for all sources supporting the same conclusion."""
    clean = [s.strip() for s in sources if s.strip()]
    if not clean:
        raise ValueError("at least one source is required")
    return "（来源：" + "；".join(clean) + "）"


def report_issues(markdown: str) -> list[str]:
    """Catch the report defects the user identified before audio or delivery."""
    issues: list[str] = []
    required = ["## " + heading for heading in BODY_SECTIONS]
    required.append("## 完整7源覆盖表")
    missing = [heading for heading in required if heading not in markdown]
    issues.extend("缺少章节：" + heading for heading in missing)
    if missing:
        return issues
    if markdown.index("## 完整7源覆盖表") < markdown.index("## 本期最重要的5条"):
        issues.append("覆盖表出现在正文之前")
    for section in BODY_SECTIONS:
        start = markdown.index("## " + section)
        next_heading = markdown.find("\n## ", start + 3)
        content = markdown[start:next_heading if next_heading >= 0 else None]
        numbers = [int(m.group(1)) for m in re.finditer(r"(?m)^\s*(\d+)\.\s+", content)]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            issues.append(section + "编号不连续")
        if section == "本期最重要的5条" and len(numbers) > 5:
            issues.append("最重要的5条超过5项")
    if re.search(r"（来源：[^）]*）\s*（来源：", markdown):
        issues.append("相邻来源应合并为一个括号")
    if re.search(r"(?m)^[\u3000 \t]+(?=\*\*|\S)", markdown):
        issues.append("正文出现首行缩进")
    if "Fact：" in markdown or "Take：" in markdown:
        issues.append("旧版Fact/Take标签仍在正文")
    return issues


def complete_delivery(coverage: dict, audio: dict) -> bool:
    """A formatted report is never proof that seven-source reading is complete."""
    sources = coverage.get("sources", {})
    if set(sources) != set(SEVEN_SOURCES):
        return False
    for key in SEVEN_SOURCES:
        source = sources[key]
        if not (source.get("list_boundary") and source.get("body_reviewed")
                and source.get("visible_comments_reviewed")):
            return False
        excluded = source.get("excluded_attachments", [])
        if excluded:
            if source.get("required_attachments_reviewed") or not source.get(
                    "all_accessible_attachments_reviewed"):
                return False
            if not all(item.get("filename") and item.get("observed_at")
                       and item.get("evidence") and item.get("browser_error") in (
                           "ERR_BLOCKED_BY_CLIENT", "APP_ONLY_CONTENT_PROTECTION")
                       and item.get("user_authorized") for item in excluded):
                return False
        elif not source.get("required_attachments_reviewed"):
            return False
    if set(coverage.get("announcements_checked", ())) != set(HOLDING_TICKERS):
        return False
    if coverage.get("announcement_provider") != ANNOUNCEMENT_PROVIDER:
        return False
    return bool(audio.get("complete") and audio.get("matches_report") and audio.get("file_verified"))
