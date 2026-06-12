:- consult('prolog/constraints.pl').
:- consult('prolog/run_validation.pl').

athlete(level(intermediate), injury(none)).
availability(days([monday]), minutes_per_day(30)).
goal(primary(shooting), secondary(none)).
rest_day(tuesday). rest_day(wednesday). rest_day(thursday). rest_day(friday). rest_day(saturday). rest_day(sunday).
block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
session(monday, [block(warmup_dynamic, 40, 2, [])]).

:- run_validation.
