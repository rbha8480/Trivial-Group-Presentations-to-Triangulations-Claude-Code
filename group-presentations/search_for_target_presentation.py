"""
search_for_target_presentation.py  (annotated twin of ../"script.py fundamental
group.py" -- same algorithm, same behaviour)

NOTE ON THE ORIGINAL FILE: as saved, it does not parse as Python -- its last six
lines are an EXAMPLE RESULT (two found presentations, with their isoSigs) that
got pasted directly below the code rather than into a comment. That example is
reproduced at the bottom of this docstring instead; the code below is otherwise
identical.

Searches a running triangulation for a specific target: a point during
committed simplification where the fundamental group is EXACTLY a 2-generator,
2-relator, total-relator-length-13 balanced presentation, at exactly 20
pentachora -- then checks whether a further, deeper simplification pass
trivialises that presentation completely (0 generators left).

CAVEAT (kept here rather than silently fixed, since this is an annotated twin
of code that was actually used): simplifyUpDown is called here with
alwaysModify=True -- committed drift, same pattern as
committed_drift_oneliner.py and the same one that needs a leash (anchor to the
best triangulation seen, snap back if it drifts too far upward) to avoid
wandering uphill forever on a longer run. The outer `while tri.size() >= 20`
condition does bound this specific loop (it exits once simplification drops
below size 20), but there is no anchor/harvest mechanism within an iteration.

Meant to be pasted into an interactive `regina-python` session (or a script
run with `regina-python -i`) where a Triangulation4 is already loaded into
`tri`.

EXAMPLE RESULT (from the original run, preserved verbatim as a record of what
was actually found -- NOT something this file re-executes):

    < a b | a b^-1 a b a^-1 b, a^4 b^3 >
    uLLLLMvMzQAMAQQMQkcefigjkmlpklmlolqrsosqroqqsttttabmbabAbaaabaaGambabmbmbNamb3bmbaaAbababab2b2bBb2b2bBbaa3a3baa
    < >
    uLLvLMvAPQMQQMPQPkcejgkljompponplmnmqqmrsqsrsttttabmbAbaaabaa2baambaaababmbabmbmbNambxa3ambAbabaaab2bBbab3a3baa

    < a b | a b^-1 a^-1 b^-1 a b, a^4 b^-3 >
    uLLLLMvMzQAMAQQMQkcefigjkmlpklmlolqrsosqroqqsttttabmbabAbaaabaaGambabmbmbNamb3bmbaaAbababab2b2bBb2b2bBbaa3a3baa
    < >
    uLLvLMvAPQMQQMPQPkcejgkljompponplmnmqqmrsqsrsttttabmbAbaaabaa2baambaaababmbabmbmbNambxa3ambAbabaaab2bBbab3a3baa

usage (interactive, with `tri` already loaded):
    exec(open('search_for_target_presentation.py').read())
"""
while tri.size() >= 20:
    found = False

    res = tri.simplifyUpDown(10, 30, True)
    g = tri.fundamentalGroup()
    if (g.countGenerators() == 2 and g.countRelations() == 2
            and g.relatorLength() == 13 and tri.size() == 20):
        print(g, tri.isoSig())
        found = True

    res = tri.simplifyUpDown(10, 500, True)
    g = tri.fundamentalGroup()
    if g.countGenerators() == 0 and found == True:
        print(g, tri.isoSig())
