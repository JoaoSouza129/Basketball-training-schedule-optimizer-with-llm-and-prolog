# Basketball Training Schedule Optimizer (LLM + Prolog)

Projeto que gera um plano semanal de treino de basquetebol com apoio de um LLM e validação lógica em Prolog.

## Visão geral

O fluxo principal combina:
- **Normalização de input** do atleta
- **Filtragem e validação de viabilidade** dos blocos de treino
- **Geração de plano com LLM**
- **Validação rígida em Prolog** (regras hard + soft)
- **Scoring final** da qualidade do plano
- **Interface Streamlit** para uso interativo

## Fluxo da aplicação

1. O utilizador preenche os dados no `app.py`.
2. O `orchestrator.py` coordena a geração do plano.
3. O `llm_client.py` chama o modelo e devolve JSON.
4. O `prolog_bridge.py` converte o plano em factos e valida com SWI-Prolog.
5. Se o plano for válido, o `score_calculator.py` calcula a pontuação final.

## Requisitos

- Python 3.10+
- SWI-Prolog (`swipl`) disponível no PATH
- Dependências Python usadas no projeto:
  - `streamlit`
  - `python-dotenv`
  - `groq`
  - `pytest` (para testes)

## Variáveis de ambiente

Defina no ambiente (ou em `.env`):

- `GROQ_API_KEY`
- `OLLAMA-API-KEY`

## Como executar

### 1) Correr a app

```bash
streamlit run app.py
```

### 2) Correr testes

```bash
pytest -q
```

## Estrutura de pastas

```text
.
├── app.py
├── orchestrator.py
├── llm_client.py
├── normalizer.py
├── catalog_loader.py
├── prolog_bridge.py
├── score_calculator.py
├── load_system_prompt.py
├── data/
│   └── catalog.json
├── prompts/
│   ├── system_prompt.md
│   └── user_prompt.md
├── schemas/
│   ├── input_schema.json
│   └── output_schema.json
├── prolog/
│   ├── constraints.pl
│   ├── run_validation.pl
│   └── test_facts.pl
└── tests/
    ├── debug_test.pl
    ├── sanity-check.py
    ├── test_bridge.py
    ├── test_catalog_loader.py
    ├── test_llm.py
    ├── test_llm_validation.py
    ├── test_normalizer.py
    ├── test_score_benchmark.py
    ├── test_soft_validation_for_llm.py
    ├── test_soft_violation.py
    └── test_validator_prolog.py
```

## Notas

- A validação em Prolog é responsável por garantir regras rígidas (ex.: limites de tempo, restrições de lesão, equipamento).
- O orquestrador repete tentativas de geração até obter um plano válido.
- O plano final devolve também histórico de violações e score.
