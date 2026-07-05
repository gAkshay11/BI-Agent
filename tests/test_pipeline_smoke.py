"""
Smoke test — re-validates S2's 5 exit-criteria questions against the
regenerated dataset (9 quarters, 2024-Q3 to 2026-Q3) instead of the
original 4-month dataset they were tested against.

This does not test new logic. It re-runs the same pipeline, same
questions, against new data, to confirm nothing broke when the date
range changed.
"""

from agent.core import run_pipeline
from agent.memory import SlidingWindowMemory

questions = [
    "What is our revenue vs target by region?",
    "Who are the top 5 reps by closed deal value?",
    "Where are we over budget this quarter?",
    "Show the monthly revenue trend",
    "What is the win rate by sales team?",
]

memory = SlidingWindowMemory(max_turns=6)

for i, q in enumerate(questions, 1):
    print(f"\n{'='*60}")
    print(f"Q{i}: {q}")
    result = run_pipeline(q, memory=memory)
    if result["error"]:
        print(f"ERROR: {result['insight']}")
    else:
        print(f"SQL: {result['sql']}")
        print(f"Rows: {len(result['data'])}")
        print(f"Chart: {type(result['chart']).__name__ if result['chart'] else 'None'}")
        print(f"Insight: {result['insight']}")
    print(f"Memory size: {len(memory)} messages")