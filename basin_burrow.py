"""
basin_burrow.py  (annotated twin of ../dig.py — same algorithm, same behaviour)

Three strategies in one loop, traded off by weighted dice roll, over a basin
library accumulated by melt_farm.py and by this script itself:

  MELT (70%)   -- same subdivide + resimplify trick as melt_farm.py: land in a
                 fresh, essentially unrelated basin. Volume is the fuel here.
  DIVE  (25%)  -- a LONGER excursion (4-16 moves vs melt_farm's light wander)
                 from a library basin, then simplify -- explores further from
                 a known-good basin than a plain melt does.
  BURROW (5%)  -- pick ONE basin from this worker's library shard and run a
                 CAPPED exhaustive retriangulate() from it. A smaller result
                 inside the cap means that basin had a real way out --
                 publish it. Exhausting the cap with nothing found certifies
                 the whole basin dead; it never needs probing again.

SHARDING: with many workers burrowing, a shared library would get redundantly
probed. Each basin sig is assigned to exactly one worker by
`crc32(sig) % NWORKERS`, partitioning the library into disjoint shards.
refresh_library() periodically re-scans every worker's banked files (not just
this one's) so a basin melted by worker 3 but hashed to worker 7's shard still
reaches worker 7.

RECORD DISCIPLINE: every new low also gets a permanent REC_size<N>.isosig,
never touched again -- two genuine records (sizes 14 and 12) were once lost to
being silently overwritten by a smaller result within seconds; this is the fix.

GENUINE MOVES ONLY: pachner / move44 / simplify / retriangulate / subdivide
are all real Regina operations, retriangulate in particular an exhaustive BFS
over Pachner moves, not a heuristic. See search_common.py for the invariant
gate and melt/dive/descend helpers shared with the other closed-M scripts.

usage:   /usr/local/bin/regina-python basin_burrow.py DIR WORKER_ID HOURS [NWORKERS]
launch (8 cores):
    for i in 0 1 2 3 4 5 6 7; do
        nohup /usr/local/bin/regina-python basin_burrow.py DIR $i 12 8 &
    done
"""
import regina, sys, os, time, random, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import search_common as common

PROJECT_DIR  = sys.argv[1]
WORKER_ID    = int(sys.argv[2])
BUDGET_HOURS = float(sys.argv[3])
NUM_WORKERS  = int(sys.argv[4]) if len(sys.argv) > 4 else 8

BEST_PATH = os.path.join(PROJECT_DIR, 'BEST_M3.isosig')
SIZE_PATH = BEST_PATH + '.size'
TARGET_SIX_SIG = 'gvLQQQcdefdefeffya2aqbPbgaoavacafaba'   # dDelta^5, the known destination

new_basins_file = open(os.path.join(PROJECT_DIR, 'dig%d.sigs' % WORKER_ID), 'a', buffering=1)
log_file        = open(os.path.join(PROJECT_DIR, 'dig%d.log' % WORKER_ID), 'a', buffering=1)
random.seed(os.getpid() * 100003 + WORKER_ID)
def log(msg):
    log_file.write('%s w%d %s\n' % (time.strftime('%H:%M:%S'), WORKER_ID, msg))

invariants_hold = common.closed_sphere_invariants_hold


def publish(tri):
    """Atomically publish, then -- only on success -- also write the permanent
    per-size record and note if the published state is exactly the target."""
    size = tri.size()
    sig = tri.isoSig()
    if not common.publish(tri, BEST_PATH, SIZE_PATH, WORKER_ID, invariants_hold, log):
        return False
    open(os.path.join(PROJECT_DIR, 'REC_size%d.isosig' % size), 'w').write(sig)
    hit_target = ' == dDelta^5' if sig == TARGET_SIX_SIG else ''
    log('PUBLISH %d (verified closed chi=2 H1=0 H2=0)%s' % (size, hit_target))
    return True


def capped_exhaustive_probe(sig, height, node_cap, deadline):
    """Regina's retriangulate(height, 1, callback): a genuine BFS over every
    triangulation reachable from `sig` within `height` Pachner moves (4-4 is
    itself a 2-4 then 4-2, so this subsumes the plain-Pachner closure). The
    callback stops the walk (returns True) the moment it sees something
    smaller, or once node_cap/deadline is hit; otherwise it returns False,
    meaning "keep going". retriangulate() only halts early on a True, or once
    it has genuinely exhausted the whole component.

    Returned box: box['hit'] set -> found something smaller; box['capped']
    True -> gave up on budget, inconclusive; neither set -> exhausted the
    ENTIRE component below the cap and found nothing -- certified dead."""
    tri = regina.Triangulation4.fromIsoSig(sig)
    start_size = tri.size()
    box = {'visited': 0, 'hit': None, 'capped': False}

    def callback(sig_seen, tri_seen):
        box['visited'] += 1
        if tri_seen.size() < start_size:
            box['hit'] = sig_seen
            return True
        if box['visited'] >= node_cap or time.time() > deadline:
            box['capped'] = True
            return True
        return False

    tri.retriangulate(height, 1, callback)
    return box


