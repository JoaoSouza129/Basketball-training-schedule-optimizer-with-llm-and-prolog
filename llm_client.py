import json
from groq import Groq
import dotenv
import sys
import os
from huggingface_hub import InferenceClient
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
dotenv.load_dotenv()
API_KEY=os.getenv("GROQ_API_KEY")
HF_API_KEY=os.getenv("HF-API-KEY")

# Carrega o schema JSON
def load_output_schema() -> dict:
    schema_path = os.path.join(os.path.dirname(__file__), "schemas", "output_schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def gerar_user_prompt(atleta: dict, blocos: list, feedback_anterior: str = "") -> str:
    objetivo = atleta["primary_goal"]
    dias_disponiveis = len(atleta["availability"]["available_days"])
    minutos_max = atleta["availability"]["minutes_per_day"]

    prompt = f"""
### Dados do Atleta
{json.dumps(atleta, indent=2, ensure_ascii=False)}

### Catálogo de Exercícios Elegíveis
{json.dumps(blocos, indent=2, ensure_ascii=False)}


### Missão Específica
    1. Seleciona os blocos que melhor atacam o objetivo principal do atleta: "{objetivo}".
    2. Respeita a disponibilidade de {dias_disponiveis} dias de treino.
    3. Garante que a duração total diária não excede os {minutos_max} minutos.
    4. Gera o output estritamente em JSON com a estrutura especificada no system prompt.
    5. IMPORTANTE: Toda chave JSON deve estar entre aspas duplas.
    """

    if feedback_anterior:
        prompt += f"""
### Feedback da Tentativa Anterior
O plano anterior foi rejeitado pelas seguintes razões:
{feedback_anterior}
Por favor corrige esses erros e gera um novo plano.
"""

    return prompt

def call_llm(system_prompt: str, user_prompt: str)->dict:
    client=Groq(api_key=API_KEY)
    schema = load_output_schema()
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model="meta-llama/llama-4-scout-17b-16e-instruct",  # Modelo potente
        temperature=0.3,  # Reduzido para mais consistência
        max_tokens=8192,
        response_format={
            "type": "json_object",
            "schema": schema  # Passa o schema para guiar a geração
        }
    )
    # Extrair o conteúdo do assistant
    json_str = response.choices[0].message.content.strip()

    # Tentar parsear o JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM devolveu JSON inválido: {json_str}") from e
        
def call_llm_hf(system_prompt: str, user_prompt: str) -> dict:
    client = InferenceClient(
        model="meta-llama/Llama-3.1-8B-Instruct",
        token=HF_API_KEY
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat_completion(
        messages=messages,
        max_tokens=8192,
        temperature=0.1,
        seed=42,
    )
    
    return response.choices[0].message.content