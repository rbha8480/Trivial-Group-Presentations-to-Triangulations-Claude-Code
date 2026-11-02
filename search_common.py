"""
search_common.py -- pure helpers shared by every forward-search script (ball and
closed alike): ball_basin_hopping.py, closed_basin_hopping.py, melt_farm.py, and
basin_burrow.py. backward_common.py also uses closed_sphere_invariants_hold and
read_best_size, since its target triangulation must satisfy the same check.

What's here is deliberately narrow: the mechanical "is this record file a new
low, does the candidate still verify, write it atomically" logic that was
previously four near-identical copies, one per script; the one invariant check
(closed homotopy 4-sphere) that was four more copies of the same five lines;
and the melt/dive excursion + descent helpers shared between basin_burrow.py
and backward_common.py. Nothing here differs between the ball case and the
closed case except which invariant-check function gets passed in; the ball
case's own check stays local to ball_basin_hopping.py precisely because it
genuinely differs (one boundary component, chi=1, the boundary itself must be
a homotopy 3-sphere) rather than being a copy of this.
"""
import regina, os, random


def closed_sphere_invariants_hold(tri):
    """Hard gate: must still certify as the closed homotopy 4-sphere M (valid,
    connected, orientable, closed, chi=2, H1=H2=0)."""
    return (tri.isValid() and tri.isConnected() and tri.isOrientable() and tri.isClosed()
            and tri.eulerCharTri() == 2
            and str(tri.homology(1)) == '0' and str(tri.homology(2)) == '0')


def read_best_size(size_path):
    try:
        return int(open(size_path).read())
    except Exception:
        return 10**9


def publish(tri, best_path, size_path, worker_id, invariants_hold, log):
    """Try to overwrite the shared record with `tri`. Re-checks the shared size
    file immediately before writing (another worker may have beaten us to it
    since we last looked) and independently re-verifies `invariants_hold(tri)` --
    a result is NEVER trusted just because our own search produced it. Write-
    then-rename makes the swap atomic, so a reader can never see a half-written
    file. Returns True on success; callers add their own success-log line and
    any extra per-script bookkeeping (e.g. a permanent per-size record file)."""
    size = tri.size()
    if size >= read_best_size(size_path):
        return False
    if not invariants_hold(tri):
        log('REJECT size=%d invariants failed' % size)
        return False
    tmp_path = best_path + '.w%s' % worker_id
    open(tmp_path, 'w').write(tri.isoSig())
    os.replace(tmp_path, best_path)
    open(size_path, 'w').write(str(size))
    return True


def sweep(count, get, *try_moves):
    """One descending scan over 0..count()-1 (recomputing count() each step,
    since a successful move shrinks the triangulation and renumbers what's
    left): at each index, try each of `try_moves` in order and stop at the
    first that succeeds. Returns True the moment any move anywhere in the scan
    succeeds (so the caller can re-scan from the top with the new, smaller
    triangulation); False if nothing in the whole scan applied. Scanning
    high-to-low means a successful move's renumbering can never cause the scan
    to skip over a still-reducible piece further down."""
    for i in range(count() - 1, -1, -1):
        if i >= count():
            break
        piece = get(i)
        if any(move(piece) for move in try_moves):
            return True
    return False


def uphill_excursion(tri, num_moves):
    """`num_moves` successful moves, mixed 50% 2-4 (grows by one), 35% 3-3
    (neutral), 15% 4-4 (neutral) -- perturbs a basin before a melt, or explores
    further from one before a longer descent. No explicit lock-in step (unlike
    kick() in the basin-hopping scripts): what follows (subdivide, or a
    multi-round simplify_and_descend) scrambles the combinatorics thoroughly
    on its own."""
    done = 0
    attempts = 0
    while done < num_moves and attempts < 40 * num_moves:
        attempts += 1
        r = random.random()
        try:
            if r < 0.5:
                applied = tri.pachner(tri.tetrahedron(random.randrange(tri.countTetrahedra())))
            elif r < 0.85:
                applied = tri.pachner(tri.triangle(random.randrange(tri.countTriangles())))
            else:
                applied = tri.move44(tri.edge(random.randrange(tri.countEdges())))
        except Exception:
            applied = False
        if applied:
            done += 1


def simplify_and_descend(tri, rounds=4):
    """simplify(), then up to `rounds` extra passes of (light 3-3 shuffle +
    simplify()) to re-route around whatever the first pass missed, keeping the
    smallest copy seen. Stops early once a round shrinks nothing."""
    tri.simplify()
    best = regina.Triangulation4(tri)
    for _ in range(rounds):
        size_before = tri.size()
        for _ in range(2 * size_before):
            tri.pachner(tri.triangle(random.randrange(tri.countTriangles())))
        tri.simplify()
        if tri.size() < best.size():
            best = regina.Triangulation4(tri)
        if tri.size() >= size_before:
            break
    return best
