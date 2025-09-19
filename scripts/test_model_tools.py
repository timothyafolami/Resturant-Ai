#!/usr/bin/env python3
"""
Minimal tool-call capability test for the current LLM.

It binds a trivial tool and asks the model to use it. We then inspect
the returned AIMessage for tool_calls. If empty, the model likely does
not support tool-calling (or chooses not to, despite strong instruction).
"""

import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from typing import Any, Dict

# Use the same LLM instance as the app
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.llm import llm


@tool
def add_numbers(a: int, b: int) -> str:
    """Add two integers and return the sum as a string."""
    return str(int(a) + int(b))


@tool
def echo_text(text: str) -> str:
    """Echo the provided text back verbatim."""
    return text


def run_probe(prompt: str):
    bound = llm.bind_tools([add_numbers, echo_text])
    msgs = [
        SystemMessage(
            content=(
                "You have access to two tools: add_numbers and echo_text.\n"
                "When asked to compute a sum or echo text, you MUST call the appropriate tool.\n"
                "Return the final answer only after using the tool."
            )
        ),
        HumanMessage(content=prompt),
    ]
    ai = bound.invoke(msgs)
    return ai


def main() -> None:
    load_dotenv()

    tests = [
        "Please use add_numbers to add 2 and 3.",
        "Echo back the phrase 'hello tools' using echo_text.",
    ]

    print("=== Tool-call capability probe ===")
    for i, t in enumerate(tests, 1):
        print(f"\nTest {i}: {t}")
        ai = run_probe(t)
        # LangChain AIMessage may include tool_calls attribute when model calls tools
        tool_calls = getattr(ai, "tool_calls", [])
        print("AI content:", repr(ai.content))
        print("Tool calls detected:", tool_calls)
        if tool_calls:
            print("✅ Model attempted tool calls.")
        else:
            print("❌ No tool calls emitted by model.")


if __name__ == "__main__":
    main()
