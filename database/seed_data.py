"""
Initializes and populates the SQLite database (students.db)
with 2 default relational tables:
1. students: id, name, course, department
2. courses: id, course, credits, marks, grade
"""

import os
import sqlite3

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "students.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")

SAMPLE_STUDENTS = [
    ("Aarav Sharma", "Computer Networks", "Computer Science"),
    ("Priya Patel", "Artificial Intelligence", "Computer Science"),
    ("Rohan Verma", "Database Systems", "Computer Science"),
    ("Aditya Nair", "Data Science", "Data Science"),
    ("Rahul Gupta", "Thermodynamics", "Mechanical"),
    ("Vikram Rathod", "Fluid Mechanics", "Mechanical"),
    ("Vikram Singh", "Manufacturing Processes", "Mechanical"),
    ("Ishaan Mehta", "Electrical Engineering", "Electrical"),
    ("Devansh Saxena", "Civil Engineering", "Civil"),
    ("Sanya Kapoor", "Deep Learning", "AI & ML")
]

SAMPLE_COURSES = [
    ("Computer Networks", 4, 94.5, 9.5, 16000, "Dr. Ramesh Rao"),
    ("Artificial Intelligence", 4, 88.0, 8.8, 20000, "Dr. Sunita Menon"),
    ("Database Systems", 3, 76.5, 7.7, 12000, "Prof. Amit Sharma"),
    ("Data Science", 4, 95.0, 9.5, 18000, "Dr. Meera Reddy"),
    ("Thermodynamics", 4, 82.5, 8.3, 13000, "Dr. Rajesh Gupta"),
    ("Fluid Mechanics", 3, 85.0, 8.5, 11000, "Prof. K. V. Raman"),
    ("Manufacturing Processes", 3, 68.0, 6.8, 9000, "Dr. Anil Deshmukh"),
    ("Electrical Engineering", 4, 91.0, 9.1, 15000, "Prof. S. K. Joshi"),
    ("Civil Engineering", 3, 65.5, 6.6, 8000, "Dr. Harish Verma"),
    ("Deep Learning", 4, 97.0, 9.7, 22000, "Dr. Pooja Nair")
]

SAMPLE_EMPLOYEES = [
    ("Rajesh Kumar", "Engineering", "Lead Architect", 125000),
    ("Arun Roy", "Engineering", "Senior Developer", 95000),
    ("Sneha Sen", "Product", "Product Manager", 110000),
    ("Pooja Nair", "HR", "HR Specialist", 65000),
    ("Kiran Joshi", "Finance", "Financial Analyst", 82000),
    ("Amit Patel", "Operations", "Operations Associate", 42000),
    ("Neha Shah", "Operations", "Support Specialist", 38000),
    ("Ritu Sharma", "Marketing", "Intern", 28000),
    ("Vicky Verma", "Marketing", "Coordinator", 45000)
]

def init_database(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    """Initializes and seeds the database with the default relational tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    insert_query_students = """
    INSERT INTO students (name, course, department)
    VALUES (?, ?, ?)
    """
    cursor.executemany(insert_query_students, SAMPLE_STUDENTS)

    insert_query_courses = """
    INSERT INTO courses (course, credits, marks, cgpa, fee, instructor)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(insert_query_courses, SAMPLE_COURSES)

    insert_query_employees = """
    INSERT INTO employees (name, department, role, salary)
    VALUES (?, ?, ?, ?)
    """
    cursor.executemany(insert_query_employees, SAMPLE_EMPLOYEES)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM courses")
    total_courses = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]
    conn.close()

    print(f"Database initialized successfully at: {db_path}")
    print(f"Inserted {total_students} records into 'students'.")
    print(f"Inserted {total_courses} records into 'courses'.")
    print(f"Inserted {total_employees} records into 'employees'.")
    return db_path

if __name__ == "__main__":
    init_database()
