"""Small, self-contained renderer for the report Markdown subset."""

from __future__ import annotations

import html
import re

from .policy import report_issues


STYLE = """
:root{color-scheme:light}*{box-sizing:border-box}
body{margin:0;background:#f3f6f8;color:#20364a;font:17px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1050px;margin:32px auto;padding:44px 54px;background:#fff;box-shadow:0 4px 26px #15334c12}
h1{font-size:30px;line-height:1.3;margin:0 0 24px;color:#173e56}
h2{font-size:23px;margin:44px 0 20px;padding-bottom:10px;border-bottom:1px solid #d7e1e8;color:#173e56}
h3{font-size:19px;margin:25px 0 12px;color:#21475f}
p{margin:12px 0 18px;text-indent:0;padding-left:0}
ol{margin:12px 0 24px;padding-left:1.7em}li{padding-left:.2em;margin:0 0 17px}li p{margin:0}
strong{color:#173e56}a{color:#286ba4;text-decoration:none;border-bottom:1px solid #9dbbd0}
table{border-collapse:collapse;width:100%;margin:18px 0 22px;font-size:15px}th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #dce5eb}th{background:#eaf1f5}
blockquote{margin:16px 0;padding:0 0 0 16px;border-left:3px solid #9dbbd0;color:#50677b}
@media(max-width:700px){body{font-size:16px}main{margin:0;padding:22px 18px}h1{font-size:25px}h2{font-size:21px}}
"""


def inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", lambda m: f'<a href="{m.group(2)}" rel="noopener noreferrer">{m.group(1)}</a>', escaped)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def render(markdown: str) -> str:
    issues = report_issues(markdown)
    if issues:
        raise ValueError("；".join(issues))
    lines = markdown.splitlines()
    out: list[str] = []
    list_open = False
    table_open = False
    for line in lines:
        line = line.strip()
        ordered = re.fullmatch(r"\d+\.\s+(.+)", line)
        is_table = line.startswith("|") and line.endswith("|")
        if list_open and not ordered:
            out.append("</ol>")
            list_open = False
        if table_open and not is_table:
            out.append("</table>")
            table_open = False
        if not line:
            continue
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif ordered:
            if not list_open:
                number = int(line.split(".", 1)[0])
                out.append("<ol>" if number == 1 else f'<ol start="{number}">')
                list_open = True
            out.append(f"<li>{inline(ordered.group(1))}</li>")
        elif is_table:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if not table_open:
                out.append("<table>")
                table_open = True
                tag = "th"
            else:
                tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{inline(cell)}</{tag}>" for cell in cells) + "</tr>")
        else:
            out.append(f"<p>{inline(line)}</p>")
    if list_open:
        out.append("</ol>")
    if table_open:
        out.append("</table>")
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + STYLE + '</style><main>' + "\n".join(out) + "</main></html>"
