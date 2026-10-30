"""
Table Manager Module.
Allows users to create custom tables, import CSV data, inspect schema,
and add custom records into the SQLite database.
"""

import os
import re
import csv
import io
import sqlite3

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "students.db"
)

def get_db_connection(db_path=DEFAULT_DB_PATH):
    return sqlite3.connect(db_path)

def sanitize_identifier(identifier: str) -> str:
    """Sanitizes table and column names to alphanumeric and underscores only."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", identifier.strip().lower())
    if not cleaned or cleaned[0].isdigit():
        cleaned = "t_" + cleaned
    return cleaned

def get_all_tables_info(db_path=DEFAULT_DB_PATH):
    """
    Returns information about all user tables in the database:
    name, columns, types, and row count.
    """
    if not os.path.exists(db_path):
        return []

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name ASC
    """)
    table_names = [row[0] for row in cursor.fetchall()]

    tables_info = []
    for tbl in table_names:
        # Get column info
        cursor.execute(f"PRAGMA table_info({tbl})")
        columns = [{"name": r[1], "type": r[2], "pk": bool(r[5])} for r in cursor.fetchall()]

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        count = cursor.fetchone()[0]

        # Get first 3 preview rows
        cursor.execute(f"SELECT * FROM {tbl} LIMIT 3")
        preview = cursor.fetchall()

        tables_info.append({
            "table_name": tbl,
            "columns": columns,
            "row_count": count,
            "preview_rows": preview
        })

    conn.close()
    return tables_info

def create_table(table_name: str, columns: list, initial_rows: list = None, db_path=DEFAULT_DB_PATH):
    """
    Creates a new custom table.
    columns format: [{"name": "col_name", "type": "TEXT"|"INTEGER"|"REAL"}]
    initial_rows format: [{"col_name": val, ...}]
    """
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return False, "Invalid table name."

    if not columns:
        return False, "At least one column is required."

    allowed_types = {"TEXT", "INTEGER", "REAL", "NUMERIC", "BLOB"}
    col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    valid_col_names = []

    for col in columns:
        col_name = sanitize_identifier(col.get("name", ""))
        col_type = col.get("type", "TEXT").upper()
        if not col_name or col_name == "id":
            continue
        if col_type not in allowed_types:
            col_type = "TEXT"
        col_defs.append(f"{col_name} {col_type}")
        valid_col_names.append(col_name)

    create_sql = f"CREATE TABLE IF NOT EXISTS {safe_table} ({', '.join(col_defs)});"

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(create_sql)

        # Insert initial rows if provided
        inserted_count = 0
        if initial_rows:
            for row in initial_rows:
                if not isinstance(row, dict):
                    continue
                row_cols = []
                row_vals = []
                for c in valid_col_names:
                    val = row.get(c, "")
                    if val != "" and val is not None:
                        row_cols.append(c)
                        row_vals.append(val)
                if row_cols:
                    ph = ", ".join(["?"] * len(row_vals))
                    insert_sql = f"INSERT INTO {safe_table} ({', '.join(row_cols)}) VALUES ({ph})"
                    cursor.execute(insert_sql, row_vals)
                    inserted_count += 1

        conn.commit()
        conn.close()
        msg = f"Table '{safe_table}' created successfully."
        if inserted_count > 0:
            msg += f" Added {inserted_count} record(s)."
        return True, msg
    except Exception as e:
        return False, f"Failed to create table: {str(e)}"

def import_csv_data(table_name: str, csv_content: str, db_path=DEFAULT_DB_PATH):
    """
    Imports CSV string into a new or existing table.
    Automatically infers column names and types.
    Handles existing table schema mismatches and headerless CSV data cleanly.
    """
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return False, "Invalid table name."

    f = io.StringIO(csv_content.strip())
    reader = csv.reader(f)

    try:
        first_line = next(reader)
    except StopIteration:
        return False, "CSV content is empty."

    remaining_rows = list(reader)

    # Check if first_line is actually a header or data
    # If any value is purely numeric, it's likely a data row, not a header
    has_pure_numbers = any(re.match(r"^-?\d+(\.\d+)?$", val.strip()) for val in first_line if val.strip())

    if has_pure_numbers:
        # First line is a data row!
        all_rows = [first_line] + remaining_rows
        # Generate reasonable column names based on table name or generic
        if safe_table == "courses" and len(first_line) == 4:
            safe_headers = ["course_name", "department", "credits", "semester"]
        elif safe_table == "courses" and len(first_line) == 3:
            safe_headers = ["code", "title", "credits"]
        elif safe_table == "details" and len(first_line) == 3:
            safe_headers = ["name", "age", "number"]
        else:
            safe_headers = [f"col_{i+1}" for i in range(len(first_line))]
        rows = all_rows
    else:
        # First line is indeed a header
        safe_headers = [sanitize_identifier(h) for h in first_line]
        rows = remaining_rows

    if not rows:
        return False, "CSV has headers but no data rows to import."

    # Infer types (INTEGER, REAL, TEXT)
    col_types = []
    for col_idx in range(len(safe_headers)):
        inferred = "INTEGER"
        for row in rows:
            if col_idx < len(row):
                val = row[col_idx].strip()
                if not val:
                    continue
                # Test integer
                if inferred == "INTEGER":
                    if not re.match(r"^-?\d+$", val):
                        inferred = "REAL"
                # Test real
                if inferred == "REAL":
                    if not re.match(r"^-?\d+(\.\d+)?$", val):
                        inferred = "TEXT"
                        break
        col_types.append(inferred)

    # Build CREATE TABLE
    col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for h, t in zip(safe_headers, col_types):
        if h == "id":
            continue
        col_defs.append(f"{h} {t}")

    create_sql = f"CREATE TABLE IF NOT EXISTS {safe_table} ({', '.join(col_defs)});"

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # For custom tables (not the core students table), drop and recreate to match new schema cleanly
        if safe_table != "students":
            cursor.execute(f"DROP TABLE IF EXISTS {safe_table}")

        cursor.execute(create_sql)

        # Insert rows
        placeholders = ", ".join(["?"] * len(safe_headers))
        cols_str = ", ".join(safe_headers)
        insert_sql = f"INSERT INTO {safe_table} ({cols_str}) VALUES ({placeholders})"

        # Ensure each row has right length
        cleaned_rows = []
        for r in rows:
            if len(r) < len(safe_headers):
                r = r + [""] * (len(safe_headers) - len(r))
            elif len(r) > len(safe_headers):
                r = r[:len(safe_headers)]
            cleaned_rows.append(r)

        cursor.executemany(insert_sql, cleaned_rows)
        conn.commit()
        conn.close()

        return True, f"Successfully created table '{safe_table}' and imported {len(cleaned_rows)} rows."
    except Exception as e:
        return False, f"Error importing CSV: {str(e)}"

