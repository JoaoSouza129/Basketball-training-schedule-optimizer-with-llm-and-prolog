import json

ALLOWED_TAGS = {
    "low_intensity", "medium_intensity", "high_intensity",
    "knee_impact", "ankle_impact", "shoulder_impact", "no_impact",
    "technical", "physical", "recovery", "warmup", "cooldown",
    "shooting", "dribbling", "defense", "passing", "footwork",
    "plyometrics", "strength", "conditioning", "mobility", "agility", "sprint",
    "requires_gym", "requires_court", "requires_basket", "requires_cones",
    "beginner_ok", "intermediate_ok", "advanced_only"
}
REQUIRED_FIELDS = {
    "id", "name", "category", "focus_area",
    "min_duration_minutes", "max_duration_minutes",
    "intensity_range", "required_equipment", "contraindications",
    "tags", "level_suitability", "recovery_cost"
}

with open("data/catalog.json", encoding="utf-8") as f:
    catalog = json.load(f)

errors = []
ids = set()
for b in catalog:
    missing = REQUIRED_FIELDS - b.keys()
    if missing:
        errors.append(f"{b.get('id','?')}: campos em falta {missing}")
    if b["id"] in ids:
        errors.append(f"id duplicado: {b['id']}")
    ids.add(b["id"])
    invalid_tags = set(b["tags"]) - ALLOWED_TAGS
    if invalid_tags:
        errors.append(f"{b['id']}: tags inválidas {invalid_tags}")
    if not (1 <= b["recovery_cost"] <= 5):
        errors.append(f"{b['id']}: recovery_cost fora de 1-5")
    if b["intensity_range"][0] > b["intensity_range"][1]:
        errors.append(f"{b['id']}: intensity_range invertido")

print("OK" if not errors else "\n".join(errors))
print(f"Total blocos: {len(catalog)}")
