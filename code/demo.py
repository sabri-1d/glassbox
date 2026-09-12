"""Run a simulated Glassbox workload without an API key."""

import random
import time

from tracer import track


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class FakeResponse:
    def __init__(self, model, input_tokens, output_tokens):
        self.model = model
        self.usage = FakeUsage(input_tokens, output_tokens)


@track()
def fake_llm_call(prompt):
    time.sleep(random.uniform(0.3, 1.8))
    if random.random() < 0.08:
        raise RuntimeError("simulated API error")
    return FakeResponse(
        random.choice(["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-5"]),
        len(prompt.split()) * 4,
        random.randint(50, 400),
    )


if __name__ == "__main__":
    prompts = [
        "Summarize the plot of Hamlet",
        "Write a haiku about databases",
        "Explain quicksort to a five year old",
        "Draft a polite decline email",
    ]
    print("Sending simulated calls. Run watch.py in another terminal to view them.")
    for call_number in range(30):
        try:
            fake_llm_call(random.choice(prompts))
            print(f"  call {call_number + 1}/30 sent")
        except RuntimeError:
            print(f"  call {call_number + 1}/30 failed (simulated)")
        time.sleep(0.6)