# orchestrator.py

import os
import sys
import json

# Adicionar o diretório pai ao path (se necessário)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from normalizer import normalize_input
from catalog_loader import check_feasibility, get_eligible_blocks, load_catalog
from llm_client import call_llm, gerar_user_prompt, call_llm_hf
from prolog_bridge import validate_plan
from load_system_prompt import load_system_prompt
from score_calculator import calculate_score
MAX_TENTATIVAS = 3


FULL_CATALOG=load_catalog()

def formatar_violacoes_para_llm(violacoes: list) -> str:
    linhas = []
    for v in violacoes:
        regra = v.get("rule", "desconhecida")
        arg1 = v.get("arg1", "")
        arg2 = v.get("arg2", "")
        arg3 = v.get("arg3", "")
        linhas.append(f"- Regra '{regra}' no dia '{arg1}'. Valor atual: {arg2}, Limite: {arg3}")
    return "\n".join(linhas)





def pipeline_principal(user_input: dict):
    # 1. Normalizar input
    atleta = normalize_input(user_input)

    # 2. Obter blocos elegíveis
    blocos = FULL_CATALOG

    # 3. Pré-checar viabilidade
    """problemas = check_feasibility(atleta, blocos)
    if problemas:
        print("Não foi possível gerar plano. Erros encontrados:")
        for erro in problemas:
            print(f" - {erro}")
        return None
"""
    # 4. Carregar prompt do sistema
    system_prompt = load_system_prompt()

    # 5. Loop de tentativas
    feedback_anterior = ""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        print(f"\n[TENTATIVA {tentativa}] Solicitando plano ao LLM...")
        
        user_prompt = gerar_user_prompt(atleta, blocos, feedback_anterior)
        plano = call_llm(system_prompt, user_prompt)
        
        plano=completar_plano(plano)
        print("[VALIDANDO] Enviando plano para validação Prolog...")
        resultado = validate_plan(atleta, plano, blocos)

        if resultado["is_valid"]:
            print("✅ Plano validado com sucesso!")
            return plano
        else:
            print("❌ Plano inválido. Preparando feedback...")
            feedback_anterior = formatar_violacoes_para_llm(resultado["violations"])

    print("⚠️ Número máximo de tentativas atingido. Retornando último plano.")
    return plano

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def completar_plano(plan: dict) -> dict:
    weekly = plan.get("weekly_plan", {})
    for day in DAYS_OF_WEEK:
        if day not in weekly:
            weekly[day] = None
    plan["weekly_plan"] = weekly
    return plan
# Teste rápido

if __name__ == "__main__":
    user_input = {
        "profile": {"level": "beginner", "experience_years": 2},
        "primary_goal": "conditioning",
        "availability": {
            "days_per_week": 3,
            "minutes_per_day": 60,
            "available_days": ["monday", "wednesday", "friday"]
        },
        "physical_restrictions": {"has_injury": False, "injury_region": None}
    }

    plano_final = pipeline_principal(user_input)
    if plano_final:
        print("\n--- PLANO FINAL ---")
        print(json.dumps(plano_final, indent=2, ensure_ascii=False))
    print("\n")
    print(calculate_score(user_input,plano_final,FULL_CATALOG))