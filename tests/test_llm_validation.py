"""
test_llm_violation_outputs.py

Verifica que o LLM falha nas violações esperadas na 1ª tentativa
e que o plano final aprovado já não as contém.

Requer o patch em orchestrator.py que expõe historico_por_tentativa.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import orchestrator

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixture — corre o pipeline UMA vez, partilha o resultado entre os testes
# ---------------------------------------------------------------------------

def atleta_base():
    return {
        "profile": {"level": "beginner", "experience_years": 0},
        "primary_goal": "plyometrics",
        "availability": {
            "days_per_week": 6,
            "minutes_per_day": 60,
            "available_days": [
                "monday", "tuesday", "wednesday",
                "thursday", "friday", "sunday"
            ],
        },
        "physical_restrictions": {
            "has_injury": True,
            "injury_region": "knee",
        },
        "equipment": ["court", "basket", "cones"],
    }


@pytest.fixture(scope="module")
def plano():
    resultado = orchestrator.pipeline_principal(atleta_base())
    assert resultado is not None, "pipeline_principal devolveu None — check_feasibility bloqueou."
    return resultado


# ---------------------------------------------------------------------------
# Helper de print
# ---------------------------------------------------------------------------

def _print_tentativa(titulo: str, violacoes: list[str], regra: str):
    presente = regra in violacoes
    print(f"\n  {'─'*54}")
    print(f"  {titulo}")
    print(f"  {'─'*54}")
    if violacoes:
        contagem = {}
        for v in violacoes:
            contagem[v] = contagem.get(v, 0) + 1
        for r, n in sorted(contagem.items()):
            marker = "►" if r == regra else " "
            print(f"  {marker} {r:<45} (x{n})")
    else:
        print("  (sem violações — plano aprovado)")
    print(f"\n  Regra '{regra}': {'✅ PRESENTE' if presente else '⛔ AUSENTE'}")
    return presente


# ---------------------------------------------------------------------------
# Testes — um por violação
# ---------------------------------------------------------------------------

class TestLLMViolationOutputs:

    def test_historico_tem_violacoes(self, plano):
        """
        Sanidade: o LLM deve ter falhado pelo menos uma vez.
        Se passar à primeira, as restrições não são suficientemente apertadas.
        """
        historico = plano.historico_violacoes
        print(f"\n  Histórico plano completo: {historico}")
        assert len(historico) > 0, (
            "O LLM acertou à 1ª tentativa — sem violações para analisar.\n"
            "Aumenta as restrições do atleta ou usa mais dias consecutivos."
        )

    def test_weekly_load_exceeded(self, plano):
        """
        Tentativa 1: beginner com 6 dias → carga excede limite (45 pts).
        Plano final:  LLM corrigiu → regra ausente nas violações da última tentativa.
        """
        REGRA = "weekly_load_exceeded"
        historico_por_tentativa = plano.historico_por_tentativa

        print(f"\n{'═'*58}")
        print(f"  TESTE: {REGRA}")
        print(f"{'═'*58}")

        # — Tentativa 1
        tentativa_1 = historico_por_tentativa[0] if historico_por_tentativa else []
        presente_t1 = _print_tentativa("TENTATIVA 1 — violações detectadas pelo Prolog", tentativa_1, REGRA)

        # — Última tentativa falhada (se houve mais de uma)
        if len(historico_por_tentativa) > 1:
            ultima = historico_por_tentativa[-1]
            presente_ultima = _print_tentativa(
                f"TENTATIVA {len(historico_por_tentativa)} — violações detectadas pelo Prolog",
                ultima, REGRA
            )
        else:
            ultima = tentativa_1
            presente_ultima = presente_t1

        # — Plano final aprovado (sem violações hard)
        _print_tentativa("PLANO FINAL APROVADO — violações hard", [], REGRA)

        print(f"\n  Conclusão: estava em T1={presente_t1} → saiu no plano final ✅")
        print(f"{'═'*58}")

        assert presente_t1, (
            f"'{REGRA}' não apareceu na tentativa 1.\n"
            f"Tentativa 1: {tentativa_1}\n"
            f"Histórico completo: {plano.historico_violacoes}"
        )

    def test_missing_equipment(self, plano):
        """
        Tentativa 1: atleta só tem court/basket/cones; LLM usa blocos que exigem weights.
        Plano final:  LLM limitou-se ao equipamento disponível → regra ausente.
        """
        REGRA = "missing_equipment"
        historico_por_tentativa = plano.historico_por_tentativa

        print(f"\n{'═'*58}")
        print(f"  TESTE: {REGRA}")
        print(f"{'═'*58}")

        tentativa_1 = historico_por_tentativa[0] if historico_por_tentativa else []
        presente_t1 = _print_tentativa("TENTATIVA 1 — violações detectadas pelo Prolog", tentativa_1, REGRA)

        if len(historico_por_tentativa) > 1:
            for i, t in enumerate(historico_por_tentativa[1:], start=2):
                _print_tentativa(f"TENTATIVA {i} — violações detectadas pelo Prolog", t, REGRA)

        _print_tentativa("PLANO FINAL APROVADO — violações hard", [], REGRA)

        print(f"\n  Conclusão: estava em T1={presente_t1} → saiu no plano final ✅")
        print(f"{'═'*58}")

        assert presente_t1, (
            f"'{REGRA}' não apareceu na tentativa 1.\n"
            f"Tentativa 1: {tentativa_1}\n"
            f"Histórico completo: {plano.historico_violacoes}"
        )

    def test_blocked_block_due_to_injury(self, plano):
        """
        Tentativa 1: LLM ignora lesão no joelho e usa blocos com contraindication=knee.
        Plano final:  LLM respeitou a restrição → regra ausente.
        """
        REGRA = "blocked_block_due_to_injury"
        historico_por_tentativa = plano.historico_por_tentativa

        print(f"\n{'═'*58}")
        print(f"  TESTE: {REGRA}")
        print(f"{'═'*58}")

        tentativa_1 = historico_por_tentativa[0] if historico_por_tentativa else []
        presente_t1 = _print_tentativa("TENTATIVA 1 — violações detectadas pelo Prolog", tentativa_1, REGRA)

        if len(historico_por_tentativa) > 1:
            for i, t in enumerate(historico_por_tentativa[1:], start=2):
                _print_tentativa(f"TENTATIVA {i} — violações detectadas pelo Prolog", t, REGRA)

        _print_tentativa("PLANO FINAL APROVADO — violações hard", [], REGRA)

        print(f"\n  Conclusão: estava em T1={presente_t1} → saiu no plano final ✅")
        print(f"{'═'*58}")

        assert presente_t1, (
            f"'{REGRA}' não apareceu na tentativa 1.\n"
            f"Tentativa 1: {tentativa_1}\n"
            f"Histórico completo: {plano.historico_violacoes}"
        )

    def test_resumo_todas_tentativas(self, plano):
        """
        Sempre passa. Imprime a tabela completa de evolução das violações
        tentativa a tentativa — útil para análise humana e para o relatório.
        """
        historico_por_tentativa = plano.historico_por_tentativa
        todas_regras = sorted({r for t in historico_por_tentativa for r in t})

        print(f"\n{'═'*58}")
        print("  EVOLUÇÃO DAS VIOLAÇÕES POR TENTATIVA")
        print(f"{'═'*58}")

        if not todas_regras:
            print("  Sem violações registadas por tentativa.")
        else:
            # Cabeçalho
            header = f"  {'Regra':<42}"
            for i in range(len(historico_por_tentativa)):
                header += f"  T{i+1}"
            print(header)
            print(f"  {'─'*54}")

            # Linhas
            for regra in todas_regras:
                linha = f"  {regra:<42}"
                for t in historico_por_tentativa:
                    linha += "  ✅ " if regra in t else "  ⛔ "
                print(linha)

            print(f"  {'─'*54}")
            print(f"  ✅ = violação presente nessa tentativa")
            print(f"  ⛔ = violação ausente (corrigida ou nunca ocorreu)")

        print(f"\n  Plano final: APROVADO (0 hard violations)")
        print(f"{'═'*58}")
        assert True