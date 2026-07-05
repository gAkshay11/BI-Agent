import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.core import run_pipeline
from agent.memory import SlidingWindowMemory

# --- Integration tests ---
# These call run_pipeline() end-to-end against the real DB and real Groq API.
# They test the full path: NL -> SQL -> chart -> insight.
# Slow tests — only run when explicitly needed, not on every commit.

def test_revenue_by_region():
    memory = SlidingWindowMemory()
    result = run_pipeline("What is our revenue vs target by region?", memory)
    assert result["error"] is False
    assert result["data"] is not None
    assert not result["data"].empty
    assert result["sql"] is not None

def test_top_reps_by_deal_value():
    memory = SlidingWindowMemory()
    result = run_pipeline("Who are the top 5 reps by closed deal value?", memory)
    assert result["error"] is False
    assert result["data"] is not None
    assert len(result["data"]) <= 5

def test_unanswerable_question():
    memory = SlidingWindowMemory()
    result = run_pipeline("What is the weather in Dallas today?", memory)
    # Should not crash — either returns error=True with message, or returns empty result gracefully
    assert result is not None
    assert "error" in result