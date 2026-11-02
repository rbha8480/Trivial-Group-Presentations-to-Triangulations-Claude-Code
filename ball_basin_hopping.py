"""
ball_basin_hopping.py  (annotated twin of ../bh.py — same algorithm, same behaviour)

Basin hopping on the homotopy 4-ball B: escape a local minimum by deliberately
making it worse first.
    1. KICK uphill: K successful 2-4 Pachner moves (each one pentachoron bigger).
    2. LOCK IN each kick with a burst of size-neutral "scrambling" moves (3-3,
       4-4, openBook) -- otherwise the degree-4 edge a 2-4 move just created is
       exactly what a 4-2 move needs, and the next greedy pass immediately
       undoes the kick.
    3. DESCEND greedily from the kicked-and-scrambled state.
    4. ACCEPT if it's a new record, or within an acceptance WINDOW of the
       current best (keep exploring sideways); otherwise discard and kick
       again from the last accepted state.

GENUINE MOVES ONLY: every operation (collapseEdge, pachner, move20, move44,
shellBoundary, openBook) is a real Regina move, so every intermediate state is
honestly a triangulation of B -- but a published result is independently
re-verified against invariants_hold() regardless, never trusted just because
the search that produced it is believed correct. See search_common.py for the
shared read_best_size/publish/sweep machinery used here and by the other
forward-search scripts.

Multiple WORKER_ID processes run this script in parallel against one shared
record file (BEST_BALL.isosig), each at a different point on an
explore<->exploit ladder (KICK0, WINDOW below), periodically adopting whatever
the best worker has published.

usage:   /usr/local/bin/regina-python ball_basin_hopping.py DIR WORKER_ID HOURS
launch (8 cores):
    for i in 0 1 2 3 4 5 6 7; do
        nohup /usr/local/bin/regina-python ball_basin_hopping.py DIR $i 8 &
    done
"""
import regina, sys, os, time, random

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import search_common as common

PROJECT_DIR  = sys.argv[1]
WORKER_ID    = int(sys.argv[2])
BUDGET_HOURS = float(sys.argv[3])

BEST_PATH = os.path.join(PROJECT_DIR, 'BEST_BALL.isosig')
SIZE_PATH = BEST_PATH + '.size'

random.seed(os.getpid() * 100003 + WORKER_ID)
log_file = open(os.path.join(PROJECT_DIR, 'bh%d.log' % WORKER_ID), 'a', buffering=1)
def log(msg):
    log_file.write('%s w%d %s\n' % (time.strftime('%H:%M:%S'), WORKER_ID, msg))

# Explore/exploit ladder (8 workers): small kicks + tight window = exploit near
# the current best; large kicks + loose window = explore further afield.
KICK_LADDER   = (10, 15, 20, 30, 40, 60, 80, 120)
WINDOW_LADDER = ( 0,  1,  2,  3,  4,  6,  8,  12)
KICK0  = KICK_LADDER[WORKER_ID % 8]
WINDOW = WINDOW_LADDER[WORKER_ID % 8]


def invariants_hold(tri):
    """Must certify as the homotopy 4-ball B: one boundary component, chi=1,
    trivial H1/H2 on B and on its boundary (which must itself be a homotopy
    3-sphere). Genuinely different from the closed-M case in search_common.py,
    so it stays local here rather than shared."""
    if not (tri.isValid() and tri.isConnected() and tri.isOrientable()):
        return False
    if tri.countBoundaryComponents() != 1 or tri.eulerCharTri() != 1:
        return False
    if str(tri.homology(1)) != '0' or str(tri.homology(2)) != '0':
        return False
    boundary = tri.boundaryComponent(0).build()
    return boundary.eulerCharTri() == 0 and str(boundary.homology()) == '0'


def greedy_descend(tri):
    """Sweep edges, then vertices, then triangles, then boundary pentachora;
    restart the whole sweep after any successful move, stop once a full pass
    changes nothing. Terminates because every move strictly shrinks tri."""
    for _ in range(20000):
        if common.sweep(tri.countEdges, tri.edge, tri.collapseEdge, tri.pachner, tri.move20):
            continue
        if common.sweep(tri.countVertices, tri.vertex, tri.move20, tri.pachner):
            continue
        if common.sweep(tri.countTriangles, tri.triangle, tri.move20):
            continue
        if not common.sweep(tri.size, tri.pentachoron, tri.shellBoundary):
            return


def scramble(tri, count):
    """`count` size-neutral moves (65% 3-3, 27% 4-4, 8% openBook -- mix is
    empirical) to lock in a kick so the obvious reverse move can't undo it."""
    done = 0
    for _ in range(20 * count):
        if done >= count:
            return
        r = random.random()
        if r < 0.65:
            if tri.pachner(tri.triangle(random.randrange(tri.countTriangles()))):
                done += 1
        elif r < 0.92:
            if tri.move44(tri.edge(random.randrange(tri.countEdges()))):
                done += 1
        else:
            if tri.openBook(tri.tetrahedron(random.randrange(tri.countTetrahedra()))):
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
        log('PUBLISH %d (verified chi=1 H1=0 H2=0, bdry chi=0 H1=0)' % size)
        return True
    return False


# ---- main basin-hopping loop ----------------------------------------------------
current = regina.Triangulation4.fromIsoSig(open(BEST_PATH).read().strip())
greedy_descend(current)
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

    if time.time() - last_improved_at > 1800:
        kick_size = min(kick_size * 2, 240)
        last_improved_at = time.time()
        log('escalate K=%d' % kick_size)

    if time.time() - last_logged_at > 600:
        last_logged_at = time.time()
        log('it=%d cur=%d best=%d K=%d' % (iterations, current.size(), best_size, kick_size))

log('EXIT it=%d best=%d' % (iterations, best_size))