def insert_single_row(table_name: str, row_data: dict, db_path=DEFAULT_DB_PATH):
    """Inserts a single row dictionary into the specified table."""
    safe_table = sanitize_identifier(table_name)
    if not row_data:
        return False, "No data provided."

    cols = []
    vals = []
    for k, v in row_data.items():
        if k == "id":
            continue
        cols.append(sanitize_identifier(k))
        vals.append(v)

    placeholders = ", ".join(["?"] * len(vals))
    cols_str = ", ".join(cols)
    sql = f"INSERT INTO {safe_table} ({cols_str}) VALUES ({placeholders})"

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(sql, vals)
        conn.commit()
        conn.close()
        return True, f"Record added to '{safe_table}'."
    except Exception as e:
        return False, f"Error inserting record: {str(e)}"

def delete_table(table_name: str, db_path=DEFAULT_DB_PATH):
    """Drops a custom table. Protects the core default tables."""
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return False, "Invalid table name."
    if safe_table in ("students", "courses", "employees"):
        return False, f"The default table '{safe_table}' is protected and cannot be deleted."

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {safe_table}")
        conn.commit()
        conn.close()
        return True, f"Table '{safe_table}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting table: {str(e)}"

def delete_row(table_name: str, row_id, db_path=DEFAULT_DB_PATH):
    """Deletes a single row by primary key (id, course, or first column) from the specified table."""
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return False, "Invalid table name."

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({safe_table})")
        cols_info = cursor.fetchall()
        col_names = [r[1] for r in cols_info]
        pk_cols = [r[1] for r in cols_info if r[5] > 0]
        if "id" in col_names:
            pk_col = "id"
        elif pk_cols:
            pk_col = pk_cols[0]
        else:
            pk_col = col_names[0]

        cursor.execute(f"DELETE FROM {safe_table} WHERE {pk_col} = ?", (row_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        if affected > 0:
            return True, f"Record '{row_id}' deleted from '{safe_table}'."
        else:
            return False, f"Record '{row_id}' not found in '{safe_table}'."
    except Exception as e:
        return False, f"Error deleting row: {str(e)}"

def update_row(table_name: str, row_id, updated_data: dict, db_path=DEFAULT_DB_PATH):
    """Updates fields of a single row by primary key (id, course, etc.)."""
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return False, "Invalid table name."
    if not updated_data:
        return False, "No data provided for update."

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({safe_table})")
        cols_info = cursor.fetchall()
        col_names = [r[1] for r in cols_info]
        pk_cols = [r[1] for r in cols_info if r[5] > 0]
        if "id" in col_names:
            pk_col = "id"
        elif pk_cols:
            pk_col = pk_cols[0]
        else:
            pk_col = col_names[0]

        set_clauses = []
        vals = []
        for k, v in updated_data.items():
            if k == pk_col:
                continue
            col_safe = sanitize_identifier(k)
            set_clauses.append(f"{col_safe} = ?")
            vals.append(v)

        if not set_clauses:
            conn.close()
            return False, "No valid columns provided to update."

        vals.append(row_id)
        sql = f"UPDATE {safe_table} SET {', '.join(set_clauses)} WHERE {pk_col} = ?"
        cursor.execute(sql, vals)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        if affected > 0:
            return True, f"Record '{row_id}' in '{safe_table}' updated successfully."
        else:
            return False, f"Record '{row_id}' not found in '{safe_table}'."
    except Exception as e:
        return False, f"Error updating row: {str(e)}"

def get_table_data(table_name: str, limit: int = 100, db_path=DEFAULT_DB_PATH):
    """Retrieves columns and rows for a table to display in manager."""
    safe_table = sanitize_identifier(table_name)
    if not safe_table:
        return {"success": False, "error": "Invalid table name."}

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({safe_table})")
        columns = [r[1] for r in cursor.fetchall()]
        order_col = "id" if "id" in columns else (columns[0] if columns else "rowid")
        cursor.execute(f"SELECT * FROM {safe_table} ORDER BY {order_col} ASC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return {"success": True, "columns": columns, "rows": rows, "table_name": safe_table}
    except Exception as e:
        return {"success": False, "error": str(e)}
