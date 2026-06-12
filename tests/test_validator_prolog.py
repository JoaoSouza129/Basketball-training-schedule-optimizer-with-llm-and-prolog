import pytest
import subprocess
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from prolog_bridge import validate_plan
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
            block_catalog(warmup_dynamic, 1, 2, none, 1).
            block_catalog(shooting_catch_and_shoot, 2, 3, none, 2).
            block_catalog(cooldown_static_stretching, 1, 1, none, 1).
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

    def test_(self):
        # 1. Atleta com lesão no joelho (knee)
        atleta_lesionado = {
            "profile": {"level": "beginner"},
            "physical_restrictions": {"injury_region": "knee"},
            "availability": {
                "available_days": ["monday"],
                "minutes_per_day": 30
            }
        }

        # 2. Catálogo onde o bloco 'depth_jumps' tem contraindicação 'knee' e custo 10
        # Lembra-te de passar o formato que a tua função catalog_to_facts espera receber!
        catalogo_teste = [
            {
                "id": "depth_jumps",
                "name": "Depth Jumps",
                "intensity_range": [4, 5],
                "contraindications": ["knee"],
                "recovery_cost": 10
            }
        ]

        # 3. O plano semanal gerado (como se viesse do LLM) que força o erro
        plano_invalido = {
            "weekly_plan": {
                "monday": {
                    "sessions": [
                        {
                            "block_id": "depth_jumps",
                            "duration_minutes": 20,
                            "intensity": 4,
                            "tags": ["plyometrics"]
                        }
                    ]
                },
                "tuesday": None, "wednesday": None, "thursday": None, "friday": None, "saturday": None, "sunday": None
            }
        }

        # 4. Executar a validação

        resultado = validate_plan(atleta_lesionado, plano_invalido, catalogo_teste)

        # 5. O que esperamos que aconteça?
        # Se o teu Prolog estiver bem afinado, is_valid deve ser False e a regra violada deve ser apanhada!
        assert resultado["is_valid"] is False
        
        # Vamos inspecionar as violações que o teu dicionário traz
        regras_violadas = [v["rule"] for v in resultado["violations"]]
        print("Regras que o Prolog apanhou:", regras_violadas)
        
        assert "blocked_block_due_to_injury" in regras_violadas
    
    def test_ultrapassar_carga_semanal(self):
        atleta = {
            "profile": {"level": "beginner"},
            "physical_restrictions": {"injury_region": ["none"]},
            "availability": {
                "available_days": ["monday","tuesday","wednesday","friday","sunday"],
                "minutes_per_day": 90
            }
        }
        
        catalogo_teste = [
            {
                "id": "plyometrics_depth_jumps",
                "name": "Depth Jumps",
                "intensity_range": [4, 5],
                "contraindications": ["knee"],
                "recovery_cost": 5
            },
            {
                "id": "shooting_catch_and_shoot",
                "name": "lançamento",
                "intensity_range": [4, 5],
                "contraindications": [],
                "recovery_cost": 5
            }
        ]
        
        plano_invalido = {
            "weekly_plan": {
                "monday": {
                    "sessions": [
                        {
                            "block_id": "plyometrics_depth_jumps",
                            "duration_minutes": 20,
                            "intensity": 4,
                            "tags": ["plyometrics"]
                        }, 
                        {
                            "block_id": "shooting_catch_and_shoot",
                            "duration_minutes": 70,
                            "intensity": 4,
                            "tags": ["shooting"]
                        }   
                    ]
                },
                "tuesday": {
                    "sessions": [
                        {
                            "block_id": "plyometrics_depth_jumps",
                            "duration_minutes": 20,
                            "intensity": 1,
                            "tags": ["plyometrics"]
                        }, 
                        {
                            "block_id": "shooting_catch_and_shoot",
                            "duration_minutes": 70,
                            "intensity": 2,
                            "tags": ["shooting"]
                        }   
                    ]
                },
                "friday": {
                    "sessions": [
                        {
                            "block_id": "plyometrics_depth_jumps",
                            "duration_minutes": 20,
                            "intensity": 4,
                            "tags": ["plyometrics"]
                        }, 
                        {
                            "block_id": "shooting_catch_and_shoot",
                            "duration_minutes": 70,
                            "intensity": 4,
                            "tags": ["shooting"]
                        }   
                    ]
                },
                "sunday": {
                    "sessions": [
                        {
                            "block_id": "plyometrics_depth_jumps",
                            "duration_minutes": 20,
                            "intensity": 4,
                            "tags": ["plyometrics"]
                        }, 
                        {
                            "block_id": "shooting_catch_and_shoot",
                            "duration_minutes": 70,
                            "intensity": 4,
                            "tags": ["shooting"]
                        }   
                    ]
                },
                "wednesday": None, "thursday": None, "saturday": None,
            }
        }
        
        resultado = validate_plan(atleta, plano_invalido, catalogo_teste)

        # 5. O que esperamos que aconteça?
        # Se o teu Prolog estiver bem afinado, is_valid deve ser False e a regra violada deve ser apanhada!
        assert resultado["is_valid"] is False
        regras_violadas = [v["rule"] for v in resultado["violations"]]
        print("Regras que o Prolog apanhou:", regras_violadas)
        
        assert "weekly_load_exceeded" in regras_violadas