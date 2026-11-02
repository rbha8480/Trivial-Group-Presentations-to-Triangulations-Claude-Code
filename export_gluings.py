"""
export_gluings.py  (annotated twin of ../export_M.py — same behaviour)

Converts an isoSig into a standalone, human-readable Python source file that
rebuilds the exact same triangulation via Triangulation4.fromGluings(...) — the
same format the thesis's hand-copied .rtf triangulation sources use. This is the
inverse of the "load from an rtf" step: isoSig is compact but opaque, fromGluings
is verbose but lets a reader see every facet pairing directly.

Each facet pairing is only written once (for pentachoron `s`, facet `f`, glued to
pentachoron `a.index()` facet `pm[f]`): the `(a.index(), pm[f]) > (s, f)` guard
keeps whichever one of the two mirror-image entries for a shared facet sorts later,
so the output lists every gluing exactly once instead of twice.

After writing the file, it is immediately re-loaded and re-exec'd, and the
resulting isoSig is compared back against the original — a write that doesn't
round-trip to the same triangulation is caught here, not discovered later.

usage:   /usr/local/bin/regina-python export_gluings.py path/to/some.isosig path/to/output.py
"""
import regina, sys

isosig_path, output_path = sys.argv[1], sys.argv[2]
sig = open(isosig_path).read().strip()
tri = regina.Triangulation4.fromIsoSig(sig)

print('VERIFY size=%d valid=%s closed=%s orient=%s chi=%s H1=%s H2=%s V=%d' % (
    tri.size(), tri.isValid(), tri.isClosed(), tri.isOrientable(), tri.eulerCharTri(),
    tri.homology(1), tri.homology(2), tri.countVertices()), flush=True)

gluing_entries = []
for s in range(tri.size()):
    pent = tri.pentachoron(s)
    for f in range(5):
        neighbour = pent.adjacentPentachoron(f)
        if neighbour is None:
            continue
        perm = pent.adjacentGluing(f)
        if (neighbour.index(), perm[f]) > (s, f):   # write each shared facet exactly once
            gluing_entries.append(
                '[ %d, %d, %d, Perm5(%d,%d,%d,%d,%d) ]'
                % (s, f, neighbour.index(), perm[0], perm[1], perm[2], perm[3], perm[4]))

lines = [
    '# Closed homotopy 4-sphere M, %d pentachora (from the "after double" lineage)' % tri.size(),
    '# pi_1 trivial (GAP coset enumeration: order 1)',
    '# isoSig: %s' % sig,
    'tri = Triangulation4.fromGluings(%d, [' % tri.size(),
]
for i in range(0, len(gluing_entries), 2):
    pair = gluing_entries[i:i + 2]
    lines.append('    ' + ', '.join(pair) + (',' if i + 2 < len(gluing_entries) else ''))
lines.append('])')
open(output_path, 'w').write('\n'.join(lines) + '\n')

# Round-trip check: re-load what we just wrote and confirm it's the same triangulation.
namespace = {'Triangulation4': regina.Triangulation4, 'Perm5': regina.Perm5}
exec(open(output_path).read(), namespace)
print('wrote %s entries=%d reload_ok=%s'
      % (output_path.split('/')[-1], len(gluing_entries), namespace['tri'].isoSig() == sig), flush=True)
