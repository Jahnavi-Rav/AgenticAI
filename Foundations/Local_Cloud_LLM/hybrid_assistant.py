from local_llm import call_local_llm
from cloud_llm import call_huggingface


def is_bad_input(text: str) -> bool:
    return not text.strip() or len(text.strip()) < 3


def ask_llm(prompt: str):
    print("\nTrying local model...")
    answer = call_local_llm(prompt)

    if answer:
        print("Used local model.")
        return answer

    print("Falling back to free cloud model...")
    answer = call_huggingface(prompt)

    if answer:
        print("Used cloud model.")
        return answer

    return None


def main():
    print("Hybrid CLI Assistant (Local + Free Cloud)")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower().strip() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if is_bad_input(user_input):
            print("Please enter a clearer question.")
            continue

        answer = ask_llm(user_input)

        if answer:
            print("\nAssistant:", answer, "\n")
        else:
            print("Both models failed.\n")


if __name__ == "__main__":
    main()