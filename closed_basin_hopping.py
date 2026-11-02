"""
closed_basin_hopping.py  (annotated twin of ../bhc.py — same algorithm, same behaviour)

Same basin-hopping idea as ball_basin_hopping.py (read that file's header first)
but for the CLOSED homotopy 4-sphere M instead of the bounded ball B:

  - invariants_hold() checks the closed-manifold signature instead of the ball's
    (shared with the other closed-M scripts via search_common.py).
  - scramble() drops openBook and greedy_descend() drops the shellBoundary pass
    -- both only ever apply to a boundary facet, and M has none.
  - polish() is new: Regina's own simplify() (internal 3-3 retries this hand-
    rolled greedy_descend doesn't attempt) costs ~10s at the sizes this search
    spends most of its time near, too slow to run after every kick -- so it
    only runs as a second pass on states that already beat the record.

Kick ladder and window sit a size notch below the ball version: M's record is
smaller, and smaller triangulations have proportionally fewer places for a kick
to land, so smaller kicks dominate the empirically useful range.

usage:   /usr/local/bin/regina-python closed_basin_hopping.py DIR WORKER_ID HOURS
launch (8 cores):
    for i in 0 1 2 3 4 5 6 7; do
        nohup /usr/local/bin/regina-python closed_basin_hopping.py DIR $i 8 &
    done
"""
import regina, sys, os, time, random

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import search_common as common

PROJECT_DIR  = sys.argv[1]
WORKER_ID    = int(sys.argv[2])
BUDGET_HOURS = float(sys.argv[3])

BEST_PATH = os.path.join(PROJECT_DIR, 'BEST_M2.isosig')
SIZE_PATH = BEST_PATH + '.size'

random.seed(os.getpid() * 100003 + WORKER_ID)
log_file = open(os.path.join(PROJECT_DIR, 'bhc%d.log' % WORKER_ID), 'a', buffering=1)
def log(msg):
    log_file.write('%s w%d %s\n' % (time.strftime('%H:%M:%S'), WORKER_ID, msg))

invariants_hold = common.closed_sphere_invariants_hold

# Small kicks dominate here (probe-measured) — see module docstring.
KICK_LADDER   = ( 2,  3,  4,  6,  8, 12, 20, 32)
WINDOW_LADDER = ( 0,  1,  1,  2,  2,  3,  4,  6)
KICK0  = KICK_LADDER[WORKER_ID % 8]
WINDOW = WINDOW_LADDER[WORKER_ID % 8]


def greedy_descend(tri):
    """Sweep edges, then vertices, then triangles; restart after any success,
    stop once a full pass changes nothing. No shellBoundary pass -- M is closed."""
    for _ in range(20000):
        if common.sweep(tri.countEdges, tri.edge, tri.collapseEdge, tri.pachner, tri.move20):
            continue
        if common.sweep(tri.countVertices, tri.vertex, tri.move20, tri.pachner):
            continue
        if not common.sweep(tri.countTriangles, tri.triangle, tri.move20):
            return


def polish(tri):
    """simplify() + greedy_descend(), alternating until a round shrinks nothing.
    Only called on candidate improvements -- simplify() is too slow for the
    inner loop."""
    for _ in range(10):
        size_before = tri.size()
        tri.simplify()
        greedy_descend(tri)
        if tri.size() >= size_before:
            return


def scramble(tri, count):
    """`count` size-neutral moves (3-3, 4-4 -- no openBook, M is closed) to lock
    in a kick so the obvious reverse move can't immediately undo it."""
    done = 0
    for _ in range(20 * count):
        if done >= count:
            return
        if random.random() < 0.7:
            if tri.pachner(tri.triangle(random.randrange(tri.countTriangles()))):
                done += 1
        else:
            if tri.move44(tri.edge(random.randrange(tri.countEdges()))):
                done += 1


def kick(tri, k):
    """k successful uphill 2-4 moves, each locked in by scramble()."""
    done = 0
    for _ in range(40 * k):
        if done >= k:
            return
        if tri.pachner(tri.tetrahedron(random.randrange(tri.countTetrahedra()))):
            done += 1
            scramble(tri, 12)


def publish(tri):
    size = tri.size()
    if common.publish(tri, BEST_PATH, SIZE_PATH, WORKER_ID, invariants_hold, log):
        log('PUBLISH %d (verified closed chi=2 H1=0 H2=0)' % size)
        return True
    return False


# ---- main basin-hopping loop ----------------------------------------------------
current = regina.Triangulation4.fromIsoSig(open(BEST_PATH).read().strip())
greedy_descend(current)
if not invariants_hold(current):
    log('FATAL bad seed')
    sys.exit(1)

best_size = min(current.size(), common.read_best_size(SIZE_PATH))
publish(current)

kick_size = KICK0
deadline = time.time() + 3600 * BUDGET_HOURS
iterations = 0
last_improved_at = time.time()
last_logged_at = 0.0
log('start size=%d K0=%d W=%d' % (current.size(), KICK0, WINDOW))

while time.time() < deadline:
    iterations += 1
    trial = regina.Triangulation4(current)
    kick(trial, kick_size)
    greedy_descend(trial)
    if trial.size() < best_size:
        polish(trial)
    trial_size = trial.size()

    if trial_size < best_size:
        if publish(trial):
            best_size = trial_size
        current = trial
        kick_size = KICK0
        last_improved_at = time.time()
    elif trial_size <= best_size + WINDOW:
        current = trial

    if iterations % 100 == 0:
        shared_best = common.read_best_size(SIZE_PATH)
        if shared_best < best_size:
            try:
                current = regina.Triangulation4.fromIsoSig(open(BEST_PATH).read().strip())
                best_size = shared_best
                kick_size = KICK0
            except Exception:
                pass

    if time.time() - last_improved_at > 1200:
        kick_size = min(kick_size * 2, 160)
        last_improved_at = time.time()
        log('escalate K=%d' % kick_size)

    if time.time() - last_logged_at > 600:
        last_logged_at = time.time()
        log('it=%d cur=%d best=%d K=%d' % (iterations, current.size(), best_size, kick_size))

log('EXIT it=%d best=%d' % (iterations, best_size))
