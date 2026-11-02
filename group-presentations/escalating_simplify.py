"""
escalating_simplify.py  (annotated twin of ../simplify.py -- same algorithm,
same behaviour)

A hand-rolled simplification ladder: greedy simplify() to a fixed point, then
Regina's simplifyUpDown(n, 3n) -- which allows the triangulation to grow up to
n pentachora before coming back down, escaping local minima that plain
simplify() cannot -- at successively larger n (50, 100, ..., 1000), running
each tier's up-down pass to its own fixed point before moving to the next.

CAVEAT (kept here rather than silently fixed, since this is an annotated twin
of code that was actually used): simplifyUpDown here is called with
alwaysModify left at its default (False, "only keep an improving result"),
unlike the committed (alwaysModify=True) drift pattern in
committed_drift_oneliner.py. That makes this version naturally self-limiting
-- unlike a committed drift, it cannot wander uphill forever -- at the cost of
being more conservative about what counts as progress at each tier.

Meant to be pasted into an interactive `regina-python` session (or a script
run with `regina-python -i`) where a Triangulation4 is already loaded into a
variable, then called as custom_simplify(tri).

usage (interactive):
    custom_simplify(tri)
"""


def custom_simplify(tri):
    print('simplify', tri)

    res = True
    while res:                       # plain greedy simplify() to its own fixed point first
        tri.simplify()
        res = tri.simplifyUpDown()   # default n: Regina's own built-in up-down budget

    for n in [50, 100, 150, 200, 250, 400, 500, 600, 700, 800, 900, 1000]:
        print('running up down simplify with parameter n=', n)
        res = True
        while res:
            tri.simplify()
            res = tri.simplifyUpDown(n, 3 * n)   # allow growth up to n, descend with budget 3n

    return tri
