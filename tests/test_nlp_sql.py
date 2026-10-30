"""
Unit Test Suite for NLP for Database Interaction Project.
Validates each branch of the flowchart:
1. Empty input validation
2. Intent classification (6 intents + NO_MATCH)
3. Parameter extraction
4. SQL generation correctness
5. Read-only query security validator
6. Database query execution
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nlp_engine import parse_query
from nlp_engine.intent_classifier import Intent
from executor.query_executor import is_safe_read_only_query, execute_query

class TestNLPSQLPipeline(unittest.TestCase):

    def test_empty_input(self):
        """Flowchart: Is the input empty? -> Yes -> Ask user to enter a question"""
        res_empty = parse_query("")
        self.assertEqual(res_empty["status"], "empty")

        res_spaces = parse_query("   ")
        self.assertEqual(res_spaces["status"], "empty")

    def test_list_students_intent(self):
        """Flowchart: List students -> Select all student records (all details)"""
        res = parse_query("show all students")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.LIST_STUDENTS)
        self.assertIn("SELECT", res["sql"])
        self.assertIn("FROM students", res["sql"])

    def test_list_student_names_only(self):
        """Display the names of all students -> Selects only the name column"""
        res = parse_query("Display the names of all students.")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.LIST_STUDENTS)
        self.assertIn("SELECT name", res["sql"])
        self.assertIn("FROM students", res["sql"])
        exec_res = execute_query(res["sql"], res["params"])
        self.assertEqual(exec_res["columns"], ["name"])
        self.assertEqual(exec_res["row_count"], 10)

    def test_list_student_names_and_cgpa(self):
        """Show the names and cgpa of students -> Selects name and cgpa columns"""
        res = parse_query("Show the names and cgpa of students.")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.LIST_STUDENTS)
        self.assertIn("name", res["sql"])
        self.assertIn("cgpa", res["sql"])
        exec_res = execute_query(res["sql"], res["params"])
        self.assertEqual(exec_res["columns"], ["name", "cgpa"])
        self.assertEqual(exec_res["row_count"], 10)

    def test_marks_filter_greater(self):
        """Flowchart: Marks filter -> Extract threshold and comparison (>)"""
        res = parse_query("students with marks greater than 80")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.MARKS_FILTER)
        self.assertEqual(res["entities"]["operator"], ">")
        self.assertEqual(res["entities"]["threshold"], 80.0)
        self.assertIn("marks > ?", res["sql"])
        self.assertEqual(res["params"], (80.0,))

    def test_marks_filter_less_than(self):
        """Flowchart: Marks filter -> Extract threshold and comparison (<)"""
        res = parse_query("students with marks below 70")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.MARKS_FILTER)
        self.assertEqual(res["entities"]["operator"], "<")
        self.assertEqual(res["entities"]["threshold"], 70.0)

    def test_top_n_intent(self):
        """Flowchart: Top N -> Extract N and sort by marks"""
        res = parse_query("who are the top 3 students")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.TOP_N)
        self.assertEqual(res["entities"]["n"], 3)
        self.assertTrue("ORDER BY courses.marks DESC" in res["sql"] or "ORDER BY marks DESC" in res["sql"])
        self.assertIn("LIMIT ?", res["sql"])
        self.assertEqual(res["params"], (3,))

    def test_top_student_single(self):
        """Flowchart: Top N -> Topper defaults to N=1"""
        res = parse_query("who is the topper")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.TOP_N)
        self.assertEqual(res["entities"]["n"], 1)

    def test_department_intent(self):
        """Flowchart: Department -> Extract department name"""
        res = parse_query("students in Computer Science")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.DEPARTMENT)
        self.assertEqual(res["entities"]["department"], "Computer Science")
        self.assertIn("LOWER(department) = LOWER(?)", res["sql"])
        self.assertEqual(res["params"], ("Computer Science",))

    def test_aggregate_average(self):
        """Flowchart: Average or count -> Select aggregate SQL query (AVG)"""
        res = parse_query("what is the average marks of students")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.AVERAGE_OR_COUNT)
        self.assertEqual(res["entities"]["aggregate"], "AVG")
        self.assertIn("AVG(marks)", res["sql"])

    def test_aggregate_count_dept(self):
        """Flowchart: Average or count -> Select aggregate SQL query (COUNT with Dept)"""
        res = parse_query("how many students in Mechanical")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.AVERAGE_OR_COUNT)
        self.assertEqual(res["entities"]["aggregate"], "COUNT")
        self.assertEqual(res["entities"]["department"], "Mechanical")
        self.assertIn("COUNT(*)", res["sql"])

    def test_name_search_intent(self):
        """Flowchart: Name search -> Extract student name"""
        res = parse_query("find student named Priya")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.NAME_SEARCH)
        self.assertIn("priya", res["entities"]["name"].lower())
        self.assertIn("LOWER(name) LIKE LOWER(?)", res["sql"])

    def test_specific_attribute_query(self):
        """Specific attribute question -> Returns only that attribute (e.g. ID of Aditya Nair)"""
        res = parse_query("give id of student Aditya Nair")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["intent"], Intent.NAME_SEARCH)
        self.assertIn("SELECT id", res["sql"])
        self.assertIn("FROM students", res["sql"])
        exec_res = execute_query(res["sql"], res["params"])
        self.assertEqual(exec_res["columns"], ["id"])
        self.assertEqual(exec_res["rows"], [(4,)])

    def test_no_match_unsupported(self):
        """Flowchart: No match -> Display unsupported question message"""
        res = parse_query("what is the capital of France")
        self.assertEqual(res["status"], "unsupported")
        self.assertEqual(res["intent"], Intent.NO_MATCH)

    def test_security_read_only_validator(self):
        """Flowchart: Read-only SQL enforcement"""
        is_safe, _ = is_safe_read_only_query("SELECT * FROM students")
        self.assertTrue(is_safe)

        is_safe, _ = is_safe_read_only_query("DROP TABLE students")
        self.assertFalse(is_safe)

        is_safe, _ = is_safe_read_only_query("DELETE FROM students WHERE id = 1")
        self.assertFalse(is_safe)

        is_safe, _ = is_safe_read_only_query("SELECT * FROM students; DROP TABLE students")
        self.assertFalse(is_safe)

    def test_query_execution_success(self):
        """Flowchart: Query successful? -> Yes -> Display generated SQL and results"""
        res = parse_query("show all students")
        exec_res = execute_query(res["sql"], res["params"])
        self.assertTrue(exec_res["success"])
        self.assertGreater(exec_res["row_count"], 0)
        self.assertIn("name", exec_res["columns"])

if __name__ == "__main__":
    unittest.main()
