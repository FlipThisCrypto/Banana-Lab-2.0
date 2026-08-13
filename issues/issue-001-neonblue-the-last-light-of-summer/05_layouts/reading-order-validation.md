# Issue 001 — Reading Order Validation

Reading order is **left to right, top to bottom**, on every page, with no
exceptions and no arrows.

## Automated check

`scripts/production/render_layout_thumbnails.py` validates every page:

```
geometry OK: no overlaps, no escapes, no repeated grids
```

The reading-order check (`check_reading_order`) walks the panels of each page in
script order and asserts:

1. A panel in the same row as its predecessor starts to its **right**.
2. A panel in a new row starts **at or below the bottom** of its predecessor.

**Result: 22 of 22 pages pass.**

### Why this check exists

The layout generator originally varied page shapes by reversing the row plan,
which reordered the panels. Pages rendered as attractive irregular grids while
telling the story out of sequence — page 2 read 6, 4, 5, 2, 3, 1.

It looked fine in a thumbnail. It was unreadable as a comic.

The check now runs on every build, and the generator only uses row plans that
consume panel indices in ascending order. Visual variety comes from **how rows
are grouped**, never from resequencing panels.

## Panel sequence integrity

Independently verified: on all 22 pages, the panel IDs in the layout spec appear
in ascending order and match the panel script exactly.

```
pages with scrambled panel order: 0
```

## Ambiguity risks by page

Irregular grids create ambiguity when two panels start at a similar vertical
position. Reviewed page by page:

| Page | Shape | Risk | Mitigation |
|---|---|---|---|
| 1 | Wide anchor over a pair, then a wide | Low | The pair is clearly one row |
| 2 | Six panels, mixed rows | **Medium** | Two side-by-side rows; gutters must stay even |
| 3 | Tall left with quad right | **Medium** | The tall panel is full-height for its rows |
| 7 | Seven panels | **High** | Dense page; row boundaries must be unmistakable |
| 11 | Splash | None | One panel |
| 17 | Two stacked | None | Unambiguous |
| 18 | Seven panels | **High** | Same as page 7 |
| 19 | Two stacked | None | Unambiguous |

The four medium and high-risk pages need a human read-through at final size
before layout approval. Automated geometry cannot judge whether a gutter *reads*
as a row boundary.

## Gutters and the row-boundary rule

The generator uses a 1.2 percent within-row gutter. On pages 7 and 18 the
between-row gutter is **2.4 percent** — twice the within-row gap — so row
boundaries read as groups rather than as one dense field.

**Owner ruling, 2026-08-13:** apply the denser-row treatment on pages 7 and 18
only. Not issue-wide.

## Page-turn integrity

Every page ends on a panel that motivates the turn. Verified against the script:
no page ends mid-exchange, and no balloon runs across a page boundary.

## Page-11 turn lock

The 28-page book is: cover (1, recto), inside front (2, verso), story pages
3–24. Story page N is physical page N+2. Odd physical pages are recto.

Story page 11 is physical page 13, **recto**. Page 10 is verso. The splash
arrives after the turn.

This is a hard validation rule (`book_assembly.page_turn_locks`). Adding or
removing a front-matter page fails `validate`. That is the approval
requirement: the reveal cannot silently move onto a left-hand page.

## Open items

1. Human read-through of pages 2, 3, 7 and 18 **at final print size**. The
   validator identifies these; geometry cannot judge whether a gutter *reads*
   as a row boundary. Thumbnails were regenerated with the new grids.
