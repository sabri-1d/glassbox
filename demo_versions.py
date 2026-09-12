"""Simulate the same function under two prompt versions."""

import time
import random

from tracer import track


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class FakeResponse:
    def __init__(self, model, input_tokens, output_tokens):
        self.model = model
        self.usage = FakeUsage(input_tokens, output_tokens)


def _make_versioned_call(low_tokens, high_tokens, version_tag):
    def call_claude(prompt):
        time.sleep(random.uniform(0.2, 0.9))
        return FakeResponse("claude-sonnet-5", random.randint(low_tokens, high_tokens), random.randint(150, 300))
    return track(version=version_tag)(call_claude)


call_claude_v1 = _make_versioned_call(900, 1300, "v1-verbose-system-prompt")
call_claude_v2 = _make_versioned_call(300, 500, "v2-concise-system-prompt")


if __name__ == "__main__":
    print("Simulating 15 calls on the old, verbose prompt (v1)...")
    for _ in range(15):
        call_claude_v1("What's the weather like today?")
    print("Simulating 15 calls on the new, trimmed-down prompt (v2)...")
    for _ in range(15):
        call_claude_v2("What's the weather like today?")
    print("\nDone. Now run:\n    python diff.py --function call_claude")
