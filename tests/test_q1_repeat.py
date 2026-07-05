"""
Isolated test — runs Q1 three times in a row to check whether the
'WHERE period = current_period' over-application seen in the last
smoke test run is consistent behavior or a one-time sampling fluke.

Q1 has no temporal qualifier in the question itself, so it should
query the full dataset, not restrict to current_period.
"""

from agent.core import run_pipeline

QUESTION = "What is our revenue vs target by region?"

def main():
    for i in range(1, 4):
        print(f"\n{'='*70}")
        print(f"  Run {i}")
        print(f"{'='*70}")

        result = run_pipeline(QUESTION)

        if result["error"]:
            print(f"  ❌ ERROR: {result['insight']}")
            continue

        print(f"  SQL:\n  {result['sql']}\n")
        df = result["data"]
        if df is not None and not df.empty:
            print(f"  Rows returned: {len(df)}")
            print(df.to_string(index=False))
        else:
            print("  ⚠️  No data returned")

    print(f"\n{'='*70}")
    print("  Check: does 'WHERE period =' or 'WHERE quarter =' appear in")
    print("  any of the 3 SQL statements above? Q1 has no time qualifier,")
    print("  so it should NOT be restricted to current_period/current_quarter.")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()