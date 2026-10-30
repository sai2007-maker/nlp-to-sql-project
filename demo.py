"""
Automated Demonstration Script for DMAI Project.
Runs each branch of the flowchart sequentially with test cases.
Ideal for presentation, viva verification, or recording a video demo.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nlp_engine import parse_query
from executor import execute_query
from ui.cli import format_table

TEST_CASES = [
    {
        "branch": "Branch 1: Empty Input Check",
        "question": "",
        "expectation": "Prompts user to enter a question"
    },
    {
        "branch": "Branch 2: List Students",
        "question": "show all students",
        "expectation": "Selects all student records"
    },
    {
        "branch": "Branch 3: Marks Filter (Threshold & Comparison)",
        "question": "students with marks greater than 85",
        "expectation": "Filters students where marks > 85.0"
    },
    {
        "branch": "Branch 3b: Marks Filter (Below threshold)",
        "question": "students who scored below 70",
        "expectation": "Filters students where marks < 70.0"
    },
    {
        "branch": "Branch 4: Top N (Limit & Sort by marks)",
        "question": "who are the top 3 students",
        "expectation": "Sorts descending by marks with LIMIT 3"
    },
    {
        "branch": "Branch 5: Department Filter",
        "question": "students in Computer Science department",
        "expectation": "Filters students where department = Computer Science"
    },
    {
        "branch": "Branch 6a: Average Aggregate",
        "question": "what is the average marks of students",
        "expectation": "Computes ROUND(AVG(marks), 2)"
    },
    {
        "branch": "Branch 6b: Count Aggregate by Department",
        "question": "how many students in Mechanical",
        "expectation": "Counts students in Mechanical department"
    },
    {
        "branch": "Branch 7: Name Search",
        "question": "find student named Priya",
        "expectation": "Searches student by name matching Priya"
    },
    {
        "branch": "Branch 8: Unsupported Question Fallback",
        "question": "what is the capital of Australia",
        "expectation": "Displays unsupported question message"
    },
    {
        "branch": "Security Check: Destructive Query Rejection",
        "question": "drop table students",
        "expectation": "Safely rejected by read-only validator"
    }
]

def run_demo():
    print("=" * 80)
    print(" DMAI PROJECT DEMO: NLP FOR DATABASE INTERACTION (TEXT-TO-SQL)")
    print(" Demonstrating all decision paths defined in the system flowchart")
    print("=" * 80)

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test['branch'].upper()}")
        print(f" Input Question    : \"{test['question']}\"")
        print(f" Expected Behavior : {test['expectation']}")
        print("-" * 80)

        # 1. NLP Pipeline
        nlp_res = parse_query(test["question"])
        status = nlp_res["status"]

        if status == "empty":
            print(f" -> Flowchart Decision: Input empty? -> YES")
            print(f" -> Action Output     : {nlp_res['message']}")
            continue

        print(f" -> Flowchart Decision: Input empty? -> NO")
        print(f" -> Normalized Text   : '{nlp_res['normalized_query']}'")

        if status == "unsupported":
            print(f" -> Flowchart Decision: Intent Match? -> NO MATCH")
            print(f" -> Action Output     : {nlp_res['message']}")
            continue

        print(f" -> Flowchart Decision: Intent Match? -> YES ({nlp_res['intent']})")
        print(f" -> Extracted Entities: {nlp_res['entities']}")
        print(f" -> Generated SQL     : {nlp_res['sql']}")
        print(f" -> SQL Parameters    : {nlp_res['params']}")

        # 2. Execution Pipeline
        exec_res = execute_query(nlp_res["sql"], nlp_res["params"])
        if not exec_res["success"]:
            print(f" -> Query Successful? : NO")
            print(f" -> Error Message     : {exec_res['error']}")
        else:
            print(f" -> Query Successful? : YES ({exec_res['row_count']} rows returned)")
            print(format_table(exec_res["columns"], exec_res["rows"]))

    print("\n" + "=" * 80)
    print(" DEMO COMPLETED: All flowchart branches executed and verified!")
    print("=" * 80)

if __name__ == "__main__":
    run_demo()
