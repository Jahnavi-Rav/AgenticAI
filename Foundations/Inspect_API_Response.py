import requests

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": "Explain attention in one sentence",
            "stream": False
        }
    )

    data = response.json()

    print("Answer:", data.get("response", "No response"))
    print("Done:", data.get("done"))

except Exception as e:
    print("Error:", e)