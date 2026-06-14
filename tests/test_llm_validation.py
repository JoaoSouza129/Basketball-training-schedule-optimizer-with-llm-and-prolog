import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import orchestrator2

def atleta_base():
    return {
        "profile": {"level": "beginner", "experience_years": 0},
        "primary_goal": "plyometrics",
        "availability": {
            "days_per_week": 6,
            "minutes_per_day": 60,
            "available_days": ["monday", "wednesday", "friday","tuesday","thursday","sunday"],
        },
        "physical_restrictions": {
            "has_injury": True,
            "injury_region": "knee",
        },
        "equipment": ["court", "basket", "cones"],
    }

class TestLLM:
    def test_llm_violation_outputs(self):
        atleta = atleta_base()
        plano = orchestrator2.pipeline_principal(atleta)
        print(plano.historico_violacoes)
        assert len(plano.historico_violacoes) > 0
        assert "weekly_load_exceeded" in plano.historico_violacoes
        assert "daily_time_exceeded" in plano.historico_violacoes
        assert "missing_equipment" in plano.historico_violacoes
        assert "blocked_block_due_to_injury" in plano.historico_violacoes
