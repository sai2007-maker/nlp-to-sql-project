"""
SQL Templates & Generation module.
Directly implements flowchart steps:
- 'Select predefined SQL template'
- Parameter binding for read-only parameterized execution.
- Supports 2 default relational tables (students, courses) linked by course.
"""

import re
from .intent_classifier import Intent
from .entity_extractor import (
    extract_marks_filter,
    extract_range_filter,
    extract_top_n,
    extract_rank_offset,
    extract_department,
    extract_student_name,
    extract_name_prefix,
    extract_sort_clause,
    extract_aggregate_type,
    extract_target_table,
    extract_requested_columns,
    extract_group_by,
    extract_having_clause
)

# Standard relational join projection: students + courses
STUDENT_JOIN_COURSES = (
    "students.id, students.name, students.course, students.department, "
    "courses.credits, courses.marks, courses.cgpa, courses.fee "
    "FROM students JOIN courses ON students.course = courses.course"
)

COLUMN_MAP = {
    "name": "students.name",
    "cgpa": "courses.cgpa",
    "grade": "courses.cgpa",
    "marks": "courses.marks",
    "course": "students.course",
    "credits": "courses.credits",
    "department": "students.department",
    "fee": "courses.fee",
    "fees": "courses.fee",
    "cost": "courses.fee",
    "price": "courses.fee",
    "instructor": "courses.instructor",
    "instructors": "courses.instructor",
    "professor": "courses.instructor",
    "professors": "courses.instructor",
    "salary": "employees.salary",
    "salaries": "employees.salary",
    "role": "employees.role",
    "id": "students.id"
}

def format_sql(sql: str) -> str:
    """
    Formats a single-line or unformatted SQL query into clean multi-line clauses:
    SELECT ...
    FROM ...
    JOIN ...
        ON ...
    WHERE ...
    GROUP BY ...
    HAVING ...
    ORDER BY ...
    LIMIT ...;
    """
    if not sql:
        return ""

    cleaned = " ".join(sql.strip().rstrip(";").split())

    clause_regex = re.compile(
        r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\b(?:INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|OUTER\s+JOIN|JOIN|FROM|ON|WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT)\b)",
        re.IGNORECASE
    )

    raw_tokens = clause_regex.split(cleaned)
    kw_set = {
        'FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'OUTER JOIN',
        'ON', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT'
    }

    lines = []
    first = raw_tokens[0].strip()
    if first:
        lines.append(first)

    i = 1
    while i < len(raw_tokens):
        tok = raw_tokens[i].strip()
        tok_upper = " ".join(tok.upper().split())
        if tok_upper in kw_set:
            kw = tok_upper
            clause_parts = []
            i += 1
            while i < len(raw_tokens):
                next_upper = " ".join(raw_tokens[i].strip().upper().split())
                if next_upper in kw_set:
                    break
                clause_parts.append(raw_tokens[i])
                i += 1
            body = " ".join("".join(clause_parts).split())
            if kw == "ON":
                lines.append(f"    ON {body}")
            else:
                lines.append(f"{kw} {body}")
        else:
            if lines:
                lines[-1] += " " + tok
            else:
                lines.append(tok)
            i += 1

    return "\n".join(lines).strip() + ";"

