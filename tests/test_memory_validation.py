from agent.core import run_pipeline
from agent.memory import SlidingWindowMemory

memory = SlidingWindowMemory(max_turns=6)

turns = [
    "What is our revenue vs target by region?",
    "Which region is furthest from target?",
    "Drill into the North region by product",
    "Is this consistent with last quarter?",
]

for i, q in enumerate(turns, 1):
    print(f"\nTurn {i}: {q}")
    result = run_pipeline(q, memory=memory)
    print(f"SQL: {result['sql']}")
    print(f"Rows: {len(result['data']) if result['data'] is not None else 0}")
    print(f"Memory ({len(memory)} msgs): {[m['content'][:60] for m in memory.get()]}")