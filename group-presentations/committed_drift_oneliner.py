"""
committed_drift_oneliner.py  (annotated twin of ../"simplifying code.rtf" --
same algorithm, same behaviour)

The simplest possible committed-drift loop: repeatedly call simplifyUpDown
with alwaysModify=True, which KEEPS whatever Regina's up-down search returns
even if it is larger than before, instead of only keeping improvements. That
lets it escape local minima a plain simplify() cannot -- but with no anchor to
the best triangulation seen and no greedy harvest pass after each step, it can
in principle wander uphill indefinitely (see search_for_target_presentation.py
and escalating_simplify.py for the same caveat elsewhere in this project; see
the leashed version of this exact pattern in the triangulation-search
appendix's basin-hopping scripts, which pair committed drift with exactly
these two safeguards). In practice, watched interactively, this is the fastest
way to probe whether a triangulation descends easily at all.

Meant to be pasted directly into an interactive `regina-python` session where
a Triangulation4 is already loaded into `tri`; prints the size after every
step so progress (or the lack of it) is visible immediately. The number 48 indicates
the number of pentachora in the triangulation and can be changed to whatever is suitable.

usage (interactive, with `tri` already loaded):
    exec(open('committed_drift_oneliner.py').read())
"""
while tri.size() >= 48:
    res = tri.simplifyUpDown(20, 100, True)
    print(tri.size())
