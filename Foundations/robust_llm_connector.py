import time
import requests
from typing import Optional


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def normalize_output(text: str) -> str:
    return " ".join(text.strip().split())


def is_inconsistent_or_bad(answer: str) -> bool:
    if not answer:
        return True

    if len(answer.split()) < 3:
        return True

    bad_phrases = [
        "i don't know",
        "error",
        "undefined",
        "null",
    ]

    return any(phrase in answer.lower() for phrase in bad_phrases)


def call_llm(prompt: str, timeout: int = 60) -> Optional[str]:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2  # lower = more consistent output
                },
            },
            timeout=timeout,
        )

        response.raise_for_status()
        data = response.json()

        answer = data.get("response", "")
        answer = normalize_output(answer)

        if is_inconsistent_or_bad(answer):
            print("Bad or inconsistent output detected.")
            return None

        return answer

    except requests.exceptions.ConnectionError:
        print("Model downtime: Ollama is not running.")
        print("Run: ollama serve")
        return None

    except requests.exceptions.Timeout:
        print("Timeout: model took too long.")
        return None

    except requests.exceptions.RequestException as e:
        print("API failure:", e)
        return None


def ask_with_retries(prompt: str, retries: int = 3) -> Optional[str]:
    for attempt in range(1, retries + 1):
        print(f"Attempt {attempt}...")

        answer = call_llm(prompt)

        if answer:
            return answer

        time.sleep(2 ** attempt)

    return None


if __name__ == "__main__":
    prompt = "Explain local vs cloud LLMs in 3 short bullet points."

    result = ask_with_retries(prompt)

    if result:
        print("\nFinal Answer:\n")
        print(result)
    else:
        print("Failed: model unavailable, timed out, or returned bad output.")