import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Agora os imports vão funcionar
from prolog_bridge import validate_plan
from normalizer import normalize_input

athlete_raw = {
    "profile": {"level": "intermediate", "experience_years": 2},
    "primary_goal": "shooting",
    "availability": {
        "days_per_week": 3,
        "minutes_per_day": 60,
        "available_days": ["monday", "wednesday", "friday"]
    },
    "physical_restrictions": {"has_injury": False, "injury_region": None}
}

athlete = normalize_input(athlete_raw)

plan = {
    "weekly_plan": {
        "monday": {
            "total_minutes": 120,
            "sessions": [
                {"block_id": "warmup_dynamic", "duration_minutes": 40, "intensity": 2, "tags": ["warmup"]},
                {"block_id": "shooting_catch_and_shoot", "duration_minutes": 30, "intensity": 3, "tags": ["technical"]},
                {"block_id": "cooldown_static_stretching", "duration_minutes": 50, "intensity": 1, "tags": ["recovery"]}
            ]
        },
        "tuesday": None,
        "wednesday": {
            "total_minutes": 70,
            "sessions": [
                {"block_id": "conditioning_hiit", "duration_minutes": 60, "intensity": 4, "tags": ["physical"]},
                {"block_id": "cooldown_static_stretching", "duration_minutes": 10, "intensity": 1, "tags": ["recovery"]}
            ]
        },
        "thursday": None,
        "friday": None,
        "saturday": None,
        "sunday": None
        # ... outros dias como None
    },
    "rationale": "Treino balanceado",
    "assumptions": ["Sem lesão"]
}

# Carregar o catálogo (do data/blocks_catalog.json)
import json
with open("data/catalog.json") as f:
    catalog = json.load(f)

result = validate_plan(athlete, plan, catalog)
print(result)