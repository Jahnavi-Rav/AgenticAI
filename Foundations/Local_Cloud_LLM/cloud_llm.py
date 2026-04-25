import requests
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
HF_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

headers = {"Authorization": f"Bearer {HF_API_KEY}"}


def call_huggingface(prompt: str) -> Optional[str]:
    try:
        if not HF_API_KEY:
            print("Missing HF_API_KEY in .env")
            return None

        response = requests.post(
            HF_URL,
            headers=headers,
            json={"inputs": prompt},
            timeout=30,
        )

        if response.status_code == 429:
            print("Cloud: Rate limited.")
            return None

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()

        print("Cloud: Unexpected response format.")
        return None

    except Exception as e:
        print("Cloud LLM failed:", e)
        return None