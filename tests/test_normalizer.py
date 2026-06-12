import pytest
import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from normalizer import normalize_input


def input_valido():
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
    }


class TestNormalizer:
    def test_input_valido(self):
        result = normalize_input(input_valido())
        assert result["profile"]["level"] == "intermediate"
        assert result["availability"]["days_per_week"] == 3
        assert result["physical_restrictions"]["has_injury"] is False

    def test_days_per_week_invalido(self):
        inp = input_valido()
        inp["availability"]["days_per_week"] = 8
        with pytest.raises(ValueError, match="Schema inválido"):
            normalize_input(inp)

    def test_minutes_per_day_abaixo_minimo(self):
        inp = input_valido()
        inp["availability"]["minutes_per_day"] = 10
        with pytest.raises(ValueError, match="Schema inválido"):
            normalize_input(inp)

    def test_available_days_tamanho_errado(self):
        inp = input_valido()
        inp["availability"]["available_days"] = ["monday", "tuesday"]
        with pytest.raises(ValueError, match="available_days tem 2 dias"):
            normalize_input(inp)

    def test_has_injury_sem_regiao(self):
        inp = input_valido()
        inp["physical_restrictions"]["has_injury"] = True
        inp["physical_restrictions"]["injury_region"] = None
        with pytest.raises(ValueError, match="has_injury=true requer injury_region"):
            normalize_input(inp)

    def test_competition_day_em_available_days(self):
        inp = input_valido()
        inp["competition_day"] = "monday"
        with pytest.raises(ValueError, match="competition_day"):
            normalize_input(inp)

    def test_equipment_normalizado(self):
        inp = input_valido()
        inp["equipment"] = ["cones", "2 basketballs", "heavy ball"]
        result = normalize_input(inp)
        assert "cones" in result["equipment"]
        assert "basketball" in result["equipment"]
        assert "heavy_ball" in result["equipment"]

    def test_level_invalido(self):
        inp = input_valido()
        inp["profile"]["level"] = "super_advanced"
        with pytest.raises(ValueError, match="Schema inválido"):
            normalize_input(inp)

    def test_campos_opcionais_ausentes(self):
        inp = input_valido()
        result = normalize_input(inp)
        assert result["position"] is None
        assert result["secondary_goal"] is None
        assert result["competition_day"] is None
        assert result["equipment"] == []

    def test_available_days_repetidos(self):
        inp = input_valido()
        inp["availability"]["available_days"] = ["monday", "monday", "friday"]
        with pytest.raises(ValueError, match="Schema inválido"):
            normalize_input(inp)

