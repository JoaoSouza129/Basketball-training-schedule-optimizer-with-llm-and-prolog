# orchestrator.py

import os
import sys
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import List


class PlanoResultado:

    def __init__(self, plano: dict, historico_violacoes: List[str], score: float, historico_por_tentativa: list):
        self._plano = plano
        self.historico_violacoes = historico_violacoes
        self.score = score
        self.historico_por_tentativa = historico_por_tentativa or []

    # --- transparência para acesso dict-like (usado em app.py) ---
    def __getitem__(self, key):
        return self._plano[key]

    def __contains__(self, key):
        return key in self._plano

    def get(self, key, default=None):
        return self._plano.get(key, default)

    def items(self):
        return self._plano.items()

    def keys(self):
        return self._plano.keys()

    def values(self):
        return self._plano.values()

    def __repr__(self):
        return f"PlanoResultado(historico_violacoes={self.historico_violacoes}, plano={self._plano}, score={self.score}, historico_por_tentativa={self.historico_por_tentativa})"

# Adicionar o diretório pai ao path (se necessário)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from normalizer import normalize_input
from catalog_loader import check_feasibility, get_eligible_blocks, load_catalog
from llm_client import call_llm, gerar_user_prompt, call_llm_ollama_cloud
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
        if regra == "weekly_load_exceeded":
            linhas.append(f"- [Carga Excedida] A carga total gerada foi {arg1}, mas o limite para o nível do atleta é {arg2}.")
        elif regra == "daily_time_exceeded":
            linhas.append(f"- [Tempo Excedido] No dia '{arg1}', o treino totalizou {arg2} minutos, ultrapassando o limite diário de {arg3} minutos.")
        elif regra == "blocked_block_due_to_injury":
            linhas.append(f"- [Restrição de Lesão] No dia '{arg1}', utilizaste o bloco '{arg2}' que é proibido devido à lesão na região '{arg3}'.")
        elif regra == "missing_equipment":
            linhas.append(f"- [Equipamento em Falta] No dia '{arg1}', tentaste usar o bloco '{arg2}', mas o atleta não tem o equipamento exigido: '{arg3}'.")
        else:
            linhas.append(f"- Violação da regra '{regra}': {arg1}, {arg2}, {arg3}")
        
    return "\n".join(linhas)

def formatar_soft_violacoes(soft_violacoes: list) -> str:
    if not soft_violacoes:
        return ""
    linhas = ["### Recomendações (não obrigatórias):"]
    for sv in soft_violacoes:
        regra = sv.get("rule", "")
        arg1 = sv.get("arg1", "")
        arg2 = sv.get("arg2", "")
        if regra == "recommend_rest_after_high_intensity":
            linhas.append(
                f"- Após sessão intensa a {arg1}, considera colocar descanso a {arg2} em vez de treino."
            )
    return "\n".join(linhas)

def construir_feedback_estruturado(violations: list, historico_violacoes: list) -> dict:
    regras_atuais = [v.get("rule", "desconhecida") for v in violations]
    contagem_historica = Counter(historico_violacoes + regras_atuais)
    repetidas = [regra for regra, count in contagem_historica.items() if count > 1]

    return {
        "status": "rejeitado",
        "violacoes_atuais": violations,
        "regras_repetidas": repetidas,
        "contagem_por_regra": dict(contagem_historica),
        "instrucao": (
            "Corrige as violacoes atuais. Se alguma regra ja se repetiu, muda a estrategia do plano "
            "em vez de apenas trocar um bloco por outro semelhante."
        ),
    }



def pipeline_principal(user_input: dict):
    # 1. Normalizar input
    atleta = normalize_input(user_input)

    # 2. Obter blocos 
    blocos = FULL_CATALOG

    # 3. Pré-checar viabilidade
    problemas = check_feasibility(atleta, blocos)
    if problemas:
        print("Não foi possível gerar plano. Erros encontrados:")
        for erro in problemas:
            print(f" - {erro}")
        return None
    # 4. Carregar prompt do sistema
    system_prompt = load_system_prompt()

    # 5. Loop de tentativas
    plan_validated=False
    feedback_anterior = ""
    count=0
    historico_violacoes = []
    historico_por_tentativa = []  
    #for tentativa in range(1, MAX_TENTATIVAS + 1):
    while not plan_validated: 
        count+=1
        print(f"\n[TENTATIVA {count}] Solicitando plano ao LLM...")
        
        user_prompt = gerar_user_prompt(atleta, blocos, feedback_anterior)
        plano = call_llm_ollama_cloud(system_prompt, user_prompt)
        
        plano=completar_plano(plano)
        print("[VALIDANDO] Enviando plano para validação Prolog...")
        resultado = validate_plan(atleta, plano, blocos)

        if resultado["is_valid"]:
            print("✅ Plano validado com sucesso!")
            soft_feedback = formatar_soft_violacoes(resultado["soft_violations"])
            if soft_feedback:
                print(f"⚠️ Plano aceite com recomendações:\n{soft_feedback}")
            plan_validated=True
            score = calculate_score(atleta,plano,FULL_CATALOG,resultado["soft_violations"])
            print(score)            
            return PlanoResultado(plano, historico_violacoes,score, historico_por_tentativa)
        else:
            print("❌ Plano inválido. Preparando feedback...")

            regras_desta_tentativa = [
                v.get("rule", "desconhecida") for v in resultado["violations"]
            ]
            historico_por_tentativa.append(regras_desta_tentativa)

            feedback_estruturado = construir_feedback_estruturado(
                resultado["violations"],
                historico_violacoes,
            )
            
            historico_violacoes.extend(
                violacao.get("rule", "desconhecida") for violacao in resultado["violations"]
            )
            
            feedback_anterior = feedback_estruturado

    #print("⚠️ Número máximo de tentativas atingido. Retornando último plano.")
    #return PlanoResultado(plano, historico_violacoes)

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
        "physical_restrictions": {"has_injury": False, "injury_region": None},
        "equipment": []
    }

    plano_final = pipeline_principal(user_input)
    if plano_final:
        print("\n--- PLANO FINAL ---")
        print(json.dumps(plano_final, indent=2, ensure_ascii=False))
    print("\n")
