"""Audit browser-visible snapshots without treating a list card as a read article."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .policy import BEIJING, SEVEN_SOURCES, report_window


FILES = {
    "15552822254242": "short-20261015-all-loaded.json",
    "28855811424141": "base-20261015.json",
    "15554411815552": "fy-20261015.json",
    "28888222154481": "research-20261015.json",
    "Ariston_Macro": (
        "x-ariston-posts-partial.json", "x-ariston-replies.json", "x-ariston-reposts.json"
    ),
    "RayDalio": ("x-ray-posts.json", "x-ray-replies.json", "x-ray-reposts.json"),
    "CryptoHayes": ("x-hayes-posts.json", "x-hayes-replies.json"),
}


def audit(evidence_dir: Path, day: datetime, edition: str) -> dict:
    """Return counts and explicit verification gaps for one window."""
    start, end = report_window(day.date(), edition)
    result: dict = {"start": start.isoformat(), "end": end.isoformat(), "sources": {}}
    for source in SEVEN_SOURCES:
        names = FILES[source]
        if isinstance(names, str):
            names = (names,)
        records = []
        snapshots = []
        for name in names:
            path = evidence_dir / name
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            snapshots.append({"file": name, "captured_at": data.get("captured_at")})
            for item in data.get("cards", data.get("articles", [])):
                raw_time = item.get("date") or item.get("time")
                if not raw_time:
                    continue
                event_time = datetime.fromisoformat(raw_time)
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=BEIJING)
                if start <= event_time.astimezone(BEIJING) < end:
                    records.append({
                        "time": event_time.astimezone(BEIJING).isoformat(),
                        "text": item.get("text", ""),
                        "links": item.get("links", []),
                        "snapshot": name,
                    })
        # List snapshots alone do not prove comments, attachments or native IDs.
        result["sources"][source] = {
            "snapshots": snapshots,
            "window_list_entries": len(records),
            "list_entries": records,
            "detail_comments_attachments_verified": False,
        }
    result["complete"] = False
    return result
