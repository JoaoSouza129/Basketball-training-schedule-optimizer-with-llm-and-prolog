import json
from dataclasses import dataclass
import tempfile
import subprocess
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from catalog_loader import get_block_ids
@dataclass
class ValidationResult:
    is_valid:bool
    violations:list
    raw_output:dict

def plan_to_facts(athlete: dict, plan: dict) -> str:
    facts=[]
    
    # Passo A: Factos dos atletas (level, injury)
    level=athlete["profile"]["level"]
    injury_region = athlete["physical_restrictions"]["injury_region"]
    if injury_region is None:
        injury_atom = "null"
    else:
        injury_atom = injury_region
    facts.append(f"athlete(level({level}), injury({injury_atom})).")
    # Passo B: Factos da Disponibilidade (days, minutes)
    days=athlete["availability"]["available_days"]
    days_prolog = ", ".join(days)
    minutes=athlete["availability"]["minutes_per_day"]
    facts.append(f"availability(days([{days_prolog}]), minutes_per_day({minutes})).")
    # Passo C: Factos dos Dias de Descanso (quem não está no plano é rest_day)
    all_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in all_days:
        if plan["weekly_plan"][day]==None:
            facts.append(f"rest_day({day}).")
            
    # Passo D: Factos das Sessões (ciclo pelos dias do plano e gerar os blocos)
    
    for day in all_days:
        day_data = plan["weekly_plan"][day]
        if day_data is not None:
            blocks_prolog = []
            for block in day_data["sessions"]:
                blocks_prolog.append(block_to_prolog(block))
            blocks_str = ", ".join(blocks_prolog)
            facts.append(f"session({day}, [{blocks_str}]).")
    
    return "\n".join(facts)

def block_to_prolog(block: dict) -> str:
    block_id = block["block_id"]
    duration = block["duration_minutes"]
    intensity = block["intensity"]
    raw_tags = block.get("tags") or []
    clean_tags = [t.lower().replace(" ", "_").replace("-", "_") for t in raw_tags if t]
    tags=", ".join(clean_tags)
    return f"block({block_id}, {duration}, {intensity}, [{tags}])"

    
def catalog_to_facts(catalog: list) -> list:
    facts = []
    for block in catalog:
        block_id = block["id"]
        min_int, max_int = block["intensity_range"]
        recovery = block["recovery_cost"]
        contras = block.get("contraindications", [])
      
        if not contras:
            fact = f"block_catalog({block_id}, {min_int}, {max_int}, none, {recovery})."
            facts.append(fact)
        else:
            for contra in contras:
                fact = f"block_catalog({block_id}, {min_int}, {max_int}, {contra}, {recovery})."
                facts.append(fact)
                
    return facts

def validate_plan(athlete: dict, plan: dict, catalog: list) -> dict:
    # 1. Verifica se os ids dos blocos são validos
    valid_ids = {block["id"] for block in catalog}
    for day, day_data in plan.get("weekly_plan", {}).items():
            if day_data is not None:
                for block in day_data.get("sessions", []):
                    # Compatibilidade de chaves para evitar None inesperado
                    b_id = block.get("block_id") or block.get("id") or block.get("block")
                    if b_id not in valid_ids:
                        return {
                            "is_valid": False,
                            "violations": [{"rule": "unknown_block", "arg1": b_id, "arg2": 0, "arg3": 0}],
                            "raw_output": {}
                        }
    # 2. Resolução de caminhos absolutos (Segurança de caminhos e concorrência)
    project_root = os.path.abspath(os.getcwd())
    constraints_abs = os.path.join(project_root, "prolog", "constraints.pl").replace("\\", "/")
    run_validation_abs = os.path.join(project_root, "prolog", "run_validation.pl").replace("\\", "/")

    # 3. Gerar factos
    plan_facts = plan_to_facts(athlete, plan)
    catalog_facts = catalog_to_facts(catalog)
    all_facts = "\n".join(catalog_facts + [plan_facts])
    
    # 4. Gravar num ficheiro temporário
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pl", delete=False, encoding="utf-8") as f:
        f.write(f":- consult('{constraints_abs}').\n")
        f.write(f":- consult('{run_validation_abs}').\n")
        f.write(all_facts)
        f.write("\n:- run_validation.\n")
        facts_file = f.name

    # Toda a leitura ou execução pós-criação DEVE estar protegida pelo try
    try:
        # Debug opcional (Seguro contra falhas de IO)
        with open(facts_file, 'r', encoding='utf-8') as ficheiro:
            conteudo = ficheiro.read()
            print("=== FACTS FILE CONTENT ===")
            print(conteudo)

        # 5. Chamar o SWI-Prolog
        result = subprocess.run(
            ["swipl", "-q", "-f", facts_file, "-t", "halt"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
        
        print("=== STDOUT ===")
        print(result.stdout)
        print("=== STDERR ===")
        print(result.stderr)
        print("================")
        
        output = result.stdout.strip()
        if not output:
            raise Exception("Prolog não devolveu output")

        json_start = output.find("{")
        if json_start >= 0:
            output = output[json_start:]

        data = json.loads(output)

        return {
            "is_valid": data["result"] == "valid",
            "violations": data["violations"],
            "raw_output": data
        }

    finally:
        # Garante a limpeza do sistema de ficheiros, aconteça o que acontecer no try
        if os.path.exists(facts_file):
            os.unlink(facts_file)