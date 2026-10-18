"""Import source snapshots exported from the logged-in browser tool.

The browser control service is available to a Codex turn, not to this Python
process. Importing its saved output keeps collection evidence tied to a window
without pretending that a list card proves a body or attachment was read.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from .policy import BEIJING, SEVEN_SOURCES, X_ACCOUNTS, report_window
from .staging import _write_json, save_preparation


def _source_url(source: str, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if source in X_ACCOUNTS:
        return parsed.hostname == "x.com" and parsed.path.rstrip("/").lower() == f"/{source.lower()}"
    return parsed.hostname == "wx.zsxq.com" and parsed.path.rstrip("/") == f"/group/{source}"


def _event_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=BEIJING) if parsed.tzinfo is None else parsed.astimezone(BEIJING)


def import_snapshot(root: Path, day: date, edition: str, source: str,
                    original: Path, phase: str) -> Path:
    """Store a hashed source/list audit. The result is always partial evidence."""
    if source not in SEVEN_SOURCES or phase not in ("preparation", "final"):
        raise ValueError("unknown source or phase")
    root = root.resolve()
    original = original.resolve()
    try:
        relative = original.relative_to(root)
    except ValueError as exc:
        raise ValueError("browser snapshot must be inside this project") from exc
    if not original.is_file():
        raise ValueError("browser snapshot is missing")
    raw = original.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("browser snapshot must be an object")
    captured = _event_time(data["captured_at"])
    if datetime.fromisoformat(data["captured_at"]).tzinfo is None:
        raise ValueError("capture time needs an explicit timezone")
    start, end = report_window(day, edition)
    if phase == "final" and captured < end:
        raise ValueError("final browser capture precedes the window cutoff")
    if phase == "preparation" and captured >= end:
        raise ValueError("preparation browser capture is after the cutoff")
    observed_url = data.get("url", "")
    if observed_url and not _source_url(source, observed_url):
        raise ValueError("browser URL does not identify the requested source")
    items = data.get("cards", data.get("articles"))
    if not isinstance(items, list):
        raise ValueError("snapshot has no visible list items")
    times = []
    undated = 0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("list item must be an object")
        value = item.get("date") or item.get("time")
        if value:
            times.append(_event_time(value))
        else:
            undated += 1
    issues = ["列表快照不证明正文、可见评论或附件已读"]
    if not observed_url:
        issues.append("原始快照未保存来源页面 URL")
    if undated:
        issues.append(f"{undated} 条列表缺原始时间")
    if not any(time < start for time in times):
        issues.append("未看到早于窗口起点的列表边界")
    if phase == "final" and not any(time >= end for time in times):
        issues.append("未看到窗口终点后的列表边界")
    value = {
        "source": source, "phase": phase, "captured_at": captured.isoformat(),
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "observed_url": observed_url or None,
        "original": {"path": relative.as_posix(), "sha256": hashlib.sha256(raw).hexdigest()},
        "visible_list_items": len(items),
        "window_list_items": sum(start <= time < end for time in times),
        "earlier_boundary_seen": any(time < start for time in times),
        "later_boundary_seen": any(time >= end for time in times),
        "issues": issues, "complete": False,
    }
    output = root / "work" / "browser-captures" / f"{day}-{edition}" / phase / f"{source}.json"
    _write_json(output, value)
    return output


def save_browser_preparation(root: Path, day: date, edition: str,
                             prepared_at: datetime, snapshots: dict[str, Path],
                             draft: Path | None = None) -> Path:
    """Connect real exported snapshots to the existing pre-delivery checkpoint."""
    imported = {source: [import_snapshot(root, day, edition, source, path, "preparation")]
                for source, path in snapshots.items()}
    for paths in imported.values():
        record = json.loads(paths[0].read_text(encoding="utf-8"))
        if prepared_at.tzinfo is None or datetime.fromisoformat(
                record["captured_at"]) > prepared_at.astimezone(BEIJING):
            raise ValueError("browser capture occurred after preparation time")
    return save_preparation(root, day, edition, prepared_at, imported, draft)
