
import math


def estimate_input_tokens(prompt: str) -> int:
    """
    Estimate prompt tokens using a simple character-based heuristic.

    This is an approximation, not an exact tokenizer count.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    return max(1, math.ceil(len(prompt) / 4))


def calculate_token_budget(prompt: str, max_tokens: int) -> int:
    """
    Calculate the total token reservation:
    estimated input tokens + maximum output tokens.
    """
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")

    input_tokens = estimate_input_tokens(prompt)
    return input_tokens + max_tokens


if __name__ == "__main__":
    prompt = "Hello AI Gateway"
    max_tokens = 100

    input_tokens = estimate_input_tokens(prompt)
    total_budget = calculate_token_budget(prompt, max_tokens)

    print("Estimated input tokens:", input_tokens)
    print("Reserved output tokens:", max_tokens)
    print("Total token budget:", total_budget)
