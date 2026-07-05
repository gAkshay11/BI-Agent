from agent.core import run_pipeline
from agent.memory import SlidingWindowMemory

memory = SlidingWindowMemory(max_turns=6)

turns = [
    "Drill into the North region by product",
    "What is the win rate by sales team?",
    "Where are we over budget this quarter?",
]

for i, q in enumerate(turns, 1):
    print(f"\nTurn {i}: {q}")
    result = run_pipeline(q, memory=memory)
    print(f"SQL: {result['sql']}")
    print(f"Rows: {len(result['data']) if result['data'] is not None else 0}")