"""
test_score_benchmark.py
-----------------------
Gera planos 10 vezes com o pipeline completo (LLM + Prolog) e calcula a média
dos scores produzidos pelo score_calculator.

Corre com:
    pytest tests/test_score_benchmark.py -v -s

A flag -s é obrigatória para ver os prints no terminal.
"""

import pytest
import sys
import os

# Garantir que o diretório raiz do projeto está no path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Mudar o CWD para a raiz do projeto, necessário para os paths relativos
# de catalog.json, schemas/, prompts/ funcionarem corretamente
os.chdir(PROJECT_ROOT)

from orchestrator import pipeline_principal
from catalog_loader import load_catalog
from score_calculator import calculate_score

# ─────────────────────────────────────────────
# Perfil de atleta usado em todas as iterações
# ─────────────────────────────────────────────
USER_INPUT = {
    "profile": {"level": "intermediate", "experience_years": 3},
    "primary_goal": "shooting",
    "availability": {
        "days_per_week": 3,
        "available_days": ["monday", "wednesday", "friday"],
        "minutes_per_day": 60,
    },
    "physical_restrictions": {"has_injury": False, "injury_region": None},
    "equipment": [],
}

NUM_RUNS = 10


def test_benchmark_score_medio():
    """
    Gera NUM_RUNS planos e imprime:
      - O score de cada iteração
      - A média total e por dimensão
    O teste passa se pelo menos metade das gerações produzir um plano válido.
    """
    catalog = load_catalog()

    scores_totais = []
    scores_por_dimensao = {
        "variety": [],
        "goal_alignment": [],
        "distribution": [],
        "progression": [],
        "efficiency": [],
    }
    falhas = 0

    print(f"\n{'='*60}")
    print(f"  BENCHMARK DE SCORE — {NUM_RUNS} iterações")
    print(f"  Atleta: {USER_INPUT['profile']['level']} | Objetivo: {USER_INPUT['primary_goal']}")
    print(f"  Dias: {USER_INPUT['availability']['available_days']}")
    print(f"{'='*60}")

    for i in range(1, NUM_RUNS + 1):
        print(f"\n[Iteração {i}/{NUM_RUNS}] A gerar plano...")
        try:
            plano = pipeline_principal(USER_INPUT)

            if plano is None:
                print(f"  ⚠️  Pipeline retornou None (inviabilidade detectada). A saltar.")
                falhas += 1
                continue

            resultado_score = calculate_score(USER_INPUT, plano, catalog)
            score_total = resultado_score["score"]
            detalhes = resultado_score["details"]

            scores_totais.append(score_total)
            for dim in scores_por_dimensao:
                if dim in detalhes:
                    scores_por_dimensao[dim].append(detalhes[dim]["score"])

            # Imprimir detalhe da iteração
            print(f"  ✅ Score: {score_total}/100")
            for dim, info in detalhes.items():
                print(f"     {dim:<20} {info['score']}/{info['max']}  — {info['notes']}")

        except Exception as e:
            print(f"  ❌ Erro na iteração {i}: {e}")
            falhas += 1

    # ─── Resultados finais ───
    print(f"\n{'='*60}")
    print(f"  RESULTADOS FINAIS")
    print(f"{'='*60}")

    if not scores_totais:
        print("  ⛔ Nenhuma geração bem-sucedida. Impossível calcular médias.")
        # Falha o teste se zero planos foram gerados
        assert False, "Nenhum plano foi gerado com sucesso em nenhuma das iterações."

    media_total = sum(scores_totais) / len(scores_totais)
    score_min = min(scores_totais)
    score_max = max(scores_totais)

    print(f"\n  Iterações bem-sucedidas : {len(scores_totais)}/{NUM_RUNS}")
    print(f"  Falhas                  : {falhas}/{NUM_RUNS}")
    print(f"\n  {'Dimensão':<25} {'Média':>8} {'/ Max':>6}")
    print(f"  {'-'*42}")
    for dim, valores in scores_por_dimensao.items():
        if valores:
            media_dim = sum(valores) / len(valores)
            print(f"  {dim:<25} {media_dim:>7.1f} {'/ 20':>6}")
        else:
            print(f"  {dim:<25} {'N/A':>7} {'/ 20':>6}")

    print(f"  {'-'*42}")
    print(f"  {'MÉDIA TOTAL':<25} {media_total:>7.1f} {'/ 100':>6}")
    print(f"  {'MÍNIMO':<25} {score_min:>7.1f} {'/ 100':>6}")
    print(f"  {'MÁXIMO':<25} {score_max:>7.1f} {'/ 100':>6}")
    print(f"{'='*60}\n")

    # O teste passa se pelo menos metade das tentativas tiver sucesso
    assert len(scores_totais) >= NUM_RUNS // 2, (
        f"Apenas {len(scores_totais)}/{NUM_RUNS} planos foram gerados com sucesso."
    )
    # E se a média for maior que 0 (básico de sanidade)
    assert media_total > 0, "Média de scores é zero — algo está errado."


# ─────────────────────────────────────────────
# Permite correr diretamente: python test_score_benchmark.py
# ─────────────────────────────────────────────
if __name__ == "__main__":
    test_benchmark_score_medio()
