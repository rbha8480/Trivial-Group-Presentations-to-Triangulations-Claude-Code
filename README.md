# Triangulation search code

Supplementary source code for the thesis appendix describing the search that
reduced a 98-pentachoron triangulation of a closed homotopy 4-sphere $M$ down
to 8 pentachora, using [Regina](https://regina-crge.github.io) (run via its
`regina-python` launcher, tested against Regina 8.0).

The appendix itself explains what each script does, how they chain together,
the manual hand-offs between stages, and what to change to adapt this to a
different manifold. This repository exists so the code is directly runnable,
rather than relying on copy-pasting it out of a PDF.

## Files

| file | role |
|---|---|
| `search_common.py` | shared invariant-check / atomic-publish / sweep helpers used by the four search scripts below |
| `ball_basin_hopping.py` | basin hopping on the homotopy 4-ball $B$ |
| `closed_basin_hopping.py` | basin hopping on the closed sphere $M$ |
| `melt_farm.py` | generates independent basins by subdivide-then-resimplify |
| `basin_burrow.py` | melt / dive / capped-exhaustive-burrow search over the basin library |
| `verify_invariants.py` | independently re-checks a saved triangulation's invariants and $\pi_1$ |
| `export_gluings.py` | converts a compact isoSig into a readable `fromGluings(...)` source listing |

## Running it

Each search script is a long-running worker, meant to be launched several
times in parallel against one shared project directory:

```sh
for i in 0 1 2 3 4 5 6 7; do
    nohup /usr/local/bin/regina-python closed_basin_hopping.py /path/to/project $i 8 &
done
```

See each script's own module docstring for its specific arguments, and the
thesis appendix for the full pipeline order and the manual hand-off steps
between stages.
