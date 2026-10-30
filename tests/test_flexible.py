"""
Test flexible natural language phrasing.
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nlp_engine import parse_query
from executor import execute_query

tests = [
    ("give me all student records", "LIST_STUDENTS"),
    ("who scored more than 80 marks", "MARKS_FILTER"),
    ("best 3 students", "TOP_N"),
    ("who is in CSE", "DEPARTMENT"),
    ("what is the mean marks", "AVERAGE_OR_COUNT"),
    ("how many students are in mechanical", "AVERAGE_OR_COUNT"),
    ("tell me about Vikram Rathod", "NAME_SEARCH"),
    ("top 3 students in computer science", "TOP_N"),
    ("who is Priya", "NAME_SEARCH"),
    ("students with marks below 70", "MARKS_FILTER"),
    ("show all students", "LIST_STUDENTS"),
    ("students with marks greater than 85", "MARKS_FILTER"),
    ("top 3 students", "TOP_N"),
    ("students in Computer Science department", "DEPARTMENT"),
    ("what is the average marks of students", "AVERAGE_OR_COUNT"),
    ("Display the names of all students.", "LIST_STUDENTS"),
    ("Show the names and cgpa of students.", "LIST_STUDENTS"),
    ("give id of student Aditya Nair", "NAME_SEARCH"),
    ("Find students with CGPA greater than 8.", "MARKS_FILTER"),
    ("Show students who scored between 70 and 90 marks.", "MARKS_FILTER"),
    ("Find students from the CSE branch.", "DEPARTMENT"),
    ("List students whose names start with A.", "NAME_SEARCH"),
    ("Find students whose CGPA is not less than 7.", "MARKS_FILTER"),
    ("Find students whose CGPA is not greater than 7", "MARKS_FILTER"),
    ("Arrange students by CGPA in descending order.", "LIST_STUDENTS"),
    ("Show the five students with the highest marks.", "TOP_N"),
    ("Display the three cheapest courses.", "TOP_N"),
    ("Sort students alphabetically by name.", "LIST_STUDENTS"),
    ("Count the total number of students.", "AVERAGE_OR_COUNT"),
    ("Find the average CGPA of all students.", "AVERAGE_OR_COUNT"),
    ("What is the highest mark obtained?", "AVERAGE_OR_COUNT"),
    ("Find the minimum and maximum course fees.", "AVERAGE_OR_COUNT"),
    ("Calculate the total number of courses.", "AVERAGE_OR_COUNT"),
    ("join both students and courses", "LIST_STUDENTS"),
    ("Count the students in each branch.", "AVERAGE_OR_COUNT"),
    ("Find the average CGPA for each department.", "AVERAGE_OR_COUNT"),
    ("Show branches with more than 10 students.", "AVERAGE_OR_COUNT"),
    ("Find departments whose average salary exceeds ₹50,000.", "AVERAGE_OR_COUNT"),
    # New Relational & Association Test Queries (Image 1)
    ("Show each student's name and enrolled courses.", "LIST_STUDENTS"),
    ("List course names with their instructors.", "LIST_STUDENTS"),
    ("Find students enrolled in more than one course.", "AVERAGE_OR_COUNT"),
    ("Show each department with its employees.", "LIST_STUDENTS"),
    ("Find students who have not enrolled in any course.", "LIST_STUDENTS"),
    # Advanced Subquery Test Queries (Image 2)
    ("Find students scoring above the average marks.", "MARKS_FILTER"),
    ("Find the student with the second-highest CGPA.", "TOP_N"),
    ("Find courses with more enrollments than the average course enrollment.", "AVERAGE_OR_COUNT"),
    ("Find employees earning more than their department's average salary.", "AVERAGE_OR_COUNT"),
    ("Find students enrolled in all available courses.", "AVERAGE_OR_COUNT")
]

all_passed = True
for q, expected_intent in tests:
    res = parse_query(q)
    intent = res["intent"]
    passed = (intent == expected_intent)
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_passed = False
    print(f"[{status}] Query: '{q}' -> Intent: {intent} (Expected: {expected_intent})")
    if res["sql"]:
        exec_res = execute_query(res["sql"], res["params"])
        print(f"       SQL: {res['sql']} | Rows: {exec_res['row_count']}")

if all_passed:
    print("\nALL FLEXIBLE NATURAL LANGUAGE QUERIES PASSED PERFECTLY!")
else:
    print("\nSOME QUERIES FAILED!")
