## find_resistant_presentation_random.g  (annotated twin of ../"Miller Schupp
## group finder in GAP.rtf" -- same algorithm, same behaviour)
##
## Same GOAL as find_resistant_presentation.g -- find a Miller-Schupp presentation
## < a, b | a^-1 b^n a b^-(n+1), w a^-1 > that resists simplification -- via a much
## cheaper, less rigorous method: RANDOMLY sample (n, w) pairs and keep the first
## one where a single call to GAP's built-in SimplifiedFpGroup leaves generators
## behind (does not reach 0). No multi-restart robustness check like
## find_resistant_presentation.g's SurvivesYourRoutine -- a hit here is a candidate
## worth then checking more rigorously, not a certified-resistant instance on its
## own, since SimplifiedFpGroup's own default simplification strategy might simply
## have gotten unlucky once. (If every one of `limit` trials fully trivialises,
## the function says so and returns `fail` -- a negative result either way,
## exactly the opposite of a find_resistant_presentation.g "survived" verdict,
## which is deliberately much harder to earn.)
##
## w is built by shuffling a multiset with EQUAL counts of a, a^-1, b, b^-1 (k of
## each, k random in [2,6]) into a random order -- not free-reduction-checked, so
## w may contain cancelling adjacent letters; GAP's group operations handle that
## correctly regardless; it's only the alphabet balance that's being controlled
## for here, not the reduced word length.
##
## usage (interactive): gap -q find_resistant_presentation_random.g
## the bottom of this file runs a 200-trial search as an example.

FindMSExample := function(limit)
    local F, a, b, trial, n, k, letters, w, G, H;

    F := FreeGroup("a", "b");
    a := F.1;
    b := F.2;

    for trial in [1..limit] do
        n := Random([2..10]);
        k := Random([2..6]);

        # Equal numbers of each generator and its inverse, then shuffled into a
        # random order below.
        letters := Concatenation(
            List([1..k], i -> a),
            List([1..k], i -> a^-1),
            List([1..k], i -> b),
            List([1..k], i -> b^-1)
        );

        w := One(F);
        while Length(letters) > 0 do
            w := w * Remove(letters, Random([1..Length(letters)]));
        od;

        if Length(w) < 6 then
            continue;   # too short to be an interesting example; try another trial
        fi;

        G := F / [
            a^-1*b^n*a*b^(-(n+1)),
            w*a^-1
        ];

        H := SimplifiedFpGroup(G);

        if Length(GeneratorsOfGroup(H)) > 0 then
            # SimplifiedFpGroup's OWN simplifier got stuck above 0 generators on
            # this instance -- i.e. it did NOT trivialise outright, so this is a
            # (possibly) interesting example, not the common case this search is
            # built to skip past.
            Print("Found on trial ", trial, "\n");
            Print("n = ", n, "\n");
            Print("w = ", w, "\n");
            Print("Original relators: ", RelatorsOfFpGroup(G), "\n");
            Print("Remaining relators: ", RelatorsOfFpGroup(H), "\n");
            return rec(n := n, w := w, group := G, simplified := H);
        fi;
    od;

    Print("All tested examples simplified completely.\n");
    return fail;
end;;

example := FindMSExample(200);;
