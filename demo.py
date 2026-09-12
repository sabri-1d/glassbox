"""
demo.py
See GlassBox working end-to-end without needing an API key yet.

Run this in one terminal:
    python demo.py

Then, in a second terminal, run this to watch the calls come in live:
    python watch.py
"""

import time
import random

from tracer import track


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class FakeResponse:
    """Mimics the shape of a real Anthropic API response closely enough
    for GlassBox's tracer to pull usage and model info out of it."""
    def __init__(self, model, input_tokens, output_tokens):
        self.model = model
        self.usage = FakeUsage(input_tokens, output_tokens)


@track()
def fake_llm_call(prompt):
    """Pretend to call an LLM. Swap this body for a real API call
    (see the commented example below) whenever you're ready."""
    time.sleep(random.uniform(0.3, 1.8))  # simulate network latency

    if random.random() < 0.08:
        raise RuntimeError("simulated API error")

    input_tokens = len(prompt.split()) * 4
    output_tokens = random.randint(50, 400)
    model = random.choice(["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-5"])
    return FakeResponse(model, input_tokens, output_tokens)


# ── Real Anthropic example — uncomment once you have an API key ──────────
#
# import os
# import anthropic
# from dotenv import load_dotenv
# load_dotenv()
# client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#
# @track()
# def call_claude(prompt):
#     return client.messages.create(
#         model="claude-sonnet-5",
#         max_tokens=500,
#         messages=[{"role": "user", "content": prompt}],
#     )


if __name__ == "__main__":
    prompts = [
        "Summarize the plot of Hamlet",
        "Write a haiku about databases",
        "Explain quicksort to a five year old",
        "Draft a polite decline email",
    ]

    print("Sending simulated calls — open another terminal and run `python watch.py` to see them live.\n")
    for i in range(30):
        prompt = random.choice(prompts)
        try:
            fake_llm_call(prompt)
            print(f"  call {i + 1}/30 sent")
        except RuntimeError:
            print(f"  call {i + 1}/30 failed (simulated)")
        time.sleep(0.6)
