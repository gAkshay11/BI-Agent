import sqlite3
import hashlib

_schema_cache = {"hash": None, "schema": None}

def _db_hash(db_path: str) -> str:
    with open(db_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def get_schema(db_path: str) -> str:
    current_hash = _db_hash(db_path)
    if _schema_cache["hash"] == current_hash:
        return _schema_cache["schema"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    schema_parts = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        col_defs = [f"  {col[1]} ({col[2]})" for col in columns]
        schema_parts.append(f"Table: {table}\n" + "\n".join(col_defs))

    conn.close()
    schema = "\n\n".join(schema_parts)
    _schema_cache["hash"] = current_hash
    _schema_cache["schema"] = schema
    return schema