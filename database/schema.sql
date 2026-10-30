-- DMAI Relational Database Schema: 3 Default Tables
DROP TABLE IF EXISTS student_courses;
DROP TABLE IF EXISTS professors;
DROP TABLE IF EXISTS details;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS courses;

-- Table 1: Students (id, name, course, department)
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    course TEXT,
    department TEXT NOT NULL
);

-- Table 2: Courses (course, credits, marks, cgpa, fee, instructor - NO id column)
CREATE TABLE courses (
    course TEXT PRIMARY KEY,
    credits INTEGER NOT NULL,
    marks REAL NOT NULL,
    cgpa REAL NOT NULL,
    fee INTEGER NOT NULL,
    instructor TEXT NOT NULL
);

-- Table 3: Employees (id, name, department, role, salary)
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    salary INTEGER NOT NULL
);

-- Indexes for search and query performance
CREATE INDEX idx_students_dept ON students(department);
CREATE INDEX idx_students_name ON students(name);
CREATE INDEX idx_students_course ON students(course);
CREATE INDEX idx_courses_course ON courses(course);
CREATE INDEX idx_courses_marks ON courses(marks);
CREATE INDEX idx_employees_dept ON employees(department);
CREATE INDEX idx_employees_salary ON employees(salary);