def _build_sql(intent: str, normalized_text: str):
    """
    Translates the classified intent and extracted entities into a parameterized SQL template.
    Supports default 'students' and 'courses' relational tables as well as user-created custom tables.
    Returns:
        (sql_template: str, parameters: tuple, description: str, entity_info: dict)
    """
    target_table = extract_target_table(normalized_text)

    if intent == Intent.LIST_STUDENTS:
        # Check for unenrolled students query
        is_not_enrolled = bool(re.search(
            r"\b(?:not\s+enrolled|unenrolled|no\s+courses?|without\s+(?:any\s+)?courses?|haven't\s+enrolled|have\s+not\s+enrolled)\b",
            normalized_text,
            re.IGNORECASE
        ))
        if is_not_enrolled:
            sql = (
                "SELECT students.id, students.name "
                "FROM students "
                "LEFT JOIN courses "
                "    ON students.course = courses.course "
                "WHERE courses.course IS NULL OR students.course IS NULL "
                "ORDER BY students.id ASC"
            )
            desc = "Find students who have not enrolled in any course"
            return sql, (), desc, {"intent": intent, "table": "students LEFT JOIN courses", "filter": "course IS NULL"}

        sort_col, sort_dir = extract_sort_clause(normalized_text)

        if target_table == "students":
            if sort_col == "cgpa":
                order_clause = f"ORDER BY courses.cgpa {sort_dir}"
            elif sort_col == "marks":
                order_clause = f"ORDER BY courses.marks {sort_dir}"
            elif sort_col == "name":
                order_clause = f"ORDER BY students.name {sort_dir}"
            elif sort_col == "department":
                order_clause = f"ORDER BY students.department {sort_dir}"
            elif sort_col == "course":
                order_clause = f"ORDER BY students.course {sort_dir}"
            elif sort_col == "credits":
                order_clause = f"ORDER BY courses.credits {sort_dir}"
            elif sort_col == "fee":
                order_clause = f"ORDER BY courses.fee {sort_dir}"
            elif sort_col == "id":
                order_clause = f"ORDER BY students.id {sort_dir}"
            else:
                order_clause = "ORDER BY students.id ASC"

            req_cols = extract_requested_columns(normalized_text)
            if req_cols:
                select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
                needs_courses = any(c in ("cgpa", "grade", "marks", "credits", "fee", "instructor") for c in req_cols) or sort_col in ("cgpa", "marks", "credits", "fee", "instructor")
                is_relational_courses = "course" in req_cols and ("name" in req_cols or "id" in req_cols or "department" in req_cols)
                if not needs_courses and not is_relational_courses:
                    simple_items = [c for c in req_cols if c in ("id", "name", "course", "department")]
                    simple_order = f"ORDER BY {sort_col} {sort_dir}" if sort_col in ("id", "name", "course", "department") else "ORDER BY id ASC"
                    sql = f"SELECT {', '.join(simple_items)} FROM students {simple_order}"
                else:
                    sql = f"SELECT {', '.join(select_items)} FROM students JOIN courses ON students.course = courses.course {order_clause}"
                desc = f"Display {', '.join(req_cols)} of students"
                return sql, (), desc, {"intent": intent, "table": "students JOIN courses" if (needs_courses or is_relational_courses) else target_table, "columns": req_cols, "sort": sort_col, "direction": sort_dir}
            else:
                is_join = bool(re.search(r"\b(?:join|joining|joined|combine|both)\b", normalized_text, re.IGNORECASE) or (re.search(r"\bstudents?\b", normalized_text, re.IGNORECASE) and re.search(r"\bcourses?\b", normalized_text, re.IGNORECASE)))
                sql = f"SELECT {STUDENT_JOIN_COURSES} {order_clause}"
                if is_join:
                    desc = "Join students and courses on course name"
                    table_name = "students JOIN courses"
                else:
                    desc = f"Select all student records {order_clause.lower()}"
                    table_name = target_table
                return sql, (), desc, {"intent": intent, "table": table_name, "columns": "all", "sort": sort_col, "direction": sort_dir}
        elif target_table == "courses":
            req_cols = extract_requested_columns(normalized_text)
            if req_cols:
                valid_course_cols = [c for c in req_cols if c in ("course", "credits", "marks", "cgpa", "fee", "instructor")]
                if not valid_course_cols:
                    valid_course_cols = ["course", "instructor"] if "instructor" in req_cols else ["course", "credits", "marks", "cgpa", "fee", "instructor"]
                order_clause = f"ORDER BY {sort_col} {sort_dir}" if sort_col in valid_course_cols else f"ORDER BY {valid_course_cols[0]} ASC"
                sql = f"SELECT {', '.join(valid_course_cols)} FROM courses {order_clause}"
                return sql, (), f"Display {', '.join(valid_course_cols)} from courses", {"intent": intent, "table": target_table, "columns": valid_course_cols}
            else:
                order_clause = f"ORDER BY {sort_col} {sort_dir}" if sort_col else "ORDER BY course ASC"
                sql = f"SELECT course, credits, marks, cgpa, fee, instructor FROM courses {order_clause}"
                return sql, (), "Select all courses records", {"intent": intent, "table": target_table, "sort": sort_col, "direction": sort_dir}
        elif target_table == "employees":
            req_cols = extract_requested_columns(normalized_text)
            is_dept_with_emp = bool(re.search(r"\bdepartments?\s+with\s+(?:its\s+|their\s+)?employees?\b", normalized_text, re.IGNORECASE) or ("department" in normalized_text.lower() and "employee" in normalized_text.lower()))
            if is_dept_with_emp or (req_cols and "department" in req_cols):
                sql = "SELECT department, name, role FROM employees ORDER BY department ASC, name ASC"
                desc = "Show each department with its employees"
                return sql, (), desc, {"intent": intent, "table": "employees", "columns": ["department", "name", "role"]}
            elif req_cols:
                emp_cols = [c for c in req_cols if c in ("id", "name", "department", "role", "salary")]
                if not emp_cols:
                    emp_cols = ["id", "name", "department", "role", "salary"]
                sql = f"SELECT {', '.join(emp_cols)} FROM employees ORDER BY id ASC"
                return sql, (), f"Display {', '.join(emp_cols)} from employees", {"intent": intent, "table": "employees", "columns": emp_cols}
            else:
                sql = "SELECT id, name, department, role, salary FROM employees ORDER BY department ASC, name ASC"
                return sql, (), "Select all employee records", {"intent": intent, "table": "employees", "columns": "all"}
        else:
            sql = f"SELECT * FROM {target_table} ORDER BY id ASC"
            return sql, (), f"Select all records from table '{target_table}'", {"intent": intent, "table": target_table}

    elif intent == Intent.MARKS_FILTER:
        # Check for scoring above/below average subquery
        is_above_avg = bool(re.search(r"\b(?:scoring|scored|with\s+marks?|marks?)\s+(?:above|greater\s+than|more\s+than|exceeding)\s+(?:the\s+)?average\s+marks?\b", normalized_text, re.I))
        if is_above_avg:
            sql = (
                f"SELECT {STUDENT_JOIN_COURSES} "
                "WHERE courses.marks > (SELECT AVG(marks) FROM courses) "
                "ORDER BY courses.marks DESC"
            )
            return sql, (), "Find students scoring above the average marks", {"intent": intent, "filter": "marks > AVG(marks)"}

        r_low, r_high = extract_range_filter(normalized_text)
        op, threshold = extract_marks_filter(normalized_text)

        is_cgpa = bool(re.search(r"\b(?:cgpa|gpa)\b", normalized_text, re.IGNORECASE))
        filter_col = "cgpa" if is_cgpa else "marks"
        filter_expr = "courses.cgpa" if is_cgpa else "marks"

        req_cols = extract_requested_columns(normalized_text)
        if req_cols:
            select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
            proj = ", ".join(select_items) + " FROM students JOIN courses ON students.course = courses.course"
        else:
            proj = STUDENT_JOIN_COURSES

        dept = extract_department(normalized_text)

        # Handle Range Filter: BETWEEN ? AND ?
        if r_low is not None and r_high is not None:
            if target_table == "courses":
                sql = f"SELECT course, credits, marks, cgpa FROM courses WHERE {filter_col} BETWEEN ? AND ? ORDER BY {filter_col} DESC"
                params = (r_low, r_high)
                desc = f"Filter courses with {filter_col.upper()} between {r_low} and {r_high}"
                return sql, params, desc, {"intent": intent, "table": target_table, "range": (r_low, r_high), "metric": filter_col}
            if dept:
                sql = f"SELECT {proj} WHERE LOWER(department) = LOWER(?) AND {filter_expr} BETWEEN ? AND ? ORDER BY {filter_expr} DESC"
                params = (dept, r_low, r_high)
                desc = f"Filter students in {dept} department with {filter_col.upper()} between {r_low} and {r_high}"
                return sql, params, desc, {"intent": intent, "department": dept, "range": (r_low, r_high), "metric": filter_col}
            else:
                sql = f"SELECT {proj} WHERE {filter_expr} BETWEEN ? AND ? ORDER BY {filter_expr} DESC"
                params = (r_low, r_high)
                desc = f"Filter students with {filter_col.upper()} between {r_low} and {r_high}"
                return sql, params, desc, {"intent": intent, "range": (r_low, r_high), "metric": filter_col}

        # Handle Single Comparison Filter: >, >=, <, <=, =
        if op is None or threshold is None:
            op, threshold = ">", 75.0

        allowed_ops = {">", ">=", "<", "<=", "="}
        if op not in allowed_ops:
            op = ">"

        if target_table == "courses":
            sql = f"SELECT course, credits, marks, cgpa FROM courses WHERE {filter_col} {op} ? ORDER BY {filter_col} DESC"
            params = (threshold,)
            desc = f"Filter courses with {filter_col.upper()} {op} {threshold}"
            return sql, params, desc, {"intent": intent, "table": target_table, "operator": op, "threshold": threshold, "metric": filter_col}

        if dept:
            sql = f"SELECT {proj} WHERE LOWER(department) = LOWER(?) AND {filter_expr} {op} ? ORDER BY {filter_expr} DESC"
            params = (dept, threshold)
            desc = f"Filter students in {dept} department with {filter_col.upper()} {op} {threshold}"
            return sql, params, desc, {"intent": intent, "department": dept, "operator": op, "threshold": threshold, "metric": filter_col}
        else:
            sql = f"SELECT {proj} WHERE {filter_expr} {op} ? ORDER BY {filter_expr} DESC"
            params = (threshold,)
            desc = f"Filter students with {filter_col.upper()} {op} {threshold}"
            return sql, params, desc, {"intent": intent, "operator": op, "threshold": threshold, "metric": filter_col}

    elif intent == Intent.TOP_N:
        rank_info = extract_rank_offset(normalized_text)
        n = extract_top_n(normalized_text)
        is_lowest = bool(re.search(r"\b(?:cheapest|lowest|least|bottom|cheaper)\b", normalized_text, re.IGNORECASE))
        is_fee = bool(re.search(r"\b(?:fee|fees|cost|price|cheapest|cheaper)\b", normalized_text, re.IGNORECASE))
        is_cgpa = bool(re.search(r"\b(?:cgpa|gpa)\b", normalized_text, re.IGNORECASE))

        order_dir = "ASC" if is_lowest else "DESC"

        if is_fee or target_table == "courses":
            target_table = "courses"
            sort_col = "fee" if is_fee else ("cgpa" if is_cgpa else "marks")
            req_cols = extract_requested_columns(normalized_text)
            if req_cols:
                select_items = [COLUMN_MAP.get(c, c).split(".")[-1] for c in req_cols if c in COLUMN_MAP]
                if is_fee and "fee" not in select_items:
                    select_items.append("fee")
                proj = ", ".join(select_items)
            else:
                proj = "course, fee" if is_fee else "course, credits, marks, cgpa, fee"
            sql = f"SELECT {proj} FROM courses ORDER BY {sort_col} {order_dir} LIMIT ?"
            params = (n,)
            desc = f"Select {n} courses sorted by {sort_col} {order_dir.lower()}"
            return sql, params, desc, {"intent": intent, "table": target_table, "n": n, "metric": sort_col, "direction": order_dir}

        sort_col = "cgpa" if is_cgpa else "marks"
        sort_expr = f"courses.{sort_col} {order_dir}"

        req_cols = extract_requested_columns(normalized_text)
        if req_cols:
            select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
            proj = ", ".join(select_items) + " FROM students JOIN courses ON students.course = courses.course"
        else:
            proj = STUDENT_JOIN_COURSES

        dept = extract_department(normalized_text)
        if rank_info:
            n_limit, n_offset = rank_info
            if dept:
                sql = f"SELECT {proj} WHERE LOWER(department) = LOWER(?) ORDER BY {sort_expr} LIMIT ? OFFSET ?"
                params = (dept, n_limit, n_offset)
            else:
                sql = f"SELECT {proj} ORDER BY {sort_expr} LIMIT ? OFFSET ?"
                params = (n_limit, n_offset)
            desc = f"Select rank {n_offset + 1} student sorted by {sort_col.upper()} {order_dir.lower()}"
            return sql, params, desc, {"intent": intent, "limit": n_limit, "offset": n_offset, "metric": sort_col, "direction": order_dir}

        if dept:
            sql = f"SELECT {proj} WHERE LOWER(department) = LOWER(?) ORDER BY {sort_expr} LIMIT ?"
            params = (dept, n)
            desc = f"Select top {n} students in {dept} sorted by {sort_col.upper()} {order_dir.lower()}"
            return sql, params, desc, {"intent": intent, "department": dept, "n": n, "metric": sort_col, "direction": order_dir}
        else:
            sql = f"SELECT {proj} ORDER BY {sort_expr} LIMIT ?"
            params = (n,)
            desc = f"Select top {n} students sorted by {sort_col.upper()} {order_dir.lower()}"
            return sql, params, desc, {"intent": intent, "n": n, "metric": sort_col, "direction": order_dir}

    elif intent == Intent.DEPARTMENT:
        dept = extract_department(normalized_text)
        if not dept:
            dept = "Computer Science"

        req_cols = extract_requested_columns(normalized_text)
        if req_cols:
            select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
            needs_courses = any(c in ("cgpa", "grade", "marks", "credits") for c in req_cols)
            if not needs_courses:
                simple_items = [c for c in req_cols if c in ("id", "name", "course", "department")]
                sql = f"SELECT {', '.join(simple_items)} FROM students WHERE LOWER(department) = LOWER(?) ORDER BY id ASC"
            else:
                sql = f"SELECT {', '.join(select_items)} FROM students JOIN courses ON students.course = courses.course WHERE LOWER(department) = LOWER(?) ORDER BY marks DESC"
            desc = f"Filter {', '.join(req_cols)} of students in department: {dept}"
            return sql, (dept,), desc, {"intent": intent, "department": dept, "columns": req_cols}
        else:
            sql = f"SELECT {STUDENT_JOIN_COURSES} WHERE LOWER(department) = LOWER(?) ORDER BY marks DESC"
            desc = f"Filter students belonging to department: {dept}"
            return sql, (dept,), desc, {"intent": intent, "department": dept}

    elif intent == Intent.AVERAGE_OR_COUNT:
        # Check for courses with more enrollments than average course enrollment
        if re.search(r"\bcourses?\s+with\s+more\s+enrollments?\s+than\s+(?:the\s+)?average\b", normalized_text, re.I):
            sql = (
                "SELECT course, COUNT(*) AS enrollment_count "
                "FROM students "
                "GROUP BY course "
                "HAVING COUNT(*) > (SELECT AVG(cnt) FROM (SELECT COUNT(*) AS cnt FROM students GROUP BY course))"
            )
            return sql, (), "Find courses with more enrollments than average course enrollment", {"intent": intent, "table": "students", "having": "COUNT(*) > AVG(enrollments)"}

        # Check for employees earning more than their department's average salary
        if re.search(r"\bemployees?\s+earning\s+more\s+than\s+(?:their\s+)?department'?s?\s+average\s+salary\b", normalized_text, re.I):
            sql = (
                "SELECT e1.id, e1.name, e1.department, e1.role, e1.salary "
                "FROM employees AS e1 "
                "WHERE e1.salary > (SELECT AVG(e2.salary) FROM employees AS e2 WHERE e2.department = e1.department) "
                "ORDER BY e1.department ASC, e1.salary DESC"
            )
            return sql, (), "Find employees earning more than their department's average salary", {"intent": intent, "table": "employees"}

        # Check for students enrolled in all available courses
        if re.search(r"\bstudents?\s+enrolled\s+in\s+all\s+(?:available\s+)?courses?\b", normalized_text, re.I):
            sql = (
                "SELECT students.name "
                "FROM students "
                "GROUP BY students.name "
                "HAVING COUNT(DISTINCT students.course) = (SELECT COUNT(DISTINCT course) FROM courses)"
            )
            return sql, (), "Find students enrolled in all available courses", {"intent": intent, "table": "students"}

        group_col = extract_group_by(normalized_text)
        having_metric, having_op, having_val = extract_having_clause(normalized_text)

        # Handle GROUP BY and HAVING queries first
        if group_col or having_metric:
            if having_metric == "COUNT(course)":
                sql = f"SELECT name, COUNT(course) AS course_count FROM students GROUP BY name HAVING COUNT(course) {having_op} ?"
                params = (int(having_val),)
                desc = f"Find students enrolled in {having_op} {int(having_val)} course{'s' if int(having_val) > 1 else ''}"
                return sql, params, desc, {"intent": intent, "table": "students", "group_by": "name", "having": f"COUNT(course) {having_op} {int(having_val)}"}
            if not group_col:
                group_col = "department"

            is_salary = bool(re.search(r"\b(?:salary|salaries)\b", normalized_text, re.IGNORECASE))
            is_cgpa = bool(re.search(r"\b(?:cgpa|gpa)\b", normalized_text, re.IGNORECASE))
            is_marks = bool(re.search(r"\b(?:marks?|scores?)\b", normalized_text, re.IGNORECASE))
            agg = extract_aggregate_type(normalized_text)

            if is_salary or target_table == "employees":
                table_target = "employees"
                if having_metric:
                    sql = f"SELECT {group_col}, ROUND(AVG(salary), 2) AS average_salary FROM employees GROUP BY {group_col} HAVING {having_metric} {having_op} ?"
                    params = (having_val,)
                    desc = f"Find {group_col}s where {having_metric} {having_op} {having_val}"
                    return sql, params, desc, {"intent": intent, "table": table_target, "group_by": group_col, "having": f"{having_metric} {having_op} {having_val}"}
                else:
                    agg_col = "ROUND(AVG(salary), 2) AS average_salary" if agg == "AVG" else "COUNT(*) AS employee_count"
                    sql = f"SELECT {group_col}, {agg_col} FROM employees GROUP BY {group_col} ORDER BY {group_col} ASC"
                    desc = f"Calculate {agg} for each {group_col} from employees"
                    return sql, (), desc, {"intent": intent, "table": table_target, "group_by": group_col, "aggregate": agg}

            elif is_cgpa or is_marks:
                metric = "cgpa" if is_cgpa else "marks"
                metric_col = f"courses.{metric}"
                group_expr = f"students.{group_col}"
                if having_metric:
                    having_expr = f"AVG(courses.{metric})" if "avg" in having_metric.lower() else having_metric
                    sql = f"SELECT {group_expr}, ROUND(AVG({metric_col}), 2) AS average_{metric} FROM students JOIN courses ON students.course = courses.course GROUP BY {group_expr} HAVING {having_expr} {having_op} ?"
                    params = (having_val,)
                    desc = f"Find {group_col}s where {having_metric} {having_op} {having_val}"
                    return sql, params, desc, {"intent": intent, "table": "students JOIN courses", "group_by": group_col, "having": f"{having_metric} {having_op} {having_val}"}
                else:
                    sql = f"SELECT {group_expr}, ROUND(AVG({metric_col}), 2) AS average_{metric} FROM students JOIN courses ON students.course = courses.course GROUP BY {group_expr} ORDER BY average_{metric} DESC"
                    desc = f"Find average {metric.upper()} for each {group_col}"
                    return sql, (), desc, {"intent": intent, "table": "students JOIN courses", "group_by": group_col, "metric": metric, "aggregate": "AVG"}

            else:
                # Count by group_col on students (e.g. "Count the students in each branch", "Show branches with more than 10 students")
                if having_metric:
                    sql = f"SELECT {group_col}, COUNT(*) AS student_count FROM students GROUP BY {group_col} HAVING {having_metric} {having_op} ?"
                    params = (int(having_val) if having_val.is_integer() else having_val,)
                    desc = f"Show {group_col}s with {having_metric} {having_op} {having_val}"
                    return sql, params, desc, {"intent": intent, "table": "students", "group_by": group_col, "having": f"{having_metric} {having_op} {having_val}"}
                else:
                    sql = f"SELECT {group_col}, COUNT(*) AS student_count FROM students GROUP BY {group_col} ORDER BY student_count DESC"
                    desc = f"Count students in each {group_col}"
                    return sql, (), desc, {"intent": intent, "table": "students", "group_by": group_col, "aggregate": "COUNT"}

        is_cgpa = bool(re.search(r"\b(?:cgpa|gpa)\b", normalized_text, re.IGNORECASE))
        is_fee = bool(re.search(r"\b(?:fee|fees|cost|price)\b", normalized_text, re.IGNORECASE))
        is_credits = bool(re.search(r"\b(?:credits?)\b", normalized_text, re.IGNORECASE))
        if is_cgpa:
            metric = "cgpa"
        elif is_fee:
            metric = "fee"
        elif is_credits:
            metric = "credits"
        else:
            metric = "marks"

        agg = extract_aggregate_type(normalized_text)

        # 1. Custom tables
        if target_table not in ("students", "courses", "employees"):
            sql = f"SELECT COUNT(*) AS total_{target_table} FROM {target_table}"
            desc = f"Calculate count for custom table '{target_table}'"
            return sql, (), desc, {"intent": intent, "table": target_table, "aggregate": "COUNT"}

        if target_table == "employees":
            if agg == "AVG":
                sql = "SELECT ROUND(AVG(salary), 2) AS average_salary FROM employees"
                return sql, (), "Calculate average salary across employees", {"intent": intent, "table": "employees", "aggregate": "AVG", "metric": "salary"}
            else:
                sql = "SELECT COUNT(*) AS total_employees FROM employees"
                return sql, (), "Calculate total employees", {"intent": intent, "table": "employees", "aggregate": "COUNT"}

        # 2. Courses table (explicit target or fee metric)
        if target_table == "courses" or is_fee:
            if agg == "MIN_MAX":
                sql = f"SELECT MIN({metric}) AS min_{metric}, MAX({metric}) AS max_{metric} FROM courses"
                desc = f"Find minimum and maximum {metric} of courses"
                return sql, (), desc, {"intent": intent, "table": "courses", "aggregate": "MIN_MAX", "metric": metric}
            elif agg == "AVG":
                sql = f"SELECT ROUND(AVG({metric}), 2) AS average_{metric} FROM courses"
                desc = f"Calculate average {metric} across courses"
                return sql, (), desc, {"intent": intent, "table": "courses", "aggregate": "AVG", "metric": metric}
            elif agg == "MAX":
                sql = f"SELECT MAX({metric}) AS max_{metric} FROM courses"
                desc = f"Find maximum {metric} of courses"
                return sql, (), desc, {"intent": intent, "table": "courses", "aggregate": "MAX", "metric": metric}
            elif agg == "MIN":
                sql = f"SELECT MIN({metric}) AS min_{metric} FROM courses"
                desc = f"Find minimum {metric} of courses"
                return sql, (), desc, {"intent": intent, "table": "courses", "aggregate": "MIN", "metric": metric}
            else:
                sql = "SELECT COUNT(*) AS total_courses FROM courses"
                desc = "Calculate total number of courses"
                return sql, (), desc, {"intent": intent, "table": "courses", "aggregate": "COUNT"}

        # 3. Students table (default)
        dept = extract_department(normalized_text)
        op, threshold = extract_marks_filter(normalized_text)
        metric_expr = f"courses.{metric}" if is_cgpa else "marks"

        if agg == "MIN_MAX":
            col_min = f"MIN(courses.{metric})" if is_cgpa else f"MIN(marks)"
            col_max = f"MAX(courses.{metric})" if is_cgpa else f"MAX(marks)"
            sql = f"SELECT {col_min} AS min_{metric}, {col_max} AS max_{metric} FROM students JOIN courses ON students.course = courses.course"
            desc = f"Find minimum and maximum {metric}"
            return sql, (), desc, {"intent": intent, "aggregate": "MIN_MAX", "metric": metric}

        if agg == "AVG":
            agg_col = f"ROUND(AVG({metric_expr}), 2) AS average_{metric}"
        elif agg == "MAX":
            agg_col = f"MAX({metric_expr}) AS highest_{metric}"
        elif agg == "MIN":
            agg_col = f"MIN({metric_expr}) AS lowest_{metric}"
        else:
            agg_col = "COUNT(*) AS total_students"

        # Check for conditioned aggregate
        if dept and op and threshold:
            sql = f"SELECT {agg_col} FROM students JOIN courses ON students.course = courses.course WHERE LOWER(department) = LOWER(?) AND {metric_expr} {op} ?"
            params = (dept, threshold)
            desc = f"Calculate {agg} for department: {dept} with {metric} {op} {threshold}"
            return sql, params, desc, {"intent": intent, "aggregate": agg, "department": dept, "operator": op, "threshold": threshold, "metric": metric}
        elif dept:
            if agg in ("AVG", "MAX", "MIN") or is_cgpa:
                sql = f"SELECT {agg_col} FROM students JOIN courses ON students.course = courses.course WHERE LOWER(department) = LOWER(?)"
            else:
                sql = f"SELECT {agg_col} FROM students WHERE LOWER(department) = LOWER(?)"
            params = (dept,)
            desc = f"Calculate {agg} for department: {dept}"
            return sql, params, desc, {"intent": intent, "aggregate": agg, "department": dept}
        elif op and threshold:
            sql = f"SELECT {agg_col} FROM students JOIN courses ON students.course = courses.course WHERE {metric_expr} {op} ?"
            params = (threshold,)
            desc = f"Calculate {agg} for students with {metric} {op} {threshold}"
            return sql, params, desc, {"intent": intent, "aggregate": agg, "operator": op, "threshold": threshold, "metric": metric}
        else:
            if agg in ("AVG", "MAX", "MIN") or is_cgpa:
                sql = f"SELECT {agg_col} FROM students JOIN courses ON students.course = courses.course"
            else:
                sql = f"SELECT {agg_col} FROM students"
            desc = f"Calculate overall {agg}"
            return sql, (), desc, {"intent": intent, "aggregate": agg, "metric": metric}

    elif intent == Intent.NAME_SEARCH:
        prefix = extract_name_prefix(normalized_text)
        if prefix:
            req_cols = extract_requested_columns(normalized_text)
            if req_cols:
                select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
                needs_courses = any(c in ("cgpa", "grade", "marks", "credits") for c in req_cols)
                if not needs_courses:
                    simple_items = [c for c in req_cols if c in ("id", "name", "course", "department")]
                    sql = f"SELECT {', '.join(simple_items)} FROM students WHERE LOWER(name) LIKE LOWER(?) ORDER BY id ASC"
                else:
                    sql = f"SELECT {', '.join(select_items)} FROM students JOIN courses ON students.course = courses.course WHERE LOWER(students.name) LIKE LOWER(?) ORDER BY students.id ASC"
                desc = f"List {', '.join(req_cols)} of students whose names start with '{prefix}'"
                return sql, (f"{prefix.lower()}%",), desc, {"intent": intent, "prefix": prefix, "columns": req_cols}
            else:
                sql = f"SELECT {STUDENT_JOIN_COURSES} WHERE LOWER(students.name) LIKE LOWER(?) ORDER BY students.id ASC"
                desc = f"Search for students whose names start with '{prefix}'"
                return sql, (f"{prefix.lower()}%",), desc, {"intent": intent, "prefix": prefix}

        name = extract_student_name(normalized_text)
        if not name:
            tokens = normalized_text.split()
            name = tokens[-1] if tokens else "Aarav"

        req_cols = extract_requested_columns(normalized_text)
        name_tokens = [t for t in name.split() if len(t) > 1]

        if req_cols:
            select_items = [COLUMN_MAP[c] for c in req_cols if c in COLUMN_MAP]
            needs_courses = any(c in ("cgpa", "grade", "marks", "credits") for c in req_cols)
            if not needs_courses:
                simple_items = [c for c in req_cols if c in ("id", "name", "course", "department")]
                if len(name_tokens) >= 2:
                    sql = (
                        f"SELECT {', '.join(simple_items)} FROM students "
                        "WHERE LOWER(name) LIKE LOWER(?) OR (LOWER(name) LIKE LOWER(?) AND LOWER(name) LIKE LOWER(?))"
                    )
                    params = (f"%{name}%", f"%{name_tokens[0]}%", f"%{name_tokens[1]}%")
                else:
                    sql = f"SELECT {', '.join(simple_items)} FROM students WHERE LOWER(name) LIKE LOWER(?)"
                    params = (f"%{name}%",)
            else:
                if len(name_tokens) >= 2:
                    sql = (
                        f"SELECT {', '.join(select_items)} FROM students JOIN courses ON students.course = courses.course "
                        "WHERE LOWER(students.name) LIKE LOWER(?) OR (LOWER(students.name) LIKE LOWER(?) AND LOWER(students.name) LIKE LOWER(?))"
                    )
                    params = (f"%{name}%", f"%{name_tokens[0]}%", f"%{name_tokens[1]}%")
                else:
                    sql = f"SELECT {', '.join(select_items)} FROM students JOIN courses ON students.course = courses.course WHERE LOWER(students.name) LIKE LOWER(?)"
                    params = (f"%{name}%",)
            desc = f"Get {', '.join(req_cols)} of student '{name}'"
            return sql, params, desc, {"intent": intent, "name": name, "columns": req_cols}
        else:
            if len(name_tokens) >= 2:
                sql = (
                    f"SELECT {STUDENT_JOIN_COURSES} "
                    "WHERE LOWER(name) LIKE LOWER(?) OR (LOWER(name) LIKE LOWER(?) AND LOWER(name) LIKE LOWER(?)) "
                    "ORDER BY marks DESC"
                )
                params = (f"%{name}%", f"%{name_tokens[0]}%", f"%{name_tokens[1]}%")
            else:
                sql = f"SELECT {STUDENT_JOIN_COURSES} WHERE LOWER(name) LIKE LOWER(?) ORDER BY marks DESC"
                params = (f"%{name}%",)

            desc = f"Search for student record where name matches '{name}'"
            return sql, params, desc, {"intent": intent, "name": name}

    else:
        # Intent.NO_MATCH
        return None, None, "Display unsupported question message", {"intent": Intent.NO_MATCH}

def generate_sql(intent: str, normalized_text: str):
    """
    Translates the classified intent and extracted entities into a parameterized SQL template.
    Formats the SQL into structured multi-line order with trailing semicolon.
    Returns:
        (sql_template: str, parameters: tuple, description: str, entity_info: dict)
    """
    sql, params, desc, entity_info = _build_sql(intent, normalized_text)
    if sql:
        sql = format_sql(sql)
    return sql, params, desc, entity_info

