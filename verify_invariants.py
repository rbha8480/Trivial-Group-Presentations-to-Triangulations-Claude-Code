"""
verify_invariants.py  (annotated twin of ../verify.py — same behaviour)

Independent sanity check on a single isoSig file: load it, print the invariants
that certify "this is still the closed homotopy 4-sphere" (valid / connected /
orientable / closed / not ideal / no boundary / single vertex / chi=2 / H1=0 /
H2=0), then extract and simplify its fundamental group presentation as a second,
independent check that pi_1 is (still) trivial.

This is deliberately the same invariant check every search script's ok()/
invariants_hold() runs before a publish — run it by hand on any saved record to
re-confirm it without trusting the search process that produced it.

usage:   /usr/local/bin/regina-python verify_invariants.py path/to/some.isosig
"""
import regina, sys

tri = regina.Triangulation4.fromIsoSig(open(sys.argv[1]).read().strip())

print('size=%d valid=%s conn=%s orient=%s closed=%s ideal=%s bdry=%d V=%d' % (
    tri.size(), tri.isValid(), tri.isConnected(), tri.isOrientable(), tri.isClosed(),
    tri.isIdeal(), tri.countBoundaryComponents(), tri.countVertices()))
print('chi=%s H1=%s H2=%s' % (tri.eulerCharTri(), tri.homology(1), tri.homology(2)))

group = regina.GroupPresentation(tri.fundamentalGroup())
for _ in range(80):
    if not group.simplify():
        break   # stop as soon as a pass finds nothing left to simplify
print('pi1 =', group.compact()[:120])
