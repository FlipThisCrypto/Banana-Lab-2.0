"""Static HTML production dashboard.

A view. It reads the filesystem and renders what it finds. It has no server, no
state and no write path - open the file, see where the work stands.

The dashboard shows a stage as complete only when its evidence exists, and shows
a human gate as approved only when the approval record says so. It cannot make
either true.
"""

from __future__ import annotations

from pathlib import Path

from app.core import paths
from app.services.issue_status import IssueState, all_issues

STAGE_CLASS = {"complete": "done", "partial": "partial", "not_started": "todo"}

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1.5rem; line-height: 1.5;
  font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  background: #12131a; color: #e7e8ee;
}
.wrap { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; letter-spacing: -.01em; }
.sub { color: #9aa0b4; margin: 0 0 2rem; font-size: .9rem; }
.issue { background: #1a1c26; border: 1px solid #272a37; border-radius: 10px;
         padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }
.issue h2 { font-size: 1.15rem; margin: 0 0 .2rem; }
.meta { color: #9aa0b4; font-size: .82rem; margin-bottom: 1rem; }
.bar { height: 6px; background: #272a37; border-radius: 3px; overflow: hidden; margin-bottom: 1rem; }
.bar > i { display: block; height: 100%; background: linear-gradient(90deg,#4a7dd6,#5fc9a8); }
ol { list-style: none; margin: 0; padding: 0; }
li { display: flex; align-items: baseline; gap: .6rem; padding: .32rem 0;
     border-bottom: 1px solid #21232e; font-size: .92rem; }
li:last-child { border-bottom: 0; }
.mark { width: 1.5rem; flex: 0 0 1.5rem; font-family: ui-monospace, monospace; font-size: .8rem; }
.done  .mark { color: #5fc9a8; }
.partial .mark { color: #e0b054; }
.todo  .mark { color: #565b70; }
.todo  .name { color: #8b90a4; }
.gate { font-size: .72rem; padding: .08rem .45rem; border-radius: 999px;
        border: 1px solid #3a3f52; color: #b6bccd; }
.gate.ok { border-color: #2f6b56; color: #6fd6b0; }
.gate.wait { border-color: #6b5a2f; color: #e0b054; }
.next { margin-top: 1rem; padding: .75rem 1rem; background: #21242f;
        border-left: 3px solid #4a7dd6; border-radius: 4px; font-size: .88rem; }
.blocked { border-left-color: #d66a6a; }
.blocked b { color: #ffb0b0; }
footer { color: #6b7086; font-size: .78rem; margin-top: 2rem; }
code { font-family: ui-monospace, monospace; font-size: .85em; color: #b6bccd; }
"""


def render_issue(issue: IssueState) -> str:
    total = len(issue.stages)
    done = issue.completed_count
    pct = int(done / total * 100) if total else 0

    rows = []
    for state in issue.stages:
        cls = STAGE_CLASS[state.status]
        mark = {"done": "[x]", "partial": "[~]", "todo": "[ ]"}[cls]
        gate = ""
        if state.stage.human_gate:
            if state.approved:
                gate = '<span class="gate ok">approved</span>'
            else:
                gate = '<span class="gate wait">awaiting approval</span>'
        rows.append(
            f'<li class="{cls}"><span class="mark">{mark}</span>'
            f'<span class="name">{state.stage.title}</span>{gate}</li>'
        )

    current = issue.current_stage
    if current is None:
        nxt = '<div class="next">All stages complete.</div>'
    else:
        blockers = issue.blockers()
        cls = "next blocked" if blockers else "next"
        detail = "".join(f"<br><b>blocked:</b> {b}" for b in blockers)
        nxt = (
            f'<div class="{cls}"><b>Next:</b> {current.stage.title} &mdash; '
            f"{current.stage.purpose}{detail}</div>"
        )

    return (
        f'<section class="issue"><h2>{issue.issue_id}: {issue.title}</h2>'
        f'<p class="meta">{done} of {total} stages complete</p>'
        f'<div class="bar"><i style="width:{pct}%"></i></div>'
        f"<ol>{''.join(rows)}</ol>{nxt}</section>"
    )


def build_html() -> str:
    issues = all_issues()
    body = "".join(render_issue(i) for i in issues) or "<p>No issues found.</p>"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Banana Lab 2.0 - Production Dashboard</title>"
        f"<style>{CSS}</style></head><body><div class=\"wrap\">"
        "<h1>Banana Lab 2.0</h1>"
        "<p class=\"sub\">Production dashboard. Generated from the filesystem &mdash; "
        "a stage shows complete only when its evidence exists.</p>"
        f"{body}"
        "<footer>Regenerate with <code>python -m app.cli.main dashboard</code>. "
        "This page cannot approve anything.</footer>"
        "</div></body></html>"
    )


def write_dashboard(path: Path) -> Path:
    paths.assert_safe_write_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_html(), encoding="utf-8")
    return path
