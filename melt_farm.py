"""
melt_farm.py  (annotated twin of ../melt.py — same algorithm, same behaviour)

Basin hopping (closed_basin_hopping.py) exhausted the then-record's basin: a
complete height-2 Pachner-move search of its neighbourhood found nothing
smaller. Stuck not because the record is minimal, but because every path out
of THAT SPECIFIC basin was explored and none descended.

The fix is to land somewhere else entirely: barycentrically SUBDIVIDE the
triangulation (~120x more pentachora, still provably the same manifold, since
subdivision is a PL-homeomorphism, not a Pachner move) and run Regina's greedy
simplify() back down. The round trip lands in a basin essentially unrelated to
the one you started in. Do it thousands of times and every landing within
reach of the record is a fresh, independent sample of "what the record size
actually looks like" -- banked to land<N>.sigs for basin_burrow.py to later
probe one by one with bounded exhaustive search, looking for the one that
admits a reduction. Each round trip is cheap (~1.5s); this script's whole job
is throughput.

GENUINE OPERATIONS ONLY: subdivide() is a PL-homeomorphism, not an
approximation; simplify()/pachner() are real Regina moves. Every publish is
independently gated regardless of what produced the candidate (see
search_common.py, shared with the other closed-M scripts).

usage:   /usr/local/bin/regina-python melt_farm.py DIR WORKER_ID HOURS
launch (8 cores):
    for i in 0 1 2 3 4 5 6 7; do
        nohup /usr/local/bin/regina-python melt_farm.py DIR $i 10 &
    done
"""
import regina, sys, os, time, random

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import search_common as common

PROJECT_DIR  = sys.argv[1]
WORKER_ID    = int(sys.argv[2])
BUDGET_HOURS = float(sys.argv[3])

BEST_PATH = os.path.join(PROJECT_DIR, 'BEST_M3.isosig')
SIZE_PATH = BEST_PATH + '.size'
landings_file = open(os.path.join(PROJECT_DIR, 'land%d.sigs' % WORKER_ID), 'a', buffering=1)
log_file      = open(os.path.join(PROJECT_DIR, 'melt%d.log' % WORKER_ID), 'a', buffering=1)
random.seed(os.getpid() * 100003 + WORKER_ID)
def log(msg):
    log_file.write('%s w%d %s\n' % (time.strftime('%H:%M:%S'), WORKER_ID, msg))

invariants_hold = common.closed_sphere_invariants_hold


def publish(tri):
    size = tri.size()
    if common.publish(tri, BEST_PATH, SIZE_PATH, WORKER_ID, invariants_hold, log):
        log('PUBLISH %d (verified closed chi=2 H1=0 H2=0)' % size)
        return True
    return False


def wander(tri):
    """Randomise the starting point before each melt (a few size-neutral 3-3
    moves, plus a 35%-chance small uphill excursion locked in by 3-3s) so
    repeated melts of the same pool member don't subdivide an identical
    triangulation. Lighter than kick() elsewhere, since subdivision scrambles
    everything regardless."""
    for _ in range(random.randrange(0, 9)):
        tri.pachner(tri.triangle(random.randrange(tri.countTriangles())))
    if random.random() < 0.35:
        for _ in range(random.randrange(1, 5)):
            tri.pachner(tri.tetrahedron(random.randrange(tri.countTetrahedra())))
            for _ in range(6):
                tri.pachner(tri.triangle(random.randrange(tri.countTriangles())))


def simplify_and_polish(tri):
    """simplify(), then up to 3 rounds of (light 3-3 reshuffle + simplify())
    to re-route around whatever the first pass missed, keeping the smallest
    copy seen. Stops as soon as a round shrinks nothing."""
    tri.simplify()
    best = regina.Triangulation4(tri)
    for _ in range(3):
        size_before = tri.size()
        for _ in range(2 * size_before):
            tri.pachner(tri.triangle(random.randrange(tri.countTriangles())))
        tri.simplify()
        if tri.size() < best.size():
            best = regina.Triangulation4(tri)
        if tri.size() >= size_before:
            break
    return best


# ---- main melt-and-reseed loop --------------------------------------------------
seed_sig = open(BEST_PATH).read().strip()
seed = regina.Triangulation4.fromIsoSig(seed_sig)
if not invariants_hold(seed):
    log('FATAL bad seed')
    sys.exit(1)

best_size = min(seed.size(), common.read_best_size(SIZE_PATH))

# pool[0] is always the current best; the rest are recent distinct near-record
# landings. pool_keys is an edge-degree-sequence fingerprint, used to cheaply
# reject near-duplicate landings before they clutter the pool or the log.
pool = [seed_sig]
pool_keys = set()
deadline = time.time() + 3600 * BUDGET_HOURS
iterations = 0
num_landings = 0
last_logged_at = 0.0
log('start size=%d best=%d' % (seed.size(), best_size))

while time.time() < deadline:
    iterations += 1
    start_sig = pool[0] if (random.random() < 0.6 or len(pool) == 1) else random.choice(pool)
    tri = regina.Triangulation4.fromIsoSig(start_sig)
    wander(tri)
    if tri.size() <= 80:    # larger seeds are already complex enough; skip the melt, just descend
        tri.subdivide()
    tri = simplify_and_polish(tri)
    size = tri.size()

    if size < best_size:
        if publish(tri):
            best_size = size
            pool = [tri.isoSig()]
            pool_keys = set()
            log('it=%d NEW BEST %d' % (iterations, size))
    elif size <= best_size + 2:
        fingerprint = tri.isoSig_EdgeDegrees()
        if fingerprint not in pool_keys:
            pool_keys.add(fingerprint)
            sig = tri.isoSig()
            pool.append(sig)
            num_landings += 1
            landings_file.write(sig + '\n')
            if len(pool) > 40:
                pool.pop(1)   # keep slot 0 (= best) fixed, rotate the rest

    if iterations % 50 == 0:
        shared_best = common.read_best_size(SIZE_PATH)
        if shared_best < best_size:
            try:
                pool[0] = open(BEST_PATH).read().strip()
                best_size = shared_best
                pool_keys = set()
                pool = pool[:1]
            except Exception:
                pass

    if time.time() - last_logged_at > 600:
        last_logged_at = time.time()
        log('it=%d best=%d landings=%d pool=%d' % (iterations, best_size, num_landings, len(pool)))

log('EXIT it=%d best=%d landings=%d' % (iterations, best_size, num_landings))
