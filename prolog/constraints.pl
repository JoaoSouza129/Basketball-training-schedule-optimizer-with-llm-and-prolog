% ============================================================
% constraints.pl - Regras Hard de validação de planos de treino
% ============================================================

:- dynamic violation/4.
:- dynamic rest_day/1.
:- dynamic session/2.
:- dynamic athlete/2.
:- dynamic availability/2.
:- dynamic goal/2.
:- dynamic block_catalog/3.


% -----------------------------------------------------------
% Utilitários
% -----------------------------------------------------------

% Soma das durações de uma lista de blocos
sum_durations([], 0).
sum_durations([block(_, Dur, _, _) | Rest], Total) :-
    sum_durations(Rest, RestTotal),
    Total is Dur + RestTotal.

% Dias consecutivos
consecutive_days(monday, tuesday).
consecutive_days(tuesday, wednesday).
consecutive_days(wednesday, thursday).
consecutive_days(thursday, friday).
consecutive_days(friday, saturday).
consecutive_days(saturday, sunday).

% Um bloco tem alta intensidade se intensity >= 4
block_high_intensity(block(_, _, Int, _)) :-
    Int >= 4.

% Uma sessão tem alta intensidade se algum bloco tiver intensity >= 4
session_has_high_intensity(Day) :-
    session(Day, Blocks),
    member(Block, Blocks),
    block_high_intensity(Block).

% -----------------------------------------------------------
% Regra 1 — Limite de tempo diário
% -----------------------------------------------------------
check_daily_time_limit :-
    availability(_, minutes_per_day(MaxMinutes)),
    forall(
        session(Day, Blocks),
        (   sum_durations(Blocks, Total),
            (   Total > MaxMinutes
            ->  assert(violation(daily_time_exceeded, Day, Total, MaxMinutes))
            ;   true
            )
        )
    ).

% -----------------------------------------------------------
% Regra 2 — Sem alta intensidade em dias consecutivos
% -----------------------------------------------------------
check_no_consecutive_high_intensity :-
    findall(Day, session(Day, _), Days),
    check_consecutive_pairs(Days).

check_consecutive_pairs([]).
check_consecutive_pairs([_]).
check_consecutive_pairs([D1, D2 | Rest]) :-
    (   consecutive_days(D1, D2),
        session_has_high_intensity(D1),
        session_has_high_intensity(D2)
    ->  assert(violation(consecutive_high_intensity, D1, D2, 0))
    ;   true
    ),
    check_consecutive_pairs([D2 | Rest]).

% -----------------------------------------------------------
% Regra 3 — Blocos com contraindicações bloqueados por lesão
% -----------------------------------------------------------
check_injury_contraindications :-
    athlete(_, injury(Region)),
    Region \= none,
    forall(
        (   session(Day, Blocks),
            member(block(BlockId, _, _, _), Blocks)
        ),
        (   block_catalog(BlockId, _, Attrs),
            member(contraindications(Contras), Attrs),
            (   member(Region, Contras)
            ->  assert(violation(blocked_block_due_to_injury, Day, BlockId, Region))
            ;   true
            )
        )
    ).

check_injury_contraindications :-
    athlete(_, injury(none)).

% -----------------------------------------------------------
% Regra 4 — Mínimo de 1 dia de descanso
% -----------------------------------------------------------
check_minimum_rest :-
    findall(D, rest_day(D), RestDays),
    length(RestDays, N),
    (   N < 1
    ->  assert(violation(insufficient_rest_days, N, 1, 0))
    ;   true
    ).

% -----------------------------------------------------------
% Regra 5 — Blocos devem existir no catálogo
% -----------------------------------------------------------
check_blocks_in_catalog :-
    forall(
        (   session(_, Blocks),
            member(block(BlockId, _, _, _), Blocks)
        ),
        (   block_catalog(BlockId, _, _)
        ->  true
        ;   assert(violation(unknown_block, BlockId, 0, 0))
        )
    ).

% -----------------------------------------------------------
% Regra 6 — Carga semanal maxima por nível
% -----------------------------------------------------------
max_load_for_level(beginner, 800).
max_load_for_level(intermediate, 1200).
max_load_for_level(advanced, 2000).

check_weekly_load_limit :-
    athlete(level(Level), _),
    max_load_for_level(Level, MaxLoad),
    findall(Cost, (
        session(_, Blocks),
        member(block(Id, Dur, _, _), Blocks),
        block_catalog(Id, _, Attrs),
        member(recovery_cost(BaseCost), Attrs),
        Cost is BaseCost * Dur / 15
    ), Costs),
    sumlist(Costs, Total),
    (   Total > MaxLoad
    ->  assert(violation(weekly_load_exceeded, Total, MaxLoad, 0))
    ;   true
    ).

% -----------------------------------------------------------
% Predicado principal de validação
% -----------------------------------------------------------
validate_plan(Result, Violations, SoftViolations) :-
    retractall(violation(_,_,_,_)),

    check_daily_time_limit,
    check_no_consecutive_high_intensity,
    check_injury_contraindications,
    check_minimum_rest,
    check_blocks_in_catalog,
    check_weekly_load_limit,

    findall(
        violation(Rule, Arg1, Arg2, Arg3),
        violation(Rule, Arg1, Arg2, Arg3),
        Violations
    ),
    (   Violations = []
    ->  Result = valid
    ;   Result = invalid
    ),
    SoftViolations = [].
