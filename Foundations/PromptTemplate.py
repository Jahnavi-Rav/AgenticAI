def build_prompt(role: str, task: str, format_rules: str, user_input: str) -> str:
    return f"""
                Role:
                {role}

                Task:
                {task}

                Format:
                {format_rules}

                User input:
                {user_input}
                """
prompt = build_prompt(
    role="You are a Python tutor.",
    task="Explain the concept clearly for a beginner.",
    format_rules="Use short paragraphs and one code example.",
    user_input="What is async programming?"
)

print(prompt)