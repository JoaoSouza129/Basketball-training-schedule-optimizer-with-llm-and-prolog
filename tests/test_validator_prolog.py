import pytest
import subprocess
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROLOG_DIR = os.path.abspath("prolog")
CONSTRAINTS_PATH = os.path.join(PROLOG_DIR, "constraints.pl")
RUN_VALIDATION_PATH = os.path.join(PROLOG_DIR, "run_validation.pl")


def run_prolog_validation(facts_code: str) -> dict:
    project_root = os.path.abspath(".")
    constraints_abs = os.path.join(project_root, "prolog", "constraints.pl").replace("\\", "/")
    run_validation_abs = os.path.join(project_root, "prolog", "run_validation.pl").replace("\\", "/")

    with tempfile.NamedTemporaryFile(
        suffix=".pl", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(f":- consult('{constraints_abs}').\n")
        f.write(f":- consult('{run_validation_abs}').\n")
        f.write(facts_code)
        f.write("\n:- run_validation.\n")
        facts_file = f.name
    try:
        result = subprocess.run(
            ["swipl", "-q", "-f", facts_file, "-t", "halt"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        # DEBUG: imprimir tudo para perceber
        print(f"\n=== STDOUT ===\n{output}")
        print(f"=== STDERR ===\n{stderr}")
        print(f"=== END ===\n")
        if not output:
            return {"result": "error", "raw": stderr}

        # Procurar por JSON no output (pode haver warnings antes)
        json_start = output.find("{")
        if json_start >= 0:
            output = output[json_start:]
        return json.loads(output)

    except json.JSONDecodeError:
        return {"result": "parse_error", "raw": output}
    except subprocess.TimeoutExpired:
        return {"result": "timeout", "raw": ""}
    finally:
        try:
            os.unlink(facts_file)
        except PermissionError:
            pass


class TestPrologValidator:
    def test_plano_valido(self):
        """Plano sem violações deve devolver valid."""
        facts = """
            athlete(level(intermediate), injury(none)).
            availability(days([monday, wednesday, friday]), minutes_per_day(60)).
            goal(primary(shooting), secondary(none)).
            rest_day(tuesday). rest_day(thursday). rest_day(saturday). rest_day(sunday).
            block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
            block_catalog(shooting_catch_and_shoot, "Shoot", [intensity_range(2,3), contraindications([]), recovery_cost(2)]).
            block_catalog(cooldown_static_stretching, "Cooldown", [intensity_range(1,1), contraindications([]), recovery_cost(1)]).
            session(monday, [block(warmup_dynamic, 10, 2, []), block(shooting_catch_and_shoot, 30, 3, []), block(cooldown_static_stretching, 10, 1, [])]).
            session(wednesday, [block(warmup_dynamic, 10, 2, []), block(shooting_catch_and_shoot, 30, 3, []), block(cooldown_static_stretching, 10, 1, [])]).
            session(friday, [block(warmup_dynamic, 10, 2, []), block(shooting_catch_and_shoot, 30, 3, []), block(cooldown_static_stretching, 10, 1, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "valid"

    def test_tempo_excedido(self):
        """Bloco com duração > minutos_per_day deve violar daily_time_exceeded."""
        facts = """
            athlete(level(intermediate), injury(none)).
            availability(days([monday]), minutes_per_day(30)).
            goal(primary(shooting), secondary(none)).
            rest_day(tuesday). rest_day(wednesday). rest_day(thursday). rest_day(friday). rest_day(saturday). rest_day(sunday).
            block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
            session(monday, [block(warmup_dynamic, 40, 2, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "invalid"

    def test_lesao_joelho_bloqueia_pliometria(self):
        """Bloco com contraindicação para joelho deve ser bloqueado."""
        facts = """
            athlete(level(intermediate), injury(knee)).
            availability(days([monday]), minutes_per_day(60)).
            goal(primary(shooting), secondary(none)).
            rest_day(tuesday). rest_day(wednesday). rest_day(thursday). rest_day(friday). rest_day(saturday). rest_day(sunday).
            block_catalog(plyometrics_box_jumps, "Box Jumps", [intensity_range(3,5), contraindications([knee, ankle]), recovery_cost(4)]).
            session(monday, [block(plyometrics_box_jumps, 20, 4, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "invalid"

    def test_sem_descanso(self):
        """Nenhum dia de descanso deve violar insufficient_rest_days."""
        facts = """
            athlete(level(beginner), injury(none)).
            availability(days([monday, tuesday, wednesday, thursday, friday, saturday, sunday]), minutes_per_day(30)).
            goal(primary(shooting), secondary(none)).
            block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
            session(monday, [block(warmup_dynamic, 10, 2, [])]).
            session(tuesday, [block(warmup_dynamic, 10, 2, [])]).
            session(wednesday, [block(warmup_dynamic, 10, 2, [])]).
            session(thursday, [block(warmup_dynamic, 10, 2, [])]).
            session(friday, [block(warmup_dynamic, 10, 2, [])]).
            session(saturday, [block(warmup_dynamic, 10, 2, [])]).
            session(sunday, [block(warmup_dynamic, 10, 2, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "invalid"

    def test_bloco_desconhecido(self):
        """Bloco que não existe no catálogo deve violar unknown_block."""
        facts = """
            athlete(level(beginner), injury(none)).
            availability(days([monday]), minutes_per_day(30)).
            goal(primary(shooting), secondary(none)).
            rest_day(tuesday). rest_day(wednesday). rest_day(thursday). rest_day(friday). rest_day(saturday). rest_day(sunday).
            block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
            session(monday, [block(inexistent_block, 10, 2, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "invalid"

    def test_consecutivos_alta_intensidade(self):
        """Dois dias consecutivos com alta intensidade devem violar."""
        facts = """
            athlete(level(advanced), injury(none)).
            availability(days([monday, tuesday]), minutes_per_day(60)).
            goal(primary(conditioning), secondary(none)).
            rest_day(wednesday). rest_day(thursday). rest_day(friday). rest_day(saturday). rest_day(sunday).
            block_catalog(conditioning_hiit, "HIIT", [intensity_range(4,5), contraindications([knee, back]), recovery_cost(4)]).
            block_catalog(warmup_dynamic, "Warmup", [intensity_range(1,2), contraindications([]), recovery_cost(1)]).
            session(monday, [block(conditioning_hiit, 20, 4, [])]).
            session(tuesday, [block(conditioning_hiit, 20, 5, [])]).
        """
        result = run_prolog_validation(facts)
        assert result["result"] == "invalid"
