import json
from typing import Any, Dict, Optional


REQUIRED_SCHEMA = {
    "status": str,
    "answer": str,
    "confidence": float,
}


def mock_llm_response(case: str) -> str:
    responses = {
        "valid": '{"status": "done", "answer": "Task completed.", "confidence": 0.9}',

        "invalid_json": 'status: done, answer: Task completed, confidence: 0.9',

        "partial_json": '{"status": "done", "answer": "Task completed."',

        "schema_drift": '{"state": "done", "message": "Task completed.", "score": 0.9}',
    }

    return responses.get(case, responses["valid"])


def parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("Error: Invalid or partial JSON.")
        return None


def validate_schema(data: Dict[str, Any]) -> bool:
    for field, expected_type in REQUIRED_SCHEMA.items():
        if field not in data:
            print(f"Error: Missing field '{field}'.")
            return False

        if not isinstance(data[field], expected_type):
            print(f"Error: Field '{field}' has wrong type.")
            return False

    return True


def repair_prompt(original_prompt: str) -> str:
    return f"""
Return ONLY valid JSON matching this schema:

{{
  "status": "done | failed | needs_clarification",
  "answer": "string",
  "confidence": 0.0
}}

Original task:
{original_prompt}
"""


def get_valid_agent_response(user_prompt: str) -> Optional[Dict[str, Any]]:
    test_cases = ["invalid_json", "partial_json", "schema_drift", "valid"]

    for attempt, case in enumerate(test_cases, start=1):
        print(f"\nAttempt {attempt}: {case}")

        raw_output = mock_llm_response(case)
        print("Raw output:", raw_output)

        data = parse_json(raw_output)

        if data and validate_schema(data):
            return data

        fixed_prompt = repair_prompt(user_prompt)
        print("Retrying with stricter prompt:")
        print(fixed_prompt[:200], "...")

    return None


if __name__ == "__main__":
    result = get_valid_agent_response("Summarize this document.")

    if result:
        print("\nValidated response:")
        print(result)
    else:
        print("Failed to get valid structured output.")