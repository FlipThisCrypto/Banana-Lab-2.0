# Issue 001 — Storyboard Notes

Thumbnails: `page-thumbnails/page_01.png` … `page_22.png`
Contact sheet: `storyboard-contact-sheet.png`

Generated from the layout spec by
`scripts/production/render_layout_thumbnails.py`. The renderer also validates
geometry — overlaps, panels escaping the live area, repeated grids and reading
order — and fails if any of those break.

Colour in the thumbnails encodes panel shape; darker fills mark silent panels;
lighter fills mark anchor panels. The page background is the page frame colour
from the layout spec.

---

## Pacing

| Act | Pages | Panels | Density | Feel |
|---|---|---:|---:|---|
| One — arrival and failure | 1–7 | 37 | 5.3 / page | Establishing, then accelerating |
| Two-A — the pattern | 8–13 | 26 | 4.3 / page | Investigation, then the splash |
| Two-B — the wound | 14–18 | 21 | 4.2 / page | Slowing hard |
| Three — choice and work | 19–22 | 19 | 4.8 / page | Two-panel stop, then action |

The shape is deliberate: dense pages when the festival is busy and the failure is
spreading, sparse pages when the story turns inward, then a two-panel page for
the decision itself.

## The rhythm extremes

| Page | Panels | Why |
|---|---:|---|
| **11** | **1** | Full-page splash. The page-turn reveal — the dark has a shape. The single most important background in the issue. |
| **17** | **2** | The breath after the Patch recognition. Almost entirely empty corridor. |
| **19** | **2** | The decision. Two panels and nothing else on the page. |
| **7** | **7** | The fault spreading. Fast cuts across the whole festival. |
| **18** | **7** | Countdown and discovery running against each other. |

Both seven-panel pages are flagged by the validator as above the soft maximum of
six. Both are intentional and confirmed here.

## Page turns

The strongest turns, where the reader must physically move to get the next beat:

| Turn | Effect |
|---|---|
| 10 → 11 | Camera lifts on page 10's last panel, then the splash delivers the whole pattern |
| 13 → 14 | The cyan dies, then NeonBlue explains it away |
| 17 → 18 | Held silence, then the countdown starts |
| 18 → 19 | Ends on the trapped three, opens on the decision |
| 21 → 22 | The rescue completes, then the quiet after |

## Anchor panels

One dominant panel per page carries the beat. Across the issue:

- `P07-07` — the two dark zones nearly meeting
- `P11-01` — the splash
- `P13-01` — the system responds
- `P15-02` — the relay marker
- `P18-06` — the trapped three
- `P19-01` — the decision
- `P21-03` — the rescue
- `P22-05` — the final image

## Silent panels

Nineteen panels carry no dialogue. The legacy version had none. Silence is used
for: held looks (`P02-04`, `P02-05`, `P10-02`), pure information (`P01-03`,
`P07-07`, `P11-01`), and emotional weight (`P15-03`, `P17-01`, `P17-02`,
`P19-02`, `P22-03`).

## Checks passed

Run `python scripts/production/render_layout_thumbnails.py <issue-slug>`:

- No overlapping panels on any page
- No panel escapes the live area
- No grid repeats on any page — 22 distinct grids across 22 pages
- Reading order is strictly top-to-bottom, left-to-right on every page
- Declared `area_share` agrees with box geometry within tolerance

## What thumbnails cannot show

Composition inside the box, character staging, and whether a panel actually
reads. Those are judged on the artwork, against
`docs/quality/QUALITY_STANDARD.md`.
