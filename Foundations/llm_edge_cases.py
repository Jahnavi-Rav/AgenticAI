import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def call_llm(prompt, max_retries=3, timeout=30):
    """
    Handles:
    - Rate limits / temporary failures with retry
    - Truncation checks
    - Hallucination warning pattern
    """

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 80  # output token limit; small value can cause truncation
        }
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=timeout
            )

            # Simulated / real rate-limit handling
            if response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"Rate limited. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            answer = data.get("response", "")
            done = data.get("done", False)

            print("\n--- LLM ANSWER ---")
            print(answer)

            print("\n--- INSPECTION ---")
            print("Done:", done)
            print("Model:", data.get("model"))
            print("Total duration:", data.get("total_duration"))

            check_truncation(answer, done)
            check_hallucination_risk(prompt, answer)

            return answer

        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt}. Retrying...")
            time.sleep(2 ** attempt)

        except requests.exceptions.ConnectionError:
            print("Connection error. Is Ollama running?")
            print("Run: ollama serve")
            return None

        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
            return None

    print("Failed after maximum retries.")
    return None


def check_truncation(answer, done):
    """
    Detects possible truncation.
    """

    suspicious_endings = (
        ",",
        ":",
        ";",
        "and",
        "or",
        "because",
        "such as"
    )

    if not done:
        print("Warning: Response may be incomplete.")

    if answer.strip().endswith(suspicious_endings):
        print("Warning: Answer may be truncated.")

    if len(answer.split()) < 5:
        print("Warning: Very short answer. Possible failure or truncation.")


def check_hallucination_risk(prompt, answer):
    """
    Basic hallucination risk detector.
    This does NOT prove hallucination.
    It only flags risky answers.
    """

    risky_phrases = [
        "according to a study",
        "research shows",
        "experts say",
        "in 2024",
        "in 2025",
        "statistics show",
        "it is proven",
        "definitely",
        "guaranteed"
    ]

    found = []

    for phrase in risky_phrases:
        if phrase.lower() in answer.lower():
            found.append(phrase)

    if found:
        print("Warning: Possible hallucination risk.")
        print("Reason: Answer contains unsupported claim phrases:", found)
        print("Suggestion: Verify with a trusted source.")


if __name__ == "__main__":
    prompt = """
    Explain hallucinations, truncation, and rate limits in LLM APIs.
    Give examples.
    """

    call_llm(prompt)