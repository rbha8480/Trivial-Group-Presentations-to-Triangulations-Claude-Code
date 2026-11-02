## find_resistant_presentation.g  (annotated twin of ../"find small miller schnupp
## group gap code.rtf" -- same algorithm, same behaviour)
##
## WHAT THIS IS SEARCHING FOR
## ---------------------------
## A Miller-Schupp-style group presentation is < a, b | a^-1 b^n a b^-(n+1), w a^-1 >
## for some exponent n and some word w. These are a classical family of candidate
## counterexamples to the Andrews-Curtis conjecture: easy to state, hard to
## trivialise. This script searches, by increasing total relator length, for the
## SHORTEST such presentation that GAP's own Tietze simplifier cannot trivialise --
## i.e. a genuine "hard" instance, not just one GAP happens not to have tried hard
## enough on.
##
## "Cannot trivialise" is checked by SurvivesYourRoutine(): run GAP's TzGoGo
## (repeated Tietze simplification) interleaved with RANDOM generator substitutions
## (TzSubstitute) -- since Tietze simplification alone gets stuck in local minima
## just like the triangulation searches elsewhere in this thesis, and random
## substitution is this script's equivalent of a "kick" to escape one. The
## presentation is only accepted as resistant if EVERY one of `restarts` independent
## attempts (each up to `maxRounds` escape-and-simplify rounds) fails to reach 0
## generators -- a single successful trivialisation across all restarts disqualifies
## it, since that's proof the presentation isn't actually resistant, just unlucky.
##
## FindSmallestMS() enumerates candidate (n, w) pairs directly: it builds every
## freely-reduced word w of each length, keeps only words whose a-exponent sum is
## zero (otherwise the resulting group's abelianisation is nontrivial in a way that
## is not what Miller-Schupp presentations are), checks the resulting presentation
## is resistant, and returns the first one found at the smallest total relator
## length it tries.
##
## usage (interactive or `gap -q find_resistant_presentation.g`):
##     smallest := FindSmallestMS(maxTotalRelatorLength, maxRoundsPerAttempt, restarts);
## the bottom of this file runs a small search as an example; raise the first
## argument to search further, at real cost -- this is an exponential search over
## words of increasing length.

## Run `restarts` independent escape-and-simplify attempts on G; return true only
## if NONE of them reaches the trivial (0-generator) presentation. Each attempt's
## random substitutions are GAP's own PRNG, so different restarts explore
## genuinely different escape paths, not just repeats of the same one.
SurvivesYourRoutine := function(G, maxRounds, restarts)
    local run, round, P, solved;

    for run in [1..restarts] do
        P := PresentationFpGroup(G, 0);
        TzOptions(P).printLevel := 0;   # silence GAP's own progress spam during the search
        solved := false;

        for round in [1..maxRounds] do
            TzGoGo(P);   # ordinary Tietze simplification to its own local minimum

            if Length(GeneratorsOfPresentation(P)) = 0 then
                solved := true;
                break;
            fi;

            # Escape the local minimum: pick one of GAP's two substitution moves at
            # random (this is the "kick", playing the same role as a basin-hopping
            # kick does for the triangulation searches elsewhere in this thesis).
            if Length(GeneratorsOfPresentation(P)) >= 2 then
                if Random([1,2]) = 1 then
                    TzSubstitute(P, 1, 1);
                else
                    TzSubstitute(P, 1, 2);
                fi;
            fi;

            TzGoGo(P);   # simplify again after the substitution

            if Length(GeneratorsOfPresentation(P)) = 0 then
                solved := true;
                break;
            fi;
        od;

        if solved then
            return false;   # this restart trivialised it -- not resistant, reject immediately
        fi;
    od;

    return true;   # every restart failed to trivialise it
end;;


## Enumerate (n, w) candidates by increasing total relator length and return the
## first one whose presentation survives SurvivesYourRoutine, or `fail`.
FindSmallestMS := function(maxTotal, maxRounds, restarts)
    local F, a, b, letters, inverseIndex, deltaA,
          answer, target, n, len, maxLen,
          Search, tested;

    F := FreeGroup("a", "b");
    a := F.1;
    b := F.2;

    letters := [a, a^-1, b, b^-1];
    inverseIndex := [2, 1, 4, 3];   # which letter undoes which, for free-reduction
    deltaA := [1, -1, 0, 0];        # each letter's contribution to the exponent sum in a

    answer := fail;
    tested := 0;

    for target in [7..maxTotal] do
        Print("Testing total relator length ", target, "...\n");

        for n in [1..QuoInt(target - 3, 2)] do
            maxLen := target - Length(a^-1*b^n*a*b^(-(n+1))) + 1;

            if maxLen >= 1 then
                for len in [1..maxLen] do

                    # Depth-first search over freely-reduced words of length `len`
                    # with the given letter alphabet, pruning any prefix that could
                    # not possibly reach exponent-sum zero in the remaining letters.
                    Search :=
                    function(prefix, last, position, aSum)
                        local i, w, r1, r2, G, relatorLengths;

                        if answer <> fail then
                            return;   # another branch already found an answer
                        fi;

                        if AbsInt(aSum) > len - position then
                            return;   # cannot reach aSum=0 even using every remaining letter
                        fi;

                        if position = len then
                            if aSum <> 0 then
                                return;
                            fi;

                            w := prefix;
                            r1 := a^-1*b^n*a*b^(-(n+1));   # the fixed Miller-Schupp relator
                            r2 := a^-1*w;                   # the relation a = w

                            if Length(r1) + Length(r2) <> target then
                                return;   # only accept candidates at exactly this target length
                            fi;

                            tested := tested + 1;
                            if RemInt(tested, 100) = 0 then
                                Print("Candidates tested: ", tested, "\r");
                            fi;

                            G := F / [r1, r2];

                            if SurvivesYourRoutine(G, maxRounds, restarts) then
                                relatorLengths := SortedList(List(RelatorsOfFpGroup(G), Length));
                                answer := rec(n := n, w := w, relators := [r1, r2],
                                              group := G, totalLength := target);

                                Print("\n\nSmallest resistant example found:\n");
                                Print("n = ", n, "\n");
                                Print("w = ", w, "\n");
                                Print("Relators = ", [r1, r2], "\n");
                                Print("Relator lengths = ", relatorLengths, "\n");
                                Print("Total relator length = ", target, "\n");
                                Print("Candidates tested = ", tested, "\n");
                                Print("Survived ", restarts, " independent tests of ",
                                      maxRounds, " rounds each.\n");
                            fi;

                            return;
                        fi;

                        # Extend the word by one more letter, skipping whichever
                        # letter would immediately cancel the previous one (free
                        # reduction) -- an unreduced word is never a shortest
                        # representative, so there is no reason to search it.
                        for i in [1..4] do
                            if last = 0 or i <> inverseIndex[last] then
                                Search(prefix * letters[i], i, position + 1, aSum + deltaA[i]);
                            fi;
                        od;
                    end;

                    Search(One(F), 0, 0, 0);

                    if answer <> fail then
                        return answer;
                    fi;
                od;
            fi;
        od;
    od;

    Print("\nNo resistant example found up to total relator length ", maxTotal, ".\n");
    Print("Candidates tested = ", tested, "\n");
    return fail;
end;;


## Example run (kept small so this file finishes quickly if sourced directly;
## raise maxTotal for a real search -- cost grows quickly with word length).
smallest := FindSmallestMS(14, 200, 10);;
