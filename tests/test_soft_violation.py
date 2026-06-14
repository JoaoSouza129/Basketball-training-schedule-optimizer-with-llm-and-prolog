"""
test_soft_violations.py

Teste de integração que verifica que o pipeline detecta soft violations
quando o LLM gera um plano com alta intensidade em dias consecutivos
sem descanso no dia seguinte.

NÃO chama o LLM real — usa um plano sintético para garantir
que a soft violation é disparada deterministicamente.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from prolog_bridge import validate_plan
from catalog_loader import load_catalog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def catalog():
    return load_catalog()

@pytest.fixture
def athlete_sem_lesao():
    return {
        "profile": {"level": "beginner", "experience_years": 1},
        "primary_goal": "conditioning",
        "availability": {
            "days_per_week": 3,
            "minutes_per_day": 60,
            "available_days": ["monday", "tuesday", "wednesday"],
        },
        "physical_restrictions": {"has_injury": False, "injury_region": None},
        "equipment": ["basketball", "court", "basket"],
    }

def _make_session(block_id, duration, intensity, tags):
    return {
        "block_id": block_id,
        "duration_minutes": duration,
        "intensity": intensity,
        "tags": tags,
    }

# ---------------------------------------------------------------------------
# Helpers para construir planos
# ---------------------------------------------------------------------------

def plano_com_alta_intensidade_consecutiva(catalog):
    """
    Segunda, terça e quarta com intensidade >= 4 e sem descanso entre elas.
    → soft violation deve disparar para segunda (e terça).
    """
    bloco_intenso = next(b for b in catalog if b["intensity_range"][1] >= 4)
    s = _make_session(bloco_intenso["id"], 30, 4, ["conditioning"])
    return {
        "weekly_plan": {
            "monday":    {"sessions": [s], "total_minutes": 30},
            "tuesday":   {"sessions": [_make_session(bloco_intenso["id"], 30, 2, ["conditioning"])], "total_minutes": 30},
            "wednesday": {"sessions": [s], "total_minutes": 30},
            "thursday":  None,
            "friday":    None,
            "saturday":  None,
            "sunday":    None,
        }
    }

def plano_com_descanso_apos_alta_intensidade(catalog):
    """
    Segunda com alta intensidade, terça de descanso, quarta treino.
    → soft violation NÃO deve disparar.
    """
    bloco_intenso = next(b for b in catalog if b["intensity_range"][1] >= 4)
    s = _make_session(bloco_intenso["id"], 30, 4, ["conditioning"])
    return {
        "weekly_plan": {
            "monday":    {"sessions": [s], "total_minutes": 30},
            "tuesday":   None,
            "wednesday": {"sessions": [s], "total_minutes": 30},
            "thursday":  None,
            "friday":    None,
            "saturday":  None,
            "sunday":    None,
        }
    }

# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestSoftViolationDisparada:
    """O plano é VÁLIDO (sem hard violations) mas tem soft violations."""

    def test_plano_e_valido(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        assert resultado["is_valid"], (
            f"Esperava plano válido mas obteve hard violations: {resultado['violations']}"
        )

    def test_soft_violation_detectada(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        soft = resultado.get("soft_violations", [])
        assert len(soft) > 0, (
            "Esperava >= 1 soft violation mas o resultado foi vazio."
        )

    def test_soft_violation_e_do_tipo_correto(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        regras = [sv.get("rule") for sv in resultado.get("soft_violations", [])]
        assert "recommend_rest_after_high_intensity" in regras, (
            f"Esperava recommend_rest_after_high_intensity, obtive: {regras}"
        )

    def test_soft_violation_aponta_dia_correto(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        soft = resultado.get("soft_violations", [])
        dias = [sv.get("arg1") for sv in soft
                if sv.get("rule") == "recommend_rest_after_high_intensity"]
        assert "monday" in dias, (
            f"Esperava 'monday' como dia de origem, obtive: {dias}"
        )

    def test_soft_violation_tem_estrutura_completa(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        for sv in resultado.get("soft_violations", []):
            assert "rule" in sv
            assert "arg1" in sv
            assert "arg2" in sv


class TestSoftViolationAusente:
    """Quando há descanso após alta intensidade, não deve haver soft violation."""

    def test_sem_soft_violation_quando_descansa(self, athlete_sem_lesao, catalog):
        athlete = {
            **athlete_sem_lesao,
            "availability": {
                "days_per_week": 2,
                "minutes_per_day": 60,
                "available_days": ["monday", "wednesday"],
            },
        }
        plano = plano_com_descanso_apos_alta_intensidade(catalog)
        resultado = validate_plan(athlete, plano, catalog)
        regras = [sv.get("rule") for sv in resultado.get("soft_violations", [])]
        assert "recommend_rest_after_high_intensity" not in regras, (
            f"Não esperava soft violation mas encontrei: {regras}"
        )


class TestRetornoDoOrquestrador:
    """Garante que validate_plan devolve sempre o campo soft_violations."""

    def test_campo_sempre_presente(self, athlete_sem_lesao, catalog):
        athlete = {
            **athlete_sem_lesao,
            "availability": {
                "days_per_week": 2,
                "minutes_per_day": 60,
                "available_days": ["monday", "wednesday"],
            },
        }
        plano = plano_com_descanso_apos_alta_intensidade(catalog)
        resultado = validate_plan(athlete, plano, catalog)
        assert "soft_violations" in resultado

    def test_campo_e_lista(self, athlete_sem_lesao, catalog):
        plano = plano_com_alta_intensidade_consecutiva(catalog)
        resultado = validate_plan(athlete_sem_lesao, plano, catalog)
        assert isinstance(resultado.get("soft_violations"), list)