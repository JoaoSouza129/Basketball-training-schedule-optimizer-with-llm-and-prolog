import json
import dotenv
from groq import Groq
import sys
import os
import urllib.error
import urllib.request
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
dotenv.load_dotenv()
API_KEY=os.getenv("GROQ_API_KEY")
OLLAMA_API_KEY=os.getenv("OLLAMA-API-KEY")
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_CLOUD_MODEL =  "gemma3:12b-cloud"


# Carrega o schema JSON
def load_output_schema() -> dict:
    schema_path = os.path.join(os.path.dirname(__file__), "schemas", "output_schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if text.lower().startswith("json"):
        text = text[4:].lstrip()

    first_object = text.find("{")
    last_object = text.rfind("}")
    if first_object != -1 and last_object != -1 and last_object > first_object:
        text = text[first_object : last_object + 1]

    return text

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
        feedback_texto = feedback_anterior
        if isinstance(feedback_anterior, dict):
            feedback_texto = json.dumps(feedback_anterior, indent=2, ensure_ascii=False)

        prompt += f"""
### Feedback da Tentativa Anterior
O plano anterior foi rejeitado. Usa esta informação como contexto obrigatório para corrigir a próxima resposta:
```json
{feedback_texto}
```

### Instrução de Correção
- Corrige todas as violações listadas no feedback.
- Se a mesma violação se repetir mais de 2 vezes, usa o raciocinio logico para mudar a estratégia do treino.
- Mantém o output estritamente em JSON válido.
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
        temperature=1,  # Reduzido para mais consistência
        max_tokens=8192,
        response_format={
            "type": "json_object",
            "schema": schema  # Passa o schema para guiar a geração
        }
    )
    # Extrair o conteúdo do assistant
    json_str = _extract_json_text(response.choices[0].message.content)

    # Tentar parsear o JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM devolveu JSON inválido: {json_str}") from e



def _call_ollama_chat(
    system_prompt: str,
    user_prompt: str,
    *,
    host: str,
    model: str,
    api_key: str = "",
    temperature: float = 0.1,
    num_predict: int = 8192,
    seed: int = 42,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "seed": seed,
        },
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Falha ao chamar o Ollama ({e.code}): {error_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Nao foi possivel conectar ao Ollama em {host}. Verifique se o servico esta ativo."
        ) from e

    json_str = _extract_json_text(response_payload.get("message", {}).get("content", ""))

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM devolveu JSON inválido: {json_str}") from e

      


def call_llm_ollama_cloud(system_prompt: str, user_prompt: str) -> dict:
    return _call_ollama_chat(
        system_prompt,
        user_prompt,
        host=OLLAMA_HOST,
        model=OLLAMA_CLOUD_MODEL,
        api_key=OLLAMA_API_KEY,
        temperature=0.1,
        num_predict=8192,
        seed=42,
    )