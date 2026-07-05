import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tools import run_sql_raw, is_safe_sql, detect_chart_type, generate_chart
from agent.schema_inspector import get_schema
import pandas as pd

DB_PATH = "data/finance_sales.db"

# --- Schema Inspector ---

def test_schema_returns_all_tables():
    schema = get_schema(DB_PATH)
    for table in ["reps", "deals", "revenue", "expenses", "products"]:
        assert table in schema

def test_schema_cache_returns_same_result():
    schema1 = get_schema(DB_PATH)
    schema2 = get_schema(DB_PATH)
    assert schema1 == schema2

# --- run_sql_raw ---

def test_basic_count_query():
    df, sql = run_sql_raw("SELECT COUNT(*) as count FROM deals", DB_PATH)
    assert not df.empty
    assert df["count"].iloc[0] > 0

def test_join_query():
    df, sql = run_sql_raw("""
        SELECT r.name, COUNT(d.deal_id) as deals
        FROM reps r LEFT JOIN deals d ON r.rep_id = d.rep_id
        GROUP BY r.rep_id LIMIT 5
    """, DB_PATH)
    assert len(df) == 5

def test_row_cap_enforced():
    df, sql = run_sql_raw("SELECT * FROM deals", DB_PATH)
    assert len(df) <= 500

def test_empty_result_no_crash():
    df, sql = run_sql_raw("SELECT * FROM deals WHERE deal_value > 99999999", DB_PATH)
    assert df.empty

def test_quarter_field_exists_and_formatted():
    df, sql = run_sql_raw("SELECT DISTINCT quarter FROM deals LIMIT 10", DB_PATH)
    assert not df.empty
    assert df["quarter"].str.match(r'\d{4}-Q[1-4]').all()

def test_markdown_stripped_from_sql():
    df, sql = run_sql_raw("```sql\nSELECT COUNT(*) as count FROM deals\n```", DB_PATH)
    assert not df.empty

# --- is_safe_sql ---

def test_blocks_drop():
    assert is_safe_sql("DROP TABLE deals") is False

def test_blocks_delete():
    assert is_safe_sql("DELETE FROM deals") is False

def test_blocks_insert():
    assert is_safe_sql("INSERT INTO deals VALUES (1)") is False

def test_blocks_update():
    assert is_safe_sql("UPDATE deals SET stage = 'x'") is False

def test_allows_select():
    assert is_safe_sql("SELECT * FROM deals") is True

# --- detect_chart_type ---

def test_period_column_returns_line():
    df = pd.DataFrame({"period": ["2025-01", "2025-02", "2025-03"], "revenue": [100, 200, 300]})
    assert detect_chart_type(df) == "line"

def test_quarter_column_returns_bar():
    df = pd.DataFrame({"quarter": ["2025-Q1", "2025-Q2", "2025-Q3"], "revenue": [100, 200, 300]})
    assert detect_chart_type(df) == "bar"

def test_few_categories_returns_pie():
    df = pd.DataFrame({"stage": ["Won", "Lost", "Open"], "count": [10, 5, 3]})
    assert detect_chart_type(df) == "pie"

def test_many_categories_returns_bar():
    df = pd.DataFrame({"rep": [f"Rep {i}" for i in range(10)], "value": range(10)})
    assert detect_chart_type(df) == "bar"

def test_empty_df_returns_none():
    df = pd.DataFrame()
    assert detect_chart_type(df) is None

def test_single_row_returns_none():
    df = pd.DataFrame({"region": ["North"], "revenue": [100]})
    assert detect_chart_type(df) is None

# --- generate_chart ---

def test_generate_chart_returns_figure_or_none():
    df = pd.DataFrame({"period": ["2025-01", "2025-02"], "revenue": [100, 200]})
    fig = generate_chart(df, "Test chart")
    assert fig is not None

def test_generate_chart_empty_returns_none():
    df = pd.DataFrame()
    fig = generate_chart(df, "Empty")
    assert fig is None