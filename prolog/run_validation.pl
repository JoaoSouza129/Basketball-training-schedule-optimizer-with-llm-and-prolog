% ============================================================
% run_validation.pl - Entry point para o bridge Python
% ============================================================

:- consult('constraints.pl').

run_validation :-
    validate_plan(Result, Violations, _),
    format('{"result":"~w","violations":[', [Result]),
    write_violations(Violations),
    write(']}').

write_violations([]).
write_violations([V]) :-
    write_violation(V).
write_violations([V|Vs]) :-
    write_violation(V),
    write(','),
    write_violations(Vs).

write_violation(violation(Rule, A1, A2, A3)) :-
    format('{"rule":"~w","arg1":', [Rule]),
    write_json_value(A1),
    write(',"arg2":'),
    write_json_value(A2),
    write(',"arg3":'),
    write_json_value(A3),
    write('}').

% Escreve um valor como JSON: números nus, átomos entre aspas
write_json_value(V) :-
    number(V), !,
    write(V).
write_json_value(V) :-
    format('"~w"', [V]).
