import requests
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3.2:1b"  # faster for local


def call_local_llm(prompt: str) -> Optional[str]:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": LOCAL_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()
        data = response.json()

        answer = data.get("response")

        if not answer:
            print("Local: Empty response.")
            return None

        return answer.strip()

    except requests.exceptions.RequestException as e:
        print("Local LLM failed:", e)
        return None