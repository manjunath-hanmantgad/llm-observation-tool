PRICING_PER_TOKEN = {
    "gpt-4o": {"input": 0.000005, "output": 0.000015},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "mock-observatory-model": {"input": 0.0, "output": 0.0},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = PRICING_PER_TOKEN.get(model, PRICING_PER_TOKEN["gpt-4o"])
    return (prompt_tokens * rate["input"]) + (completion_tokens * rate["output"])
