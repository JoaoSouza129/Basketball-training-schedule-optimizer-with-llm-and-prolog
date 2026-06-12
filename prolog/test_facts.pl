% ============================================================
% test_facts.pl - Factos de teste para validar regras Prolog
% ============================================================

% Perfil do atleta
athlete(level(intermediate), injury(none)).

% Disponibilidade
availability(days([monday, wednesday, friday]), minutes_per_day(60)).

% Objetivo
goal(primary(shooting), secondary(none)).

% Dias de descanso
rest_day(tuesday).
rest_day(thursday).
rest_day(saturday).
rest_day(sunday).

% Catálogo (apenas blocos usados no teste)
block_catalog(warmup_dynamic, "Aquecimento Dinâmico", [
    intensity_range(1, 2),
    contraindications([]),
    recovery_cost(1)
]).
block_catalog(shooting_catch_and_shoot, "Catch-and-Shoot", [
    intensity_range(2, 3),
    contraindications([]),
    recovery_cost(2)
]).
block_catalog(plyometrics_box_jumps, "Box Jumps", [
    intensity_range(3, 5),
    contraindications([knee, ankle]),
    recovery_cost(4)
]).
block_catalog(conditioning_hiit, "HIIT", [
    intensity_range(4, 5),
    contraindications([knee, back]),
    recovery_cost(4)
]).
block_catalog(cooldown_static_stretching, "Alongamentos", [
    intensity_range(1, 1),
    contraindications([]),
    recovery_cost(1)
]).

% Sessões da semana
session(monday, [
    block(warmup_dynamic, 10, 2, [warmup, mobility]),
    block(shooting_catch_and_shoot, 40, 3, [technical, shooting]),
    block(cooldown_static_stretching, 10, 1, [cooldown, recovery])
]).
session(wednesday, [
    block(warmup_dynamic, 10, 2, [warmup, mobility]),
    block(conditioning_hiit, 20, 4, [physical, conditioning]),
    block(cooldown_static_stretching, 10, 1, [cooldown, recovery])
]).
session(friday, [
    block(warmup_dynamic, 10, 2, [warmup, mobility]),
    block(shooting_catch_and_shoot, 30, 3, [technical, shooting]),
    block(cooldown_static_stretching, 10, 1, [cooldown, recovery])
]).
