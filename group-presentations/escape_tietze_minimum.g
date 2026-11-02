## escape_tietze_minimum.g  (annotated twin of ../"gap group simplification
## sript.rtf" -- same algorithm, same behaviour)
##
## Simplifies ONE specific balanced presentation,
##     < a, b | a^-1 b a b^-2,  a^-3 (ba)^2 b >
## by alternating GAP's own Tietze simplifier (TzGoGo) with a random escape move
## (TzSubstitute) whenever TzGoGo alone gets stuck -- the same basin-hopping idea
## used throughout this thesis's triangulation searches, applied here to a group
## presentation instead of a triangulation: plain greedy simplification can reach
## a local minimum long before the presentation is actually trivial, and a random
## substitution perturbs it enough to escape that minimum on the next TzGoGo pass.
##
## Runs forever (no termination condition besides reaching 0 generators), printing
## status after every round -- this is meant to be watched interactively and
## interrupted by hand once progress stalls, not launched as an unattended batch
## job. Compare find_resistant_presentation.g, which automates exactly this
## watch-and-restart judgement call (via SurvivesYourRoutine's bounded maxRounds
## and multiple independent restarts) so it can run unattended.
##
## usage (interactive): gap -q escape_tietze_minimum.g

F := FreeGroup("a","b");;
a := F.1;;
b := F.2;;

G := F / [
    a^-1*b*a*b^-2,
    a^-3*b*(b*a)^2*b
];;

P := PresentationFpGroup(G, 0);;
TzOptions(P).printLevel := 1;;   # show GAP's own simplification progress each round

i := 0;;
while true do
    i := i + 1;

    Print("\n\n====================================\n");
    Print("ROUND ", i, "\n");
    Print("====================================\n");

    TzGoGo(P);   # ordinary Tietze simplification to its own local minimum
    Print("\nAfter ordinary simplification:\n");
    TzPrintStatus(P);

    if Length(GeneratorsOfPresentation(P)) = 0 then
        Print("\n*** SUCCESS: 0 generators remain ***\n");
        break;
    fi;

    # Escape the local minimum with a random generator substitution, then
    # simplify again -- same role as a basin-hopping kick elsewhere in this
    # thesis: deliberately perturb the state so the next greedy pass doesn't
    # just retrace the same dead end.
    if Length(GeneratorsOfPresentation(P)) >= 2 then
        if Random([1,2]) = 1 then
            TzSubstitute(P, 1, 1);
        else
            TzSubstitute(P, 1, 2);
        fi;
    fi;

    TzGoGo(P);
    Print("\nEnd of round ", i, ":\n");
    TzPrintStatus(P);
od;

Print("\nFINAL PRESENTATION:\n");
TzPrintStatus(P);
TzPrintRelators(P);