# ---- load the shared basin library and compute this worker's shard -------------
seed_sig = open(BEST_PATH).read().strip()
seed = regina.Triangulation4.fromIsoSig(seed_sig)
if not invariants_hold(seed):
    log('FATAL bad seed')
    sys.exit(1)
best_size = min(seed.size(), common.read_best_size(SIZE_PATH))

# library = everything melt_farm.py and earlier basin_burrow.py runs (any
# worker) have banked: land*.sigs and dig*.sigs. shard = the subset this
# worker is responsible for burrowing (see SHARDING in the module docstring).
library = []
for filename in ('land_all.sigs', 'land%d.sigs' % WORKER_ID, 'dig%d.sigs' % WORKER_ID):
    path = os.path.join(PROJECT_DIR, filename)
    if os.path.exists(path):
        library += [line.strip() for line in open(path) if line.strip()]
library = sorted(set(library))
seen_in_library = set(library)

shard = [sig for sig in library if zlib.crc32(sig.encode()) % NUM_WORKERS == WORKER_ID]
random.shuffle(shard)
shard_probed = 0

pool = [seed_sig] + random.sample(library, min(300, len(library)))
pool_keys = set()


def refresh_library():
    """Re-scan every worker's land*/dig* files, not just this worker's own, so
    a basin melted elsewhere still reaches whichever shard it hashes into."""
    added = 0
    for filename in sorted(os.listdir(PROJECT_DIR)):
        if not (filename.startswith('land') or filename.startswith('dig')):
            continue
        if not filename.endswith('.sigs'):
            continue
        try:
            for line in open(os.path.join(PROJECT_DIR, filename)):
                sig = line.strip()
                if sig and sig not in seen_in_library:
                    seen_in_library.add(sig)
                    library.append(sig)
                    if zlib.crc32(sig.encode()) % NUM_WORKERS == WORKER_ID:
                        shard.append(sig)
                        added += 1
        except Exception:
            pass
    return added


# ---- main melt / dive / burrow loop ---------------------------------------------
deadline = time.time() + 3600 * BUDGET_HOURS
iterations = 0
last_logged_at = 0.0
log('start best=%d lib=%d shard=%d' % (best_size, len(library), len(shard)))

while time.time() < deadline and best_size > 6:
    iterations += 1

    if iterations % 400 == 0:
        added = refresh_library()
        if added:
            log('lib refresh +%d shard=%d (lib=%d)' % (added, len(shard), len(library)))

    if iterations % 25 == 0:
        if os.path.exists(os.path.join(PROJECT_DIR, 'LINK.sig')):
            log('LINK found - path closed elsewhere, exiting')
            break
        shared_best = common.read_best_size(SIZE_PATH)
        if shared_best < best_size:
            best_size = shared_best
            pool[0] = open(BEST_PATH).read().strip()
            pool = pool[:1] + random.sample(library, min(60, len(library)))
            log('REBASE %d' % best_size)

    r = random.random()
    if r < 0.70:
        start_sig = pool[0] if random.random() < 0.5 else random.choice(pool)
        tri = regina.Triangulation4.fromIsoSig(start_sig)
        common.uphill_excursion(tri, random.randrange(0, 5))
        if tri.size() <= 80:
            tri.subdivide()
        tri = common.simplify_and_descend(tri)

    elif r < 0.95:
        tri = regina.Triangulation4.fromIsoSig(random.choice(pool))
        common.uphill_excursion(tri, random.randrange(4, 17))
        tri = common.simplify_and_descend(tri, rounds=5)

    else:
        # Only basins OUTSIDE the seed's own ceiling-14 component can pay off
        # here -- that component (44.6M states) was already exhausted with
        # nothing below 8, so re-probing it would just re-tread dead ground.
        if shard_probed >= len(shard):
            continue
        sig = shard[shard_probed]
        shard_probed += 1
        height, node_cap = 6, 15000
        box = capped_exhaustive_probe(sig, height, node_cap, min(deadline, time.time() + 90))
        if box['hit']:
            tri = common.simplify_and_descend(regina.Triangulation4.fromIsoSig(box['hit']), rounds=6)
            log('BURROW HIT h=%d -> %d' % (height, tri.size()))
            publish(tri)
            if tri.size() < best_size:
                best_size = tri.size()
                pool = [tri.isoSig()]
            continue
        elif not box['capped']:
            log('EXOTIC ceiling-14 component exhausted dead n=%d sig=%s' % (box['visited'], sig))
            continue
        else:
            continue

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
            new_basins_file.write(sig + '\n')
            if zlib.crc32(sig.encode()) % NUM_WORKERS == WORKER_ID:
                shard.append(sig)
            pool.append(sig)
            if len(pool) > 60:
                pool.pop(1)

    if time.time() - last_logged_at > 600:
        last_logged_at = time.time()
        log('it=%d best=%d probed=%d/%d pool=%d'
            % (iterations, best_size, shard_probed, len(shard), len(pool)))

log('EXIT it=%d best=%d probed=%d' % (iterations, best_size, shard_probed))
