# test_llm.py
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from llm_client import call_llm, call_llm_ollama_cloud
from load_system_prompt import load_system_prompt

athlete_mock = {
    "profile": {"level": "intermediate"},
    "goal": {"primary": "shooting"},
    "availability": {
        "available_days": ["monday", "wednesday"],
        "minutes_per_day": 45
    },
    "physical_restrictions": {"injury_region": None}
}

blocks_mock = [
    {
        "id": "warmup_dynamic",
        "name": "Aquecimento Dinâmico",
        "category": "warmup",
        "tags": ["warmup"],
        "duration_minutes": 10,
        "intensity_range": [1, 2]
    },
    {
        "id": "shooting_three_point",
        "name": "Triplos",
        "category": "shooting",
        "tags": ["technical"],
        "duration_minutes": 30,
        "intensity_range": [2, 3]
    }
]

user_prompt = f"""
### Dados do Atleta
{json.dumps(athlete_mock, indent=2, ensure_ascii=False)}

### Catálogo de Exercícios Elegíveis
{json.dumps(blocks_mock, indent=2, ensure_ascii=False)}

### Missão Específica
1. Objetivo: shooting
2. Disponibilidade: 2 dias
3. Tempo máx.: 45 minutos
"""

system_prompt = load_system_prompt()

result = call_llm_ollama_cloud(system_prompt, user_prompt)
print(json.dumps(result, indent=2, ensure_ascii=False))