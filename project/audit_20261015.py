"""Summarize recovered list evidence for the manual 2026-10-15 evening run."""

import json
from datetime import datetime
from pathlib import Path

from digest.evidence import audit
from digest.policy import BEIJING

ROOT = Path(__file__).resolve().parent
result = audit(ROOT / "evidence", datetime(2026, 10, 15, tzinfo=BEIJING), "evening")
out = ROOT / "evidence" / "2026-10-15-2100-list-audit.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"窗口：{result['start']} 至 {result['end']}")
for source, entry in result["sources"].items():
    print(f"{source}: {entry['window_list_entries']} 条列表记录")
print("仅核对列表；详情、评论、附件及完整性尚未通过。")
print(f"审计记录：{out}")
