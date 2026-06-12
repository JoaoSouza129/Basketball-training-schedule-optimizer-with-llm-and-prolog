# app.py
import sys
import os
import streamlit as st
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator import pipeline_principal
from catalog_loader import load_catalog
from score_calculator import calculate_score
catalog=load_catalog()
st.title("🏀 Otimizador de Treinos de Basquetebol")
st.markdown("Insira os dados do atleta e obtenha um plano semanal otimizado.")

# Campos do formulário
nivel = st.selectbox("Nível", ["beginner", "intermediate", "advanced"])
objetivo = st.selectbox("Objetivo Principal", ["shooting", "conditioning", "defense"])
dias = st.multiselect("Dias disponíveis", ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])
minutos = st.slider("Minutos por dia", 30, 120, 60)

# Botão para gerar plano
if st.button("Gerar Plano"):
    user_input = {
        "profile": {"level": nivel, "experience_years": 2},
        "primary_goal": objetivo,
        "availability": {
            "days_per_week": len(dias),
            "available_days": dias,
            "minutes_per_day": minutos
        },
        "physical_restrictions": {"has_injury": False, "injury_region": None}
    }

    with st.spinner("A gerar plano..."):
        plano = pipeline_principal(user_input)

    if plano:
        st.success("✅ Plano gerado!")

        # Mostrar score
        score_result = calculate_score(user_input, plano, catalog)  # carregar catalog
        st.metric("Pontuação do Plano", score_result["score"])

        # Mostrar plano por dia
        for dia, conteudo in plano["weekly_plan"].items():
            if conteudo:
                st.subheader(f"{dia.capitalize()}: {conteudo['total_minutes']} minutos")
                for bloco in conteudo["sessions"]:
                    st.write(f"- {bloco['block_id']} ({bloco['duration_minutes']} min)")
            else:
                st.subheader(f"{dia.capitalize()}: Descanso")
                