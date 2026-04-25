from typing import Dict, List

MAX_RETRIES = 3


def generate_answer(prompt: str, attempt: int) -> str:
    if attempt == 1:
        return "Agents are AI things."

    if attempt == 2:
        return "AI agents pursue goals, use tools, and learn from feedback."

    return (
        "AI agents are systems that pursue goals by observing information, "
        "reasoning about next steps, using tools when needed, and improving "
        "their actions based on feedback."
    )


def critic(answer: str) -> Dict[str, List[str]]:
    issues = []

    required_terms = ["goals", "tools", "feedback"]

    if len(answer.split()) < 10:
        issues.append("Answer is too short.")

    for term in required_terms:
        if term not in answer.lower():
            issues.append(f"Missing concept: {term}")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def evaluator(answer: str, critic_review: Dict[str, List[str]]) -> Dict[str, object]:
    """
    Final decision step.

    Handles:
    - false rejection: critic complains, but answer is acceptable
    - overcorrection: answer becomes too long or overcomplicated
    """

    word_count = len(answer.split())

    if word_count > 80:
        return {
            "approved": False,
            "reason": "Overcorrection detected: answer is too long.",
        }

    if critic_review["passed"]:
        return {
            "approved": True,
            "reason": "Answer passed critic.",
        }

    # False rejection protection:
    # If only issue is length, but answer has key concepts, allow it.
    issues = critic_review["issues"]
    has_core_concepts = all(
        term in answer.lower()
        for term in ["goals", "tools", "feedback"]
    )

    if has_core_concepts and len(issues) == 1 and "too short" in issues[0].lower():
        return {
            "approved": True,
            "reason": "Approved despite critic: likely false rejection.",
        }

    return {
        "approved": False,
        "reason": "Evaluator agrees answer needs correction.",
    }


def self_correct(prompt: str) -> str:
    last_answer = ""

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nAttempt {attempt}")

        answer = generate_answer(prompt, attempt)
        last_answer = answer

        print("Draft:", answer)

        review = critic(answer)

        print("Critic:", review)

        evaluation = evaluator(answer, review)

        print("Evaluator:", evaluation)

        if evaluation["approved"]:
            return answer

        print("Retrying...")

    return f"Failed to fully satisfy checks. Best answer:\n{last_answer}"


if __name__ == "__main__":
    final_answer = self_correct("Explain AI agents.")

    print("\nFinal answer:")
    print(final_answer)