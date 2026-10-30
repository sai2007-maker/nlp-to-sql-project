"""
Interactive Command Line Interface for NLP-to-SQL System.
Follows the exact flowchart steps and presents formatted results.
"""

import sys
import os

# Add root directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nlp_engine import parse_query
from executor import execute_query

SAMPLE_QUERIES = [
    ("List students", "show all students"),
    ("Marks filter (Above)", "students with marks greater than 85"),
    ("Marks filter (Below)", "students with marks less than 70"),
    ("Top N", "who are the top 3 students"),
    ("Department filter", "students in Computer Science department"),
    ("Aggregate (Average)", "what is the average marks of students"),
    ("Aggregate (Count by Dept)", "how many students in Mechanical"),
    ("Name search", "find student named Aarav"),
    ("Unsupported question", "what is the weather today in New York")
]

def format_table(columns, rows):
    """Formats columns and rows into a clean ASCII table."""
    if not columns or not rows:
        return "(0 rows returned)"

    # Convert all cells to strings
    str_rows = [[str(cell) for cell in row] for row in rows]
    col_widths = [len(col) for col in columns]

    for row in str_rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(val))

    # Build border
    border = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header = "| " + " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns)) + " |"

    lines = [border, header, border]
    for row in str_rows:
        row_str = "| " + " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        lines.append(row_str)
    lines.append(border)

    return "\n".join(lines)

def run_pipeline(question: str):
    """Processes a single question through the complete flowchart pipeline."""
    print("\n" + "=" * 70)
    print(f" QUESTION: \"{question}\"")
    print("=" * 70)

    # 1. NLP Pipeline
    nlp_result = parse_query(question)
    status = nlp_result["status"]

    if status == "empty":
        print("[!] Flowchart Branch: Input is empty")
        print("    --> Action: Ask user to enter a question")
        print("    Response: Please enter a valid question.")
        return

    print(f"[*] Normalized Input : {nlp_result['normalized_query']}")

    if status == "unsupported":
        print("[X] Flowchart Branch: Intent = NO_MATCH")
        print("    --> Action: Display unsupported question message")
        print(f"    Response: {nlp_result['message']}")
        return

    # Supported intent
    intent = nlp_result["intent"]
    sql = nlp_result["sql"]
    params = nlp_result["params"]

    print(f"[+] Identified Intent: {intent}")
    print(f"[+] Entities Parsed  : {nlp_result['entities']}")
    print(f"[+] Selected Template: {nlp_result['description']}")
    
    print("\n" + "#" * 70)
    print(" >>> CORE DELIVERABLE: GENERATED SQL QUERY (NLP TO SQL CONVERSION)")
    print(f"     SQL: {sql}")
    if params:
        print(f"     Parameters: {params}")
    print("#" * 70)

    # 2. Execution Pipeline
    exec_result = execute_query(sql, params)

    if not exec_result["success"]:
        print("\n[-] Flowchart Branch: Query Failed")
        print("    --> Action: Display error message")
        print(f"    Error: {exec_result['error']}")
        return

    # Query successful
    print("\n[OK] Flowchart Branch: Query Successful")
    print(f"     --> Action: Display generated SQL and results ({exec_result['row_count']} rows)")
    print()
    print(format_table(exec_result["columns"], exec_result["rows"]))

def interactive_loop():
    """Starts the interactive CLI session."""
    print("*" * 70)
    print(" DMAI Project: NLP for Database Interaction (Text-to-SQL)")
    print(" Rule-based NLP & Regex Query System over SQLite Database")
    print("*" * 70)
    print("Commands:")
    print("  'samples'  : Show list of sample queries you can try")
    print("  'sample N' : Run sample query number N (1 to 9)")
    print("  'exit'     : Quit application")
    print("-" * 70)

    while True:
        try:
            user_input = input("\nEnter Question (or 'samples'/'exit') > ").strip()
            if not user_input:
                # Trigger flowchart empty input test
                run_pipeline("")
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Exiting NLP-to-SQL system. Goodbye!")
                break

            if user_input.lower() == "samples":
                print("\nAvailable Sample Queries:")
                for idx, (label, sample_q) in enumerate(SAMPLE_QUERIES, 1):
                    print(f"  {idx}. [{label}] -> \"{sample_q}\"")
                continue

            if user_input.lower().startswith("sample "):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    idx = int(parts[1]) - 1
                    if 0 <= idx < len(SAMPLE_QUERIES):
                        _, sample_q = SAMPLE_QUERIES[idx]
                        run_pipeline(sample_q)
                        continue

            run_pipeline(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

if __name__ == "__main__":
    interactive_loop()
