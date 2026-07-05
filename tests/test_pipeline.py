# test_pipeline.py
from agent.core import run_pipeline

questions = [
    "What is our revenue vs target by region?",
    "Who are the top 5 reps by closed deal value?",
    "Where are we over budget this quarter?",
    "What is the win rate by sales team?",
    "Which product has the highest margin?"
]

for q in questions:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    result = run_pipeline(q)
    print(f"SQL: {result['sql']}")
    print(f"DATA:\n{result['data']}")
    print(f"INSIGHT: {result['insight']}")
    print(f"ERROR: {result['error']}")