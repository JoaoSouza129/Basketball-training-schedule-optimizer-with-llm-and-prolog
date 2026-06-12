import json
from jsonschema import validate, ValidationError

SCHEMA_PATH = "schemas/input_schema.json"

with open(SCHEMA_PATH, encoding="utf-8") as f:
    INPUT_SCHEMA = json.load(f)

# Mapeamento de nomes amigáveis → IDs do catálogo
EQUIPMENT_MAP = {
    "2 basketballs": "basketball",
    "cones": "cones",
    "resistance bands": "resistance_bands",
    "weights": "weights",
    "heavy ball": "heavy_ball",
    "bola pesada": "heavy_ball",
    "halteres": "weights",
    "court": "court",
    "basket": "basket",
    "box or step": "box_or_step",
    "foam roller": "foam_roller",
}



def _normalize_equipment(raw_equipment: list) -> list:
    """Converte nomes amigáveis para IDs do catálogo."""
    default_equipment = ["basketball", "court", "basket"]
    
    if not raw_equipment:
        return default_equipment
    
    # Garantir que os defaults estão lá, mesmo que o user tenha enviado outros
    # Usamos set para não haver duplicados
    full_equipment = set(raw_equipment) | set(default_equipment)
    
   
    for item in raw_equipment:
        mapped = EQUIPMENT_MAP.get(item.lower(), item.lower().replace(" ", "_"))
        if mapped not in full_equipment:
            full_equipment.add(mapped)
    
    return list(full_equipment)


def normalize_input(raw: dict) -> dict:
    """
    Valida e normaliza o input do utilizador.
    Devolve dict limpo ou levanta ValueError com mensagem descritiva.
    """
    # 0. Normalizar equipamento ANTES da validação schema
    raw = dict(raw)  # cópia para não modificar o original
    
    if "equipment" in raw:
        raw["equipment"] = _normalize_equipment(raw["equipment"])

    # 1. Validar contra JSON Schema
    try:
        validate(instance=raw, schema=INPUT_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Schema inválido: {e.message}")

    # 2. Validações extra (não capturadas pelo schema)
    avail = raw["availability"]
    days = avail["available_days"]
    days_per_week = avail["days_per_week"]

    if len(days) != days_per_week:
        raise ValueError(
            f"available_days tem {len(days)} dias, mas days_per_week={days_per_week}"
        )

    restrictions = raw["physical_restrictions"]
    if restrictions["has_injury"] and not restrictions.get("injury_region"):
        raise ValueError("has_injury=true requer injury_region preenchido")

    competition_day = raw.get("competition_day")
    if competition_day and competition_day in days:
        raise ValueError(
            f"competition_day ({competition_day}) não pode estar em available_days"
        )

    # 3. Construir dict limpo e normalizado
    normalized = {
        "profile": {
            "level": raw["profile"]["level"],
            "experience_years": raw["profile"]["experience_years"],
        },
        "primary_goal": raw["primary_goal"],
        "availability": {
            "days_per_week": days_per_week,
            "minutes_per_day": avail["minutes_per_day"],
            "available_days": [d.lower() for d in days],
        },
        "physical_restrictions": {
            "has_injury": restrictions["has_injury"],
            "injury_region": restrictions.get("injury_region", None),
        },
        "position": raw.get("position", None),
        "equipment": raw.get("equipment", []),
        "preferences": raw.get("preferences", {"liked_blocks": [], "disliked_blocks": []}),
        "secondary_goal": raw.get("secondary_goal", None),
        "competition_day": raw.get("competition_day", None),
        "initial_metrics": raw.get("initial_metrics", None),
    }
    
   

    return normalized
