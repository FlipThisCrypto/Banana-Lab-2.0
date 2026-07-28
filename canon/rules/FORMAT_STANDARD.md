# Comic Format Standard

**Authority: owner-mandated, 2026-07-28.** Machine-readable form:
`config/defaults/format-standards.yaml`. Enforced by
`python -m app.cli.main validate`.

This standard **outranks the story bibles on format**. Everything else in the
canon precedence order is unchanged.

---

## The standard

### Page counts

| Format | Total pages | Story pages |
|---|---|---|
| **Single-issue mainstream comic book** | 24–32 | 20–22 |
| **Trade paperback (collection)** | 96–200 (commonly 120–160) | — |
| **Original graphic novel** | 48–500 | — |

Total pages include covers and front/back matter. Story pages are the
sequential-art pages only.

### Panel counts

| Measure | Value |
|---|---|
| Average per page | **5** |
| Minimum per page | **1** (splash page) |
| Maximum per page | **6–9**, rarely above 9 |

A single issue at 22 story pages and an average of 5 lands at roughly **110
panels**.

---

## What this supersedes

The MonkeyZoo season bible, section 18, recommends *"8 pages, 20 panels, 2 to 4
panels per page"* as its standard.

**That recommendation is superseded for all new production.** It described a
short-form web strip; the owner's instruction is that finished comics are
mainstream single issues.

The season bible itself anticipates this. Section 18 states the bible *"should
remain compatible with adjustable issue lengths"* and directs that *"for longer
issues, expand investigation, relationship beats, and consequences."* Expanding
to 22 story pages is the instruction it gives, not a departure from it.

Nothing else in the season bible is affected. Story structure, character
functions, the Echo rules, the ensemble distribution and the nonnegotiable
visual canon all still apply — they now play out across 22 pages instead of 8.

---

## The non-story page budget

A 22-page story needs the rest of a 28-page book around it:

| Slot | Pages |
|---|---|
| Front cover — carries the Fiend Studios collectible stamp | 1 |
| Inside front cover — credits, recap, or full-bleed art | 1 |
| **Story** | **22** |
| Back matter — character notes, process pages, next-issue tease | 2 |
| Inside back cover | 1 |
| Back cover | 1 |
| **Total** | **28** |

28 sits comfortably inside the 24–32 window with room to move in either
direction.

---

## Rhythm is part of the standard

An average of 5 achieved by putting exactly 5 panels on every page would
reproduce the precise defect this rebuild exists to correct. The previous issue
put the same grid on six of eight pages and it is the loudest visual problem in
the whole legacy record.

So the standard also requires:

| Rule | Value |
|---|---|
| Distinct panel counts across the issue | at least 4 |
| Consecutive pages with the same panel count | at most 2 |
| Splash pages (1 panel) | at least 1 |
| Dense pages (7+ panels) | at least 1 |
| Repeated grid on consecutive pages | never |

The average is a target for the *issue*, not a quota for the *page*.

---

## How it is enforced

`validate_issue_format()` in `app/services/validation.py` reads the layout spec
and the panel script and checks:

1. Story page count is inside the format's range.
2. Total page count, including front and back matter, is inside its range.
3. Issue panel average is within tolerance of 5.
4. No page is below the minimum or above the maximum.
5. Pages above the soft maximum of 6 are reported as warnings.
6. Every rhythm rule above.

Failures are errors and block the format gate. They do not approve anything —
per ADR-005, a machine gate may only reject.

---

## Applying it to an issue

An issue declares its format in its bible:

```yaml
format: single_issue
page_count: 28        # total, including covers and matter
story_page_count: 22
target_panel_count: 110
```

`page_count` is the whole book. `story_page_count` is what the script and
layout spec cover. The layout spec contains only story pages; covers and matter
are separate deliverables.

---

## Migration note

Issue 001 was first drafted at 8 pages and 27 panels, following the season
bible. It was rebuilt to this standard on 2026-07-28. The 27-panel draft is
preserved in git history; the beats it contained are all carried forward and
expanded rather than replaced.
