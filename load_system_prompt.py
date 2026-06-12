def load_system_prompt(file_path: str = "prompts/system_prompt.md") -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# Uso:
system_p = load_system_prompt()