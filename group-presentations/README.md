# Group presentation search (GAP and Regina)

A second, independent line of work alongside the triangulation search in the
repo root: searching, directly at the level of group presentations, for short
2-generator/2-relator ("Miller-Schupp style") presentations
$\langle a, b \mid a^{-1} b^n a b^{-(n+1)},\ w a^{-1} \rangle$ that resist
simplification, and separately watching Regina's own triangulation-driven
simplification (Tietze transformations via `fundamentalGroup()`) chase similar
targets. The three `.g` files use [GAP](https://www.gap-system.org/) (tested
against GAP 4.15.1); the three `.py` files are meant to be pasted into an
interactive `regina-python` session rather than run standalone.

## Files

| file | role |
|---|---|
| `find_resistant_presentation.g` | exhaustive search by increasing relator length for a presentation that survives repeated Tietze-simplify-and-escape attempts across multiple independent restarts |
| `find_resistant_presentation_random.g` | the cheaper, random-sampling version of the same search: one `SimplifiedFpGroup` call per candidate, no multi-restart robustness check |
| `escape_tietze_minimum.g` | interactive escape-and-simplify loop on one specific presentation, watched and interrupted by hand |
| `escalating_simplify.py` | Regina-side: an escalating `simplifyUpDown` ladder (n = 50, 100, ..., 1000) paired with greedy `simplify()` at each tier |
| `search_for_target_presentation.py` | Regina-side: searches a committed simplification run for a triangulation whose fundamental group matches a specific target presentation shape |
| `committed_drift_oneliner.py` | the simplest possible committed-drift probe: `simplifyUpDown(..., alwaysModify=True)` in a loop, printing size after every step |

## A caveat worth reading before reusing these

`escalating_simplify.py`, `search_for_target_presentation.py`, and
`committed_drift_oneliner.py` all call `simplifyUpDown` with
`alwaysModify=True` ("committed drift"): the triangulation keeps whatever the
up-down search returns, even if it's larger than before. That's what lets
these scripts escape local minima a plain `simplify()` cannot — but none of
them anchor to the best triangulation seen or snap back if the drift wanders
too far upward, so on a long unattended run they can in principle drift
uphill indefinitely. They were used interactively, watched and interrupted by
hand, which is a reasonable way to use this pattern — but if you adapt one of
these into an unattended, multi-hour background worker, pair the committed
step with an anchor-to-best/snap-back safeguard, the way the basin-hopping
scripts in the repo root do.
