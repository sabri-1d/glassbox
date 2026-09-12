"""Estimate LLM call costs from the editable pricing configuration."""

import json
from pathlib import Path

PRICING_PATH = Path(__file__).parent / "pricing.json"


def _load_pricing():
    with open(PRICING_PATH, encoding="utf-8") as pricing_file:
        return json.load(pricing_file)


def estimate_cost(model, input_tokens, output_tokens):
    """Return estimated USD cost, or None when token counts are unavailable."""
    if input_tokens is None or output_tokens is None:
        return None
    pricing = _load_pricing()
    rates = pricing.get(model, pricing["_default"])
    input_cost = (input_tokens / 1_000_000) * rates["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * rates["output_per_million"]
    return round(input_cost + output_cost, 6)