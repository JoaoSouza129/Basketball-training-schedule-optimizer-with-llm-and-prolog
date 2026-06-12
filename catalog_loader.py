import json

def load_catalog()-> dict:
    CATALOG_PATH = "data/catalog.json"

    with open(CATALOG_PATH, encoding="utf-8") as f:
        FULL_CATALOG = json.load(f) 
        return FULL_CATALOG

def get_block_ids()->list:
    catalog=load_catalog()
    
    ids=[]
    for id in catalog:
        ids.append(id["id"])
   
    return ids
def get_eligible_blocks(athlete: dict) -> list:
    """
    Filtra o catálogo completo com base no perfil do atleta.
    Devolve apenas blocos elegíveis (nível, lesão, equipamento).
    """
    level = athlete["profile"]["level"]
    injury_region = athlete["physical_restrictions"]["injury_region"]
    equipment = set(athlete.get("equipment", []))
    FULL_CATALOG=load_catalog()
    eligible = []
    for block in FULL_CATALOG:
        # Filtro 1: nível
        if level not in block["level_suitability"]:
            continue

        # Filtro 2: lesão
        if injury_region and injury_region in block["contraindications"]:
            continue

        # Filtro 3: equipamento
        required = set(block["required_equipment"])
        if required and not required.issubset(equipment):
            continue

        eligible.append(block)

    return eligible


def check_feasibility(athlete: dict, eligible_blocks: list) -> list:
    """
    Verifica se é possível gerar um plano antes de chamar o LLM.
    Devolve lista de problemas (vazia = exequível).
    """
    issues = []

    # Caso 1: zero blocos elegíveis
    if len(eligible_blocks) == 0:
        issues.append(
            "Nenhum bloco elegível encontrado. Verifique restrições de lesão e equipamento."
        )
        return issues  # não vale a pena verificar mais nada

    # Caso 2: tempo por dia muito curto para qualquer sessão mínima
    minutes_per_day = athlete["availability"]["minutes_per_day"]
    min_session = min(b["min_duration_minutes"] for b in eligible_blocks)
    # +10 min para aquecimento obrigatório
    if minutes_per_day < min_session + 10:
        issues.append(
            f"Tempo disponível ({minutes_per_day}min) demasiado curto. "
            f"Sessão mínima possível: {min_session}min + 10min aquecimento = {min_session + 10}min."
        )

    # Caso 3: dias disponíveis = 7 e descanso obrigatório
    days_per_week = athlete["availability"]["days_per_week"]
    if days_per_week == 7:
        issues.append(
            "Não é possível garantir descanso mínimo com 7 dias de treino. "
            "Disponha pelo menos 1 dia de descanso."
        )

    # Caso 4: verificar se há pelo menos 1 bloco de aquecimento disponível
    has_warmup = any("warmup" in b["tags"] for b in eligible_blocks)
    if not has_warmup:
        issues.append(
            "Nenhum bloco de aquecimento disponível para o perfil atual."
        )

    # Caso 5: verificar se há pelo menos 1 bloco de retorno à calma disponível
    has_cooldown = any("cooldown" in b["tags"] for b in eligible_blocks)
    if not has_cooldown:
        issues.append(
            "Nenhum bloco de retorno à calma disponível para o perfil atual."
        )

    return issues
