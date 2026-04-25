import json
import requests
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def call_llm(prompt: str) -> Optional[str]:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError:
            print("Error: Invalid JSON from API.")
            return None

        answer = data.get("response")

        if not answer:
            print("Error: Missing response field.")
            return None

        return answer.strip()

    except requests.exceptions.ConnectionError:
        print("Error: Ollama is not running. Run: ollama serve")
        return None

    except requests.exceptions.Timeout:
        print("Error: API request timed out.")
        return None

    except requests.exceptions.RequestException as e:
        print("API failure:", e)
        return None


def is_bad_input(text: str) -> bool:
    return not text.strip() or len(text.strip()) < 3


def main() -> None:
    print("CLI Assistant started.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower().strip() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if is_bad_input(user_input):
            print("Please enter a clearer question.")
            continue

        answer = call_llm(user_input)

        if answer is None:
            print("Assistant failed safely.")
            continue

        print("\nAssistant:", answer)
        print()


if __name__ == "__main__":
    main()