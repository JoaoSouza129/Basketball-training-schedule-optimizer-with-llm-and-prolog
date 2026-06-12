import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from catalog_loader import get_eligible_blocks, check_feasibility, FULL_CATALOG


def atleta_base():
    return {
        "profile": {"level": "intermediate", "experience_years": 2},
        "primary_goal": "shooting",
        "availability": {
            "days_per_week": 3,
            "minutes_per_day": 60,
            "available_days": ["monday", "wednesday", "friday"],
        },
        "physical_restrictions": {
            "has_injury": False,
            "injury_region": None,
        },
        "equipment": ["court", "basket", "cones"],
    }


class TestCatalogLoader:
    def test_atleta_sem_restricoes(self):
        """Atleta intermédio sem lesão deve ter muitos blocos disponíveis."""
        atleta = atleta_base()
        eligible = get_eligible_blocks(atleta)
        assert len(eligible) > 10  # deve ter pelo menos 10+ blocos

    def test_iniciante_recebe_blocos_beginner(self):
        """Iniciante só deve receber blocos com beginner na level_suitability."""
        atleta = atleta_base()
        atleta["profile"]["level"] = "beginner"
        eligible = get_eligible_blocks(atleta)
        for b in eligible:
            assert "beginner" in b["level_suitability"]

    def test_lesao_joelho_bloqueia_pliometria(self):
        """Lesão no joelho deve excluir blocos com knee_impact."""
        atleta = atleta_base()
        atleta["physical_restrictions"]["injury_region"] = "knee"
        atleta["physical_restrictions"]["has_injury"] = True
        eligible = get_eligible_blocks(atleta)
        blocked_ids = {b["id"] for b in FULL_CATALOG if "knee" in b["contraindications"]}
        eligible_ids = {b["id"] for b in eligible}
        # Nenhum bloco contraindicado para joelho deve estar nos elegíveis
        assert blocked_ids.isdisjoint(eligible_ids)

    def test_sem_equipamento_recebe_apenas_bodyweight(self):
        """Atleta sem equipamento só recebe blocos com required_equipment vazio."""
        atleta = atleta_base()
        atleta["equipment"] = []
        eligible = get_eligible_blocks(atleta)
        for b in eligible:
            assert b["required_equipment"] == [], f"{b['id']} requer equipamento"

    def test_avancado_recebe_blocos_advanced(self):
        """Avançado recebe blocos advanced e intermediate (mas não beginner-only)."""
        atleta = atleta_base()
        atleta["profile"]["level"] = "advanced"
        eligible = get_eligible_blocks(atleta)
        for b in eligible:
            assert "advanced" in b["level_suitability"] or "intermediate" in b["level_suitability"]

    def test_check_feasibility_ok(self):
        """Atleta normal não deve ter problemas de exequibilidade."""
        atleta = atleta_base()
        eligible = get_eligible_blocks(atleta)
        issues = check_feasibility(atleta, eligible)
        assert issues == []

    def test_check_feasibility_sem_blocos(self):
        """Se não há blocos elegíveis, deve reportar."""
        atleta = atleta_base()
        issues = check_feasibility(atleta, [])
        assert len(issues) > 0
        assert "Nenhum bloco elegível" in issues[0]

    def test_check_feasibility_tempo_curto(self):
        """Tempo muito curto deve ser reportado."""
        atleta = atleta_base()
        atleta["availability"]["minutes_per_day"] = 5
        eligible = get_eligible_blocks(atleta)
        issues = check_feasibility(atleta, eligible)
        assert any("demasiado curto" in i for i in issues)

    def test_check_feasibility_7_dias(self):
        """7 dias de treino deve gerar aviso de descanso."""
        atleta = atleta_base()
        atleta["availability"]["days_per_week"] = 7
        eligible = get_eligible_blocks(atleta)
        issues = check_feasibility(atleta, eligible)
        assert any("descanso mínimo" in i for i in issues)
