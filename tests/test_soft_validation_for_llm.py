
import pytest
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm_client import call_llm, gerar_user_prompt
from prolog_bridge import validate_plan
from catalog_loader import load_catalog
from score_calculator import calculate_score
from load_system_prompt import load_system_prompt
from orchestrator import completar_plano

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Atletas de teste
# ---------------------------------------------------------------------------

ATLETA_CONSECUTIVO = {
    "profile": {"level": "intermediate", "experience_years": 3},
    "primary_goal": "strength",
    "availability": {
        "days_per_week": 3,
        "minutes_per_day": 75,
        "available_days": ["monday", "tuesday", "thursday"],
    },
    "physical_restrictions": {"has_injury": False, "injury_region": None},
    "equipment": ["basketball", "court", "basket", "weights", "resistance_bands"]
}

ATLETA_INTERCALADO = {
    "profile": {"level": "intermediate", "experience_years": 3},
    "primary_goal": "strength",
    "availability": {
        "days_per_week": 3,
        "minutes_per_day": 75,
        "available_days": ["monday", "wednesday", "friday"],
    },
    "physical_restrictions": {"has_injury": False, "injury_region": None},
    "equipment": ["basketball", "court", "basket", "weights", "resistance_bands"]
}   

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _gerar_e_avaliar(atleta: dict, system_prompt: str, catalog: list) -> dict:
    MAX_TENTATIVAS = 3
    feedback, plano, resultado = "", None, None

    for _ in range(MAX_TENTATIVAS):
        user_prompt = gerar_user_prompt(atleta, catalog, feedback)
        plano = call_llm(system_prompt, user_prompt)
        plano = completar_plano(plano)
        resultado = validate_plan(atleta, plano, catalog)
        if resultado["is_valid"]:
            break
        linhas = [
            f"- Regra {v.get('rule')}: dia={v.get('arg1')}, valor={v.get('arg2')}, limite={v.get('arg3')}"
            for v in resultado["violations"]
        ]
        feedback = "\n".join(linhas)

    score = calculate_score(atleta, plano, catalog, resultado.get("soft_violations", []))
    return {
        "plano": plano,
        "score": score,
        "soft_violations": resultado.get("soft_violations", []),
        "hard_violations": resultado.get("violations", []),
        "is_valid": resultado["is_valid"],
    }

# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def catalog():
    return load_catalog()

@pytest.fixture(scope="module")
def system_prompt():
    return load_system_prompt()


class TestComparativoLLM:

    @pytest.fixture(scope="class")
    def resultados(self, catalog, system_prompt):
        return {
            "a": _gerar_e_avaliar(ATLETA_CONSECUTIVO, system_prompt, catalog),
            "b": _gerar_e_avaliar(ATLETA_INTERCALADO, system_prompt, catalog),
        }

    # --- Cenário A (consecutivo) ---

    def test_a_plano_valido(self, resultados):
        assert resultados["a"]["is_valid"], (
            f"Cenário A tem hard violations: {resultados['a']['hard_violations']}"
        )

    def test_a_imprime_resultado(self, resultados):
        r = resultados["a"]
        print(f"\n{'='*60}")
        print("CENÁRIO A — dias consecutivos: seg / ter / qui")
        print(f"  Soft violations ({len(r['soft_violations'])}): {r['soft_violations']}")
        print(f"  Score total: {r['score']['score']}/100")
        for k, v in r["score"]["details"].items():
            print(f"    {k}: {v['score']}/{v['max']}  — {v['notes']}")
        print(f"{'='*60}")
        assert True  # sempre passa, serve só para ver o output com pytest -s

    # --- Cenário B (intercalado) ---

    def test_b_plano_valido(self, resultados):
        assert resultados["b"]["is_valid"], (
            f"Cenário B tem hard violations: {resultados['b']['hard_violations']}"
        )

    def test_b_sem_soft_violations(self, resultados):
        """Dias intercalados → nunca há treino intenso em dois dias consecutivos."""
        regras = [sv.get("rule") for sv in resultados["b"]["soft_violations"]]
        print(f"\n[Cenário B] Soft violations: {resultados['b']['soft_violations']}")
        assert "recommend_rest_after_high_intensity" not in regras, (
            f"Cenário B não devia ter soft violations mas encontrei: {regras}"
        )

    def test_b_imprime_resultado(self, resultados):
        r = resultados["b"]
        print(f"\n{'='*60}")
        print("CENÁRIO B — dias intercalados: seg / qua / sex")
        print(f"  Soft violations ({len(r['soft_violations'])}): {r['soft_violations']}")
        print(f"  Score total: {r['score']['score']}/100")
        for k, v in r["score"]["details"].items():
            print(f"    {k}: {v['score']}/{v['max']}  — {v['notes']}")
        print(f"{'='*60}")
        assert True

    # --- Comparação ---

    def test_comparacao_scores(self, resultados):
        score_a = resultados["a"]["score"]["score"]
        score_b = resultados["b"]["score"]["score"]
        print(f"\n{'='*60}")
        print("COMPARAÇÃO FINAL")
        print(f"  Cenário A (consecutivo): {score_a}/100")
        print(f"  Cenário B (intercalado): {score_b}/100")
        print(f"  Diferença (B - A): {score_b - score_a:+.1f} pontos")
        print(f"{'='*60}")
        assert score_a > 0 and score_b > 0

    def test_b_score_maior_ou_igual_a(self, resultados):
        """
        B deve ter score >= A (com margem de 5 pts para variação do LLM).
        A penalização do componente 'progression' em A (soft violations)
        deve resultar num score inferior.
        """
        score_a = resultados["a"]["score"]["score"]
        score_b = resultados["b"]["score"]["score"]
        assert score_b >= (score_a - 5.0), (
            f"Score B ({score_b}) ficou mais de 5 pts abaixo de A ({score_a}). "
            f"Diferença: {score_b - score_a:.1f}"
        )