"""
Query Executor Module.
Implements flowchart steps:
- 'Execute read-only SQL with parameters'
- 'Query successful?' -> 'Display error message' OR 'Display generated SQL and results'
"""

import os
import re
import sqlite3

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "students.db"
)

# Destructive SQL statements strictly prohibited
FORBIDDEN_KEYWORDS = [
    "drop", "delete", "insert", "update", "alter",
    "truncate", "create", "replace", "pragma", "attach", "exec"
]

def is_safe_read_only_query(sql: str) -> (bool, str):
    """
    Validates that the SQL query is strictly read-only and safe to execute.
    """
    if not sql:
        return False, "SQL query cannot be empty."

    # Check for multiple statements separated by semicolon
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements are not permitted."

    clean_sql = statements[0].strip()

    # Must start with SELECT
    if not re.match(r"^select\b", clean_sql, re.IGNORECASE):
        return False, "Only read-only SELECT queries are allowed."

    # Check for forbidden mutation keywords
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, clean_sql, re.IGNORECASE):
            return False, f"Potentially destructive keyword '{keyword}' is blocked."

    return True, ""

def execute_query(sql: str, params: tuple = (), db_path: str = DEFAULT_DB_PATH):
    """
    Executes a read-only SQL query with parameters against the SQLite database.
    Returns:
        {
            "success": bool,
            "columns": list of str,
            "rows": list of tuples / list of dicts,
            "row_count": int,
            "sql": str,
            "params": tuple,
            "error": str or None
        }
    """
    # 1. Enforce read-only security
    is_safe, error_msg = is_safe_read_only_query(sql)
    if not is_safe:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": sql,
            "params": params,
            "error": f"Security Violation: {error_msg}"
        }

    # Check if database file exists
    if not os.path.exists(db_path):
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": sql,
            "params": params,
            "error": f"Database file not found at: {db_path}. Please run database/seed_data.py first."
        }

    # 2. Execute query
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        row_count = len(rows)

        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
            "sql": sql,
            "params": params,
            "error": None
        }
    except sqlite3.Error as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": sql,
            "params": params,
            "error": f"Database Execution Error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": sql,
            "params": params,
            "error": f"Unexpected Error: {str(e)}"
        }
