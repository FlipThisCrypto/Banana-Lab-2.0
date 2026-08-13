# Iteration ledger — store-quality comic pipeline

200 sequential iterations toward a comic a reader would buy.
Round 1 = 1–50, Round 2 = 51–100, Round 3 = 101–150, Cleanup = 151–200.

This file is the record. It is not a roadmap. The next task is chosen only
after the previous commit exists.

## Round 1

| # | Status | Task | Commit |
|---|---|---|---|
| 1 | complete | Human visual-quality review as a hard gate | 1d184b1 |
| 2 | complete | Generate per-panel staging guides from script + layout | 02f5399 |
| 3 | complete | Reject composites whose cast sits in reserved lettering space | 2f28fb4 |
| 4 | complete | CLI visual command reports review state and cannot pass it | 46cb20c |
| 5 | complete | Measure festival plate horizons from the plates themselves | 11ad431 |
| 6 | complete | Calibration records are repo-relative measured files | 47ac7e0 |
| 7 | complete | Coverage report tells the truth about measured festival planes | 0c96020 |
| 8 | complete | Every newly generated plate writes a measured calibration | 5ca5953 |
| 9 | complete | Comfy client timeout 1800s so contended plates finish | e9aa2a9 |
| 10 | complete | Interiors keep their place; waist crops and 70% height cap | (this commit) |
