# agent/tools.py
import re
import sqlite3
import pandas as pd

HARD_ROW_CAP = 500
DISALLOWED_PATTERNS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b',
    r'\bUPDATE\b', r'\bALTER\b', r'\bCREATE\b'
]


def is_safe_sql(query: str) -> bool:
    for pattern in DISALLOWED_PATTERNS:
        if re.search(pattern, query.upper()):
            return False
    return True


def clean_sql(query: str) -> str:
    query = query.strip()
    if query.startswith("```sql"):
        query = query[6:]
    elif query.startswith("```"):
        query = query[3:]
    if query.endswith("```"):
        query = query[:-3]
    return query.strip()


def run_sql_raw(query: str, db_path: str):
    query = clean_sql(query)

    if not is_safe_sql(query):
        raise ValueError("Destructive SQL blocked. Only SELECT queries permitted.")

    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(query, conn)
        if len(df) > HARD_ROW_CAP:
            df = df.head(HARD_ROW_CAP)
        return df, query
    except Exception as e:
        raise ValueError(f"SQL execution failed: {e}\nQuery: {query}")
    finally:
        conn.close()


def get_current_period_anchor(db_path: str, mode: str = "data") -> dict:
    """
    Resolves what "today" / "this quarter" / "this month" means for the agent.

    mode="data" (default): anchors to the most recent close_date actually
    present in the deals table. This is the right choice for a static/synthetic
    dataset — it guarantees "this quarter" always points at a quarter that has
    real data in it, instead of drifting into an empty future quarter as real
    calendar time passes.

    mode="system": anchors to the real system clock (datetime.now()). Use this
    if/when the agent is wired to a live, continuously-updated database where
    "now" should mean the actual current date, not the dataset's latest entry.

    Switching modes is a one-line change at the call site — no changes needed
    elsewhere in the pipeline, since both modes return the same dict shape.
    """
    if mode == "system":
        from datetime import date
        today = date.today()
        quarter_num = (today.month - 1) // 3 + 1
        return {
            "period": today.strftime("%Y-%m"),
            "quarter": f"{today.year}-Q{quarter_num}",
        }

    # mode == "data"
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(close_date), MAX(quarter) FROM deals")
        max_close_date, max_quarter = cursor.fetchone()
        period = max_close_date[:7] if max_close_date else None
        return {
            "period": period,
            "quarter": max_quarter,
        }
    finally:
        conn.close()


def detect_chart_type(df: pd.DataFrame) -> str | None:
    """
    Determines chart type using data shape only — no column name matching.
    Returns: 'line', 'bar', 'pie', 'grouped_bar', or None (table only).

    Decision rules (data shape first, column names never):
    - YYYY-MM in col1 values → line (time series)
    - YYYY-Qn in col1 values → bar (quarterly comparison)
    - <= 5 unique col1 values → pie (proportions)
    - 6-15 unique col1 values → bar (category comparison)
    - 2+ numeric columns → grouped_bar (multi-metric comparison)
    - anything else → None (table only)
    """
    if df.empty or len(df.columns) < 2 or len(df) < 2:
        return None

    col1_values = df.iloc[:, 0].astype(str)
    n_unique = df.iloc[:, 0].nunique()
    numeric_cols = df.select_dtypes(include='number').columns.tolist()

    # Time series — YYYY-MM period pattern
    if col1_values.str.match(r'^\d{4}-\d{2}$').any():
        return "line"

    # Quarterly — YYYY-Qn pattern
    if col1_values.str.match(r'^\d{4}-Q[1-4]$').any():
        return "bar"

    # Multiple numeric columns — grouped bar (must check BEFORE proportion)
    if len(numeric_cols) >= 2:
        return "grouped_bar"

    # Proportion — few unique categories
    if n_unique <= 5:
        return "pie"

    # Comparison — moderate unique categories
    if n_unique <= 15:
        return "bar"

    return None  # Too complex, show table only


def generate_chart(df: pd.DataFrame, question: str):
    """
    Builds a Plotly figure from a DataFrame using detected chart type.
    Returns a Plotly figure object or None if data is not suitable for
    visualization (empty DataFrame, single column, or too many unique values).

    Chart type is determined entirely by data shape — see detect_chart_type().
    No LLM call, no column name heuristics.
    """
    import plotly.express as px

    if df.empty or len(df.columns) < 2 or len(df) < 2:
        return None

    chart_type = detect_chart_type(df)
    if chart_type is None:
        return None

    col1 = df.columns[0]
    col2 = df.columns[1]
    numeric_cols = df.select_dtypes(include='number').columns.tolist()

    try:
        if chart_type == "line":
            df[col1] = df[col1].astype(str)
            return px.line(df, x=col1, y=col2, title=question, markers=True)
        elif chart_type == "pie":
            return px.pie(df, names=col1, values=col2, title=question)
        elif chart_type == "grouped_bar":
            # Exclude percentage/ratio columns from grouped bar — incompatible scale with monetary values
            plot_cols = [c for c in numeric_cols if not any(x in c.lower() for x in ['pct', 'rate', 'ratio', 'percent'])]
            if not plot_cols:
                plot_cols = numeric_cols  # fallback if all cols are percentages
            return px.bar(df, x=col1, y=plot_cols, title=question, barmode='group')
        else:  # bar
            return px.bar(df, x=col1, y=col2, title=question, color=col1)
    except Exception:
        return None