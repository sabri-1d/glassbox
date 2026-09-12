"""
pricing.py
Cost estimation for LLM calls, based on an editable pricing.json config.

Pricing changes often — the numbers in pricing.json are a reasonable
starting point, but you should check the current rates at
https://www.anthropic.com/pricing and https://openai.com/api/pricing
and update the file yourself from time to time.
"""

import json
from pathlib import Path

PRICING_PATH = Path(__file__).parent / "pricing.json"


def _load_pricing():
    with open(PRICING_PATH) as f:
        return json.load(f)


def estimate_cost(model, input_tokens, output_tokens):
    """
    Returns an estimated USD cost for a call, or None if token counts
    weren't available (e.g. the response object didn't expose usage info).
    """
    if input_tokens is None or output_tokens is None:
        return None

    pricing = _load_pricing()
    rates = pricing.get(model, pricing["_default"])

    input_cost = (input_tokens / 1_000_000) * rates["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * rates["output_per_million"]
    return round(input_cost + output_cost, 6)
