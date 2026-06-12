
def count_unique_blocks(weekly_plan:dict)->int:
    DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    seen = set()
    
    for day in DAYS:
        day_obj = weekly_plan.get(day)
        if not day_obj:
            # day_obj pode ser None ou não existir -> dia de descanso
            continue

        # Esperamos um dict com key "sessions"
        sessions = day_obj.get("sessions") if isinstance(day_obj, dict) else None
        if not sessions:
            continue

        # sessions deve ser iterável de dicionários
        for sess in sessions:
            if not isinstance(sess, dict):
                continue
            # tentar várias chaves possíveis para compatibilidade
            block_id = sess.get("block_id") or sess.get("id") or sess.get("block")
            if block_id:
                seen.add(block_id)

    return len(seen)

def calculate_goal_focus(weekly_plan:dict, primary_goal:str)->float:
    DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    total_minutes = 0
    goal_minutes = 0
    
    for day in DAYS:
        day_obj = weekly_plan.get(day)
        if not day_obj or not isinstance(day_obj, dict):
            continue

        # Somar minutos totais do dia
        total_minutes += day_obj.get("total_minutes", 0)

        # Processar sessões
        sessions = day_obj.get("sessions")
        if not sessions or not isinstance(sessions, list):
            continue

        for sess in sessions:
            if not isinstance(sess, dict):
                continue

            duration = sess.get("duration_minutes", 0)
            tags = sess.get("tags", [])

            if primary_goal in tags:
                goal_minutes += duration

    # Evitar divisão por zero
    if total_minutes == 0:
        return 0.0

    return goal_minutes / total_minutes
            
def evaluate_distribution(weekly_plan:dict, available_days:int)->int:
    DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    score = 20

    # 1. Contar dias de treino reais
    training_days_count = 0
    consecutive = 0
    max_consecutive = 0

    for day in DAYS:
        session = weekly_plan.get("weekly_plan", {}).get(day)
        is_training_day = session is not None

        if is_training_day:
            training_days_count += 1
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0

    # Penalizar mais de 2 dias consecutivos
    if max_consecutive > 2:
        score -= 5

    # Penalizar se número de dias não bate certo
    if training_days_count != available_days:
        score -= 5

    return max(0, score)
            
def calculate_intesity_progression(weekly_plan:dict)->int:
    DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    score = 20
    intensity_history = []

    # 1. Construir série de intensidade diária
    for day in DAYS:
        obj = weekly_plan.get("weekly_plan", {}).get(day)
        if obj is None:
            intensity_history.append(0)
        else:
            # Média ponderada da intensidade dos blocos
            total_duration = sum(s.get("duration_minutes", 0) for s in obj.get("sessions", []))
            weighted_sum = sum(
                s.get("intensity", 0) * s.get("duration_minutes", 0)
                for s in obj.get("sessions", [])
            )
            avg_intensity = weighted_sum / total_duration if total_duration > 0 else 0
            intensity_history.append(avg_intensity)

    # 2. Analisar sequências de alta intensidade
    for i in range(len(intensity_history) - 1):
        curr = intensity_history[i]
        next_day = intensity_history[i + 1]

        # Penalizar se dois dias seguidos com intensidade >= 4
        if curr >= 4 and next_day >= 4:
            score -= 3

        # Recompensar descanso após alta intensidade
        if curr >= 4 and next_day == 0:
            score += 1  # pequena recompensa

    return max(0, min(20, score))  # limitar entre 0 e 20
def evaluate_time_efficiency(weekly_plan:dict, athlete: dict)->int:
    score = 20
    minutos_por_dia = athlete["availability"]["minutes_per_day"]
    dias_treino = athlete["availability"]["available_days"]

    weekly = weekly_plan.get("weekly_plan", {})

    for day in dias_treino:
        obj = weekly.get(day)
        if obj is None:
            # Dia de descanso, penalizar levemente
            score -= 2
            continue

        minutos_planejados = obj.get("total_minutes", 0)

        if minutos_planejados < 0.7 * minutos_por_dia:
            # Pouco tempo utilizado
            score -= 3
        elif minutos_planejados > minutos_por_dia:
            # Erro de plano (tempo excedido)
            score -= 5

    return max(0, min(20, score))
def calculate_score(athlete: dict, plan:dict, catalog:list)->dict:
    weekly_plan = plan.get("weekly_plan", {})

    variety = count_unique_blocks(weekly_plan)
    goal_focus = calculate_goal_focus(weekly_plan, athlete["primary_goal"])
    distribution = evaluate_distribution(weekly_plan, len(athlete["availability"]["available_days"]))
    progression = calculate_intesity_progression(plan)
    efficiency = evaluate_time_efficiency(plan, athlete)

    # Normalizar scores conforme max
    score_details = {
        "variety": {
            "score": min(20, variety * 4),  # até 5 blocos únicos = 20 pts
            "max": 20,
            "notes": f"Blocos únicos usados: {variety}"
        },
        "goal_alignment": {
            "score": round(goal_focus * 20, 1),
            "max": 20,
            "notes": f"% de tempo no objetivo '{athlete['primary_goal']}': {round(goal_focus * 100, 1)}%"
        },
        "distribution": {
            "score": distribution,
            "max": 20,
            "notes": "Distribuição de dias de treino"
        },
        "progression": {
            "score": progression,
            "max": 20,
            "notes": "Variação saudável de intensidade"
        },
        "efficiency": {
            "score": efficiency,
            "max": 20,
            "notes": "Aproveitamento do tempo disponível"
        }
    }

    total = sum(item["score"] for item in score_details.values())
    return {
        "score": round(total, 1),
        "details": score_details
    }