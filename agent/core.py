import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from agent.schema_inspector import get_schema
from agent.tools import run_sql_raw, get_current_period_anchor, generate_chart
from agent.prompts import NL_TO_SQL_PROMPT, INSIGHT_PROMPT
from agent.memory import SlidingWindowMemory

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

DB_PATH = os.getenv("DB_PATH", "data/finance_sales.db")
MODEL_SQL = os.getenv("MODEL_SQL", "llama-3.3-70b-versatile")
MODEL_FALLBACK = os.getenv("MODEL_FALLBACK", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PERIOD_ANCHOR_MODE = "data"


def get_llm(model: str):
    return ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=0)


def extract_tokens(response) -> int:
    try:
        return response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
    except Exception:
        return 0


def format_chat_history(memory: SlidingWindowMemory) -> str:
    if memory is None or len(memory) == 0:
        return "None"
    lines = []
    messages = memory.get()
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def generate_sql(question: str, schema: str, current_period: str,
                 current_quarter: str, chat_history: str = "None",
                 error_context: str = "") -> tuple[str, int]:
    prompt = NL_TO_SQL_PROMPT.format(
        schema=schema,
        question=question,
        current_period=current_period,
        current_quarter=current_quarter,
        chat_history=chat_history,
    )
    if error_context:
        prompt += f"\n\nPREVIOUS ATTEMPT FAILED: {error_context}\nFix the SQL."
    try:
        response = get_llm(MODEL_SQL).invoke(prompt)
        return response.content.strip(), extract_tokens(response)
    except Exception:
        try:
            response = get_llm(MODEL_FALLBACK).invoke(prompt)
            return response.content.strip(), extract_tokens(response)
        except Exception as e:
            raise RuntimeError(f"Both primary and fallback models failed during SQL generation: {e}")


def generate_insight(question: str, data: str, chart_type: str = "none") -> tuple[str, int]:
    prompt = INSIGHT_PROMPT.format(question=question, data=data, chart_type=chart_type)
    try:
        response = get_llm(MODEL_SQL).invoke(prompt)
        return response.content.strip(), extract_tokens(response)
    except Exception:
        try:
            response = get_llm(MODEL_FALLBACK).invoke(prompt)
            return response.content.strip(), extract_tokens(response)
        except Exception as e:
            raise RuntimeError(f"Both primary and fallback models failed during insight generation: {e}")


def run_pipeline(question: str, memory: SlidingWindowMemory = None) -> dict:
    total_tokens = 0
    try:
        schema = get_schema(DB_PATH)

        anchor = get_current_period_anchor(DB_PATH, mode=PERIOD_ANCHOR_MODE)
        current_period = anchor["period"]
        current_quarter = anchor["quarter"]

        chat_history_str = format_chat_history(memory)

        sql = None
        df = None
        error_context = ""

        for attempt in range(3):
            sql, tokens = generate_sql(
                question, schema, current_period, current_quarter,
                chat_history=chat_history_str,
                error_context=error_context
            )
            total_tokens += tokens

            if sql.startswith("ERROR:"):
                if memory is not None:
                    memory.add("user", f"{question} [no data returned]")
                return {
                    "sql": None,
                    "data": None,
                    "chart": None,
                    "insight": f"This question cannot be answered with the available data. {sql}",
                    "error": True,
                    "tokens": total_tokens
                }

            try:
                df, sql_used = run_sql_raw(sql, DB_PATH)
                sql = sql_used
                break
            except Exception as e:
                error_context = str(e)
                if attempt == 2:
                    if memory is not None:
                        memory.add("user", f"{question} [SQL failed]")
                    return {
                        "sql": sql,
                        "data": None,
                        "chart": None,
                        "insight": f"SQL execution failed after 3 attempts: {e}",
                        "error": True,
                        "tokens": total_tokens
                    }

        chart = generate_chart(df, question)
        chart_type = type(chart).__name__ if chart is not None else "none"

        if chart is not None and len(df.select_dtypes(include='number').columns) == 2:
            num_cols = df.select_dtypes(include='number').columns.tolist()
            df = df.copy()
            df['gap'] = (df[num_cols[0]] - df[num_cols[1]]).round(2)

        data_str = df.to_string(index=False) if not df.empty else "No results returned."
        insight, tokens = generate_insight(question, data_str, chart_type)
        total_tokens += tokens

        if memory is not None:
            row_count = len(df)
            col_names = ", ".join(df.columns.tolist())
            summary = f"{question} [{row_count} rows: {col_names}]"
            memory.add("user", question)
            memory.add("assistant", summary)

        return {
            "sql": sql,
            "data": df,
            "chart": chart,
            "insight": insight,
            "error": False,
            "tokens": total_tokens
        }

    except Exception as e:
        error_msg = str(e)
        if "413" in error_msg or "rate_limit" in error_msg or "Request too large" in error_msg:
            user_msg = "The request was too large to process. Try asking a more specific question (e.g. add a filter, limit to a region or time period)."
        else:
            user_msg = "Something went wrong and the request could not be completed. Please try again or rephrase your question."

        if memory is not None:
            memory.add("user", f"{question} [pipeline error]")

        return {
            "sql": None,
            "data": None,
            "chart": None,
            "insight": user_msg,
            "error": True,
            "tokens": total_tokens
        }