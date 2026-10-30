"""
Entity extraction module.
Extracts parameters and entities flexibly from natural English queries:
- Marks filter (operators, thresholds, ranges)
- Top N / Rank (counts, toppers, best)
- Department name (synonyms, aliases, abbreviations)
- Student name (DB-backed fuzzy matching + pattern extraction)
- Aggregate functions (AVG, COUNT, MAX, MIN)
"""

import os
import re
import sqlite3

# NLTK integration for natural language tokenization, stop-words, and stemming
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    NLTK_AVAILABLE = True
    NLTK_STOPWORDS = set(stopwords.words("english"))
    stemmer = PorterStemmer()
except Exception:
    NLTK_AVAILABLE = False
    NLTK_STOPWORDS = set()
    stemmer = None

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "students.db"
)

# Canonical department mapping covering common abbreviations, branches, and synonyms
DEPARTMENT_SYNONYMS = {
    "computer science engineering": "Computer Science",
    "computer science": "Computer Science",
    "computer engineering": "Computer Science",
    "comp sci": "Computer Science",
    "cse": "Computer Science",
    "cs": "Computer Science",
    
    "data science": "Data Science",
    "data analytics": "Data Science",
    "ds": "Data Science",
    
    "artificial intelligence & machine learning": "AI & ML",
    "artificial intelligence and machine learning": "AI & ML",
    "artificial intelligence": "AI & ML",
    "machine learning": "AI & ML",
    "ai & ml": "AI & ML",
    "ai and ml": "AI & ML",
    "aiml": "AI & ML",
    "ai": "AI & ML",
    "ml": "AI & ML",
    
    "mechanical engineering": "Mechanical",
    "mechanical": "Mechanical",
    "mech": "Mechanical",
    
    "electrical engineering": "Electrical",
    "electrical": "Electrical",
    "eee": "Electrical",
    "ece": "Electrical",
    
    "civil engineering": "Civil",
    "civil": "Civil",
    
    "mathematics": "Mathematics",
    "applied mathematics": "Mathematics",
    "maths": "Mathematics",
    "math": "Mathematics",
}

COMPARISON_PATTERNS = [
    # Compound & negated comparisons first to prevent greedy substring matching
    (r"(?:not greater than or equal to|not more than or equal to)", "<"),
    (r"(?:not less than or equal to|not fewer than or equal to)", ">"),
    (r"(?:greater than or equal to|at least|minimum of|not less than|not fewer than|not below|not under|>=)", ">="),
    (r"(?:less than or equal to|at most|maximum of|not more than|not greater than|not higher than|not above|not exceeding|not over|<=)", "<="),
    (r"(?:greater than|more than|above|higher than|exceeding|over|strictly greater|>)", ">"),
    (r"(?:less than|fewer than|below|under|strictly less|<)", "<"),
    (r"(?:equal to|equals|exactly|scoring exactly|=)", "="),
]

def get_known_student_names(db_path=DEFAULT_DB_PATH):
    """Retrieves all student names currently in the database for fuzzy name matching."""
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students")
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names
    except Exception:
        return []

def extract_department(text: str):
    """
    Finds department names or common synonyms in the query.
    Returns the canonical department name, or None.
    """
    # Sort synonyms by length descending so longer phrases match first
    sorted_synonyms = sorted(DEPARTMENT_SYNONYMS.keys(), key=lambda s: len(s), reverse=True)
    for syn in sorted_synonyms:
        # Match as word phrase
        pattern = r"\b" + re.escape(syn) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return DEPARTMENT_SYNONYMS[syn]
    return None

def extract_marks_filter(text: str):
    """
    Extracts comparison operator and numerical threshold for marks.
    Returns: (operator: str, threshold: float) or (None, None)
    """
    # 1. Standard pattern: operator followed by number (e.g. "greater than 85", ">= 90")
    for regex_pat, op in COMPARISON_PATTERNS:
        match = re.search(regex_pat + r"\s+([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if match:
            return op, float(match.group(1))

    # 2. Number followed by operator keyword (e.g. "80 or more", "75 and above", "60 or higher")
    above_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:\+|or more|and above|or above|or higher)", text, re.IGNORECASE)
    if above_match:
        return ">=", float(above_match.group(1))

    below_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:or less|and below|or below|or lower)", text, re.IGNORECASE)
    if below_match:
        return "<=", float(below_match.group(1))

    # 3. Direct scored / got / score pattern (e.g. "scored 90 marks", "having 85 marks")
    score_match = re.search(r"\b(?:scored|got|having|score of|marks of)\s+([0-9]+(?:\.[0-9]+)?)\b", text, re.IGNORECASE)
    if score_match:
        return "=", float(score_match.group(1))

    # 4. Symbol format: "marks > 80", "score <= 75"
    sym_match = re.search(r"(?:marks|score)\s*(>=|<=|>|<|=)\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    if sym_match:
        return sym_match.group(1), float(sym_match.group(2))

    # 5. Direct operator with number without explicit 'marks' (e.g. "> 80", "< 60")
    num_op_match = re.search(r"\b(>=|<=|>|<|=)\s*([0-9]+(?:\.[0-9]+)?)\b", text)
    if num_op_match:
        return num_op_match.group(1), float(num_op_match.group(2))

    return None, None

def extract_range_filter(text: str):
    """
    Extracts numerical range: (low: float, high: float)
    E.g. 'between 70 and 90 marks' -> (70.0, 90.0)
         'from 7.5 to 9.5 cgpa' -> (7.5, 9.5)
         'scored between 70 and 90' -> (70.0, 90.0)
    """
    pattern = r"\b(?:between|from|in\s+the\s+range\s+of|in\s+range)\s+([0-9]+(?:\.[0-9]+)?)\s+(?:and|to|-)\s+([0-9]+(?:\.[0-9]+)?)\b"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        v1 = float(m.group(1))
        v2 = float(m.group(2))
        return min(v1, v2), max(v1, v2)
    return None, None

def extract_name_prefix(text: str):
    """
    Extracts name prefix letter / character for queries like:
    'whose names start with A'
    'name starting with S'
    'begins with R'
    Returns: prefix uppercase letter (e.g. 'A') or None
    """
    pattern = r"\b(?:names?|students?)\s+(?:whose\s+names?\s+)?(?:start(?:s|ing)?|begin(?:s|ning)?)\s+with\s+['\"]?([A-Za-z])['\"]?\b"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    pattern2 = r"\b(?:start(?:s|ing)?|begin(?:s|ning)?)\s+with\s+(?:letter\s+)?['\"]?([A-Za-z])['\"]?\b"
    m2 = re.search(pattern2, text, re.IGNORECASE)
    if m2:
        return m2.group(1).upper()

    return None

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "single": 1
}

def parse_num_word_or_digit(val: str) -> int:
    val = val.strip().lower()
    if val.isdigit():
        return int(val)
    return WORD_TO_NUM.get(val, 5)

def extract_top_n(text: str):
    """
    Extracts N count for Top N / ranking query.
    Supports digits and English number words (e.g. 'five students', 'three cheapest courses').
    """
    lowered = text.lower()
    num_pattern = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"

    # 1. Number preceding noun / superlative: "the five students with the highest marks", "three cheapest courses"
    m_prec = re.search(r"\b(?:the\s+)?(" + num_pattern + r")\s+(?:top|best|highest|lowest|cheapest|bottom|students?|courses?|scorers?|toppers?)", lowered)
    if m_prec:
        return parse_num_word_or_digit(m_prec.group(1))

    # 2. Superlative preceding number: "top 5 students", "top three courses", "cheapest 3"
    m_post = re.search(r"\b(?:top|best|highest|lowest|cheapest|bottom|first|peak)\s+(" + num_pattern + r")\b", lowered)
    if m_post:
        return parse_num_word_or_digit(m_post.group(1))

    # Single top student / topper
    if re.search(r"\b(?:topper|toppers|top student|top scorer|highest marks?|highest scorer|best student|rank 1|number 1)\b", lowered):
        return 1

    # Generic top intent without explicit number -> default to 5
    if re.search(r"\b(?:top|best|highest|cheapest|lowest)\b", lowered):
        return 5

    return 5

def extract_rank_offset(text: str):
    """
    Extracts rank offset for ordinal queries like 'second-highest', '2nd highest', 'third highest'.
    Returns (limit, offset) or None.
    """
    lowered = text.lower()
    ordinals = {
        "first": 0, "1st": 0,
        "second": 1, "2nd": 1,
        "third": 2, "3rd": 2,
        "fourth": 3, "4th": 3,
        "fifth": 4, "5th": 4,
    }
    m = re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s*[- ]\s*(?:highest|best|topper|lowest|cheapest|maximum|minimum|cgpa|marks?)\b", lowered)
    if m:
        ord_word = m.group(1).lower()
        return 1, ordinals.get(ord_word, 0)
    return None

def extract_sort_clause(text: str):
    """
    Extracts sorting column and direction from queries like:
    'Arrange students by CGPA in descending order' -> ('cgpa', 'DESC')
    'Sort students alphabetically by name' -> ('name', 'ASC')
    'Sort by marks descending' -> ('marks', 'DESC')
    Returns: (column: str or None, direction: str 'ASC' or 'DESC') or (None, None)
    """
    lowered = text.lower().strip()
    if not re.search(r"\b(?:sort|arrange|order|ordered|sorted|arranging|sorting)\b", lowered):
        return None, None

    direction = "ASC"
    if re.search(r"\b(?:descending|desc|highest\s+first|reverse)\b", lowered):
        direction = "DESC"
    elif re.search(r"\b(?:ascending|asc|alphabetical(?:ly)?|lowest\s+first)\b", lowered):
        direction = "ASC"
    else:
        # Default direction based on metric type
        if re.search(r"\b(?:cgpa|gpa|marks?|scores?)\b", lowered):
            direction = "DESC"
        else:
            direction = "ASC"

    col = None
    if re.search(r"\b(?:cgpa|gpa)\b", lowered):
        col = "cgpa"
    elif re.search(r"\b(?:marks?|scores?)\b", lowered):
        col = "marks"
    elif re.search(r"\b(?:names?|alphabetical(?:ly)?)\b", lowered):
        col = "name"
    elif re.search(r"\b(?:courses?)\b", lowered):
        col = "course"
    elif re.search(r"\b(?:credits?)\b", lowered):
        col = "credits"
    elif re.search(r"\b(?:departments?|dept)\b", lowered):
        col = "department"
    elif re.search(r"\b(?:fee|fees|cost|price)\b", lowered):
        col = "fee"
    elif re.search(r"\b(?:id|roll)\b", lowered):
        col = "id"

    return col, direction

def extract_student_name(text: str):
    """
    Extracts student name using a hybrid approach:
    1. Database Name Match: matches known student first, last, or full names.
    2. Linguistic Patterns: matches natural phrasing ('student named X', 'details of X', 'who is X').
    """
    clean_text = text.strip()
    lowered = clean_text.lower()

    # Step 1: Check against known database student records
    known_names = get_known_student_names()
    for full_name in known_names:
        # Check full name
        if re.search(r"\b" + re.escape(full_name.lower()) + r"\b", lowered):
            return full_name
        
        # Check individual distinct parts (first name / last name)
        # Avoid short/generic common tokens
        parts = [p for p in full_name.split() if len(p) >= 4]
        for part in parts:
            # Match whole word
            if re.search(r"\b" + re.escape(part.lower()) + r"\b", lowered):
                return full_name

    # Step 2: Linguistic Extraction Patterns
    patterns = [
        # Explicit named ...
        r"(?:named|student named|name is|name like|called)\s+([a-zA-Z\s]+?)(?:\s+(?:in|from|with|who|having)|$)",
        # Details of / about / record of / profile of ...
        r"(?:details of|info of|information about|record of|profile of|about)\s+(?:student\s+)?([a-zA-Z\s]+?)(?:\s+(?:in|from|with|who|having)|$)",
        # Search for / find / lookup / who is (excluding prepositions like 'in', 'from')
        r"(?:search for|search|find|lookup|who is)\s+(?:student\s+|the\s+student\s+)?(?!(?:in|from|of|at|with)\b)([a-zA-Z\s]+?)(?:\s+(?:in|from|with|who|having)|$)",
        # Show / display / get / view student <name>
        r"(?:show|display|get|view)\s+(?:the\s+)?student\s+([a-zA-Z\s]+?)(?:\s+(?:in|from|with|who|having)|$)",
        # Direct 'student <name>'
        r"^student\s+([a-zA-Z\s]+)$"
    ]

    stop_words = {
        "all", "the", "students", "student", "records", "record",
        "name", "names", "only", "just",
        "marks", "department", "data", "list", "everyone", "every student",
        "who", "what", "where", "how", "show", "display", "get", "view",
        "select", "find", "search", "details", "info", "information",
        "average", "avg", "mean", "count", "top", "best", "highest"
    }

    for pat in patterns:
        m = re.search(pat, clean_text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            candidate = re.sub(r"[?!.,]", "", candidate).strip()
            cand_words = candidate.lower().split()
            if not cand_words or any(w in stop_words for w in cand_words):
                continue
            if len(candidate) > 1 and candidate.lower() not in DEPARTMENT_SYNONYMS:
                return candidate

    # Step 3: Standalone name check (user simply types 'Vikram Rathod' or 'Aarav')
    words = clean_text.split()
    if 1 <= len(words) <= 3 and all(w.isalpha() for w in words):
        lowered_words = [w.lower() for w in words]
        if not any(w in stop_words for w in lowered_words):
            if lowered not in DEPARTMENT_SYNONYMS:
                return clean_text

    return None

def extract_aggregate_type(text: str):
    """
    Identifies whether the aggregate is AVG, COUNT, MAX, MIN, or MIN_MAX.
    """
    lowered = text.lower()
    if re.search(r"\b(?:min(?:imum)?\s+and\s+max(?:imum)?|max(?:imum)?\s+and\s+min(?:imum)?|lowest\s+and\s+highest|highest\s+and\s+lowest)\b", lowered):
        return "MIN_MAX"
    if re.search(r"\b(?:average|avg|mean|mean score|average score|avg marks|average cgpa)\b", lowered):
        return "AVG"
    if re.search(r"\b(?:maximum|highest|max|peak)\b", lowered):
        return "MAX"
    if re.search(r"\b(?:minimum|lowest|min|cheapest)\b", lowered):
        return "MIN"
    if re.search(r"\b(?:how many|count|number of|total students|total courses|total count|calculate\s+(?:the\s+)?total|total\s+number\s+of)\b", lowered):
        return "COUNT"
    return "COUNT"

def extract_requested_columns(text: str) -> list:
    """
    Extracts specific column attributes requested by the user.
    Recognizes: id, name, grade, marks, course, credits, department.
    Returns: list of column strings, e.g. ['id'], ['name', 'grade'].
    If no specific columns are requested (e.g. 'show all students', 'who scored > 80', 'who is Priya'), returns [].
    """
    lowered = text.lower().strip()
    cols = []

    # 1. Check for ID / Roll number request
    if re.search(r"\b(?:id|ids|roll|roll\s*no|roll\s*number)\b", lowered):
        cols.append("id")

    # 2. Check for Name request (exclude 'named <person>', name prefix filters e.g. 'names start with A', and sorting e.g. 'alphabetically by name')
    is_name_prefix_filter = bool(re.search(r"\bnames?\s+(?:start|begin|like)\b", lowered) or re.search(r"\bwhose\s+names?\b", lowered))
    is_sort_name = bool(re.search(r"\b(?:by|alphabetical(?:ly)?)\s+names?\b", lowered) or re.search(r"\balphabetical(?:ly)?\b", lowered))
    explicit_name_request = bool(re.search(r"\b(?:show|display|get|give|list)\s+(?:the\s+)?names?\s+(?:of|and)\b", lowered) or re.search(r"\b(?:and|only)\s+names?\b", lowered) or re.search(r"\bstudent'?s?\s+names?\b", lowered))
    is_course_name_only = bool(re.search(r"\bcourses?\s+names?\b", lowered) and not re.search(r"\bstudents?\b", lowered))
    if re.search(r"\b(?:names?|student\s+names?)\b", lowered) and not re.search(r"\bnamed\b", lowered) and not is_course_name_only:
        if (not is_name_prefix_filter and not is_sort_name) or explicit_name_request:
            cols.append("name")

    # 3. Check for CGPA / Grade request (exclude comparison/range filter e.g. 'cgpa > 8', 'cgpa is not less than 7', and sorting 'by cgpa')
    has_comp = bool(
        extract_marks_filter(lowered)[0] is not None or
        extract_range_filter(lowered)[0] is not None or
        re.search(r"\b(?:greater|more|above|higher|less|below|under|at least|at most|not less|not more|>=|<=|>|<|=)\b", lowered)
    )
    has_cgpa = bool(re.search(r"\b(?:cgpa|gpa)\b", lowered))
    is_cgpa_filter = has_comp and has_cgpa
    is_cgpa_sort = bool(re.search(r"\bby\s+(?:cgpa|gpa)\b", lowered) or re.search(r"\b(?:top|best|highest|lowest)\s+(?:cgpa|gpa)\b", lowered))
    explicit_cgpa_proj = bool(re.search(r"\b(?:and\s+cgpa|cgpa\s+and|names?\s*,\s*cgpa|show\s+cgpa|display\s+cgpa|give\s+cgpa)\b", lowered))
    if re.search(r"\b(?:cgpa|gpa|grades?)\b", lowered) and ((not is_cgpa_filter and not is_cgpa_sort) or explicit_cgpa_proj):
        cols.append("cgpa")

    # 4. Check for Marks request (exclude comparison filter / range filter / aggregate / ranking e.g. 'marks > 80', 'between 70 and 90 marks', 'highest marks')
    is_marks_filter = bool(
        re.search(r"\b(?:marks?\s*(?:>|<|=|>=|<=|greater|more|above|below|less|under|\d+)|\d+\s*marks?)\b", lowered) or
        extract_range_filter(lowered)[0] is not None
    )
    is_avg_marks = bool(re.search(r"\b(?:average|avg|mean)\s+marks?\b", lowered))
    is_marks_ranking = bool(re.search(r"\b(?:top|best|highest|lowest|maximum|minimum|topper)\s+(?:marks?|scores?)\b", lowered) or re.search(r"\b(?:with\s+the\s+)?(?:highest|lowest)\s+marks?\b", lowered) or re.search(r"\bby\s+marks?\b", lowered))
    if re.search(r"\b(?:marks?|scores?)\b", lowered) and not is_marks_filter and not is_avg_marks and not is_marks_ranking:
        cols.append("marks")

    # 5. Check for Fee request (exclude 'cheapest courses')
    is_fee_ranking = bool(re.search(r"\b(?:cheapest|lowest|highest|costliest)\b", lowered) or re.search(r"\bby\s+(?:fee|fees|cost|price)\b", lowered))
    if re.search(r"\b(?:fee|fees|cost|costs|price|prices)\b", lowered) and not is_fee_ranking:
        cols.append("fee")

    # 5. Check for Course request (exclude 'all courses', 'in courses', or join table names)
    is_join_syntax = bool(re.search(r"\b(?:join|joining|joined|combine|both)\b", lowered) or (re.search(r"\bstudents?\b", lowered) and re.search(r"\bcourses?\b", lowered)))
    is_enrolled_courses = bool(re.search(r"\b(?:enrolled\s+courses?|courses?\s+enrolled|their\s+courses?|student\s+courses?|course\s+names?|course\s+title|course\s+column)\b", lowered))
    is_table_target = bool(
        (re.search(r"\b(?:show|display|list|all)\s+courses?\b", lowered) and not re.search(r"\b(?:and|of)\s+courses?\b", lowered) and not is_enrolled_courses) or
        (is_join_syntax and not is_enrolled_courses)
    )
    if (re.search(r"\b(?:courses?|subjects?)\b", lowered) or is_enrolled_courses) and not is_table_target and not re.search(r"\b(?:in|from)\s+courses?\b", lowered):
        cols.append("course")

    # 6. Check for Credits request
    if re.search(r"\b(?:credits?)\b", lowered):
        cols.append("credits")

    # 7. Check for Department request (exclude 'in CS department')
    is_dept_filter = bool(re.search(r"\b(?:in|from)\s+(?:the\s+)?(?:[a-z\s]+?\s+)?(?:department|dept|branch)\b", lowered))
    if re.search(r"\b(?:departments?|depts?|branch(?:es)?)\b", lowered) and not is_dept_filter:
        cols.append("department")

    # 8. Check for Instructor / Professor request
    if re.search(r"\b(?:instructors?|professors?|teachers?|faculty)\b", lowered):
        cols.append("instructor")

    # 9. Check for Salary request
    if re.search(r"\b(?:salary|salaries|wage|wages|pay)\b", lowered):
        cols.append("salary")

    # 10. Check for Role request
    if re.search(r"\b(?:roles?|job|designation)\b", lowered):
        cols.append("role")

    return cols

def extract_target_table(text: str, db_path=DEFAULT_DB_PATH):
    """
    Detects if the query explicitly targets a specific database table.
    Defaults to 'students' if no other table is mentioned.
    """
    if not os.path.exists(db_path):
        return "students"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        all_tables = [r[0] for r in cursor.fetchall()]
        conn.close()

        lowered = text.lower()

        # Check if query references salary / employee table
        if re.search(r"\b(?:salary|salaries|wage|wages|employees?|staff|role|roles)\b", lowered):
            return "employees"

        # Check if query references instructors/professors -> courses table
        if re.search(r"\b(?:instructors?|professors?|teachers?)\b", lowered) and not re.search(r"\bstudents?\b", lowered):
            return "courses"

        # Check if query is explicitly joining tables or mentions both students and courses
        has_students = bool(re.search(r"\bstudents?\b", lowered))
        has_courses = bool(re.search(r"\bcourses?\b", lowered))
        has_join = bool(re.search(r"\b(?:join|joining|joined|combine|combining|both)\b", lowered))

        if (has_students and has_courses) or (has_join and (has_students or has_courses)):
            return "students"

        # Sort tables by length descending so multi-word tables (e.g. 'student_courses') match before substring tables (e.g. 'courses')
        sorted_tables = sorted([t for t in all_tables if t != "students"], key=len, reverse=True)
        for tbl in sorted_tables:
            # Match singular or plural of custom table, supporting spaces and underscores
            tbl_clean = tbl.lower()
            base = tbl_clean.rstrip("s") if tbl_clean.endswith("s") else tbl_clean
            pattern = r"\b" + re.escape(base).replace("_", r"[\s_]+") + r"(?:s|es)?\b"
            if re.search(pattern, lowered):
                return tbl
        return "students"
    except Exception:
        return "students"

def extract_group_by(text: str):
    """
    Extracts GROUP BY grouping column if present (e.g. 'department', 'course').
    Supports synonyms: 'branch' -> 'department'.
    Returns: group_col (str) or None.
    """
    lowered = text.lower()
    if re.search(r"\bstudents?\s+(?:enrolled\s+in\s+)?(?:more\s+than|greater\s+than|>)\s+(?:one|\d+)\s+courses?\b", lowered):
        return "name"

    has_group = bool(
        re.search(r"\b(?:in\s+each|for\s+each|each|per|by)\s+(?:branch(?:es)?|departments?|depts?|courses?|subjects?)\b", lowered) or
        re.search(r"\b(?:branches|departments|depts)\s+(?:with|whose|having)\b", lowered)
    )
    if not has_group:
        return None

    if re.search(r"\b(?:branch(?:es)?|departments?|depts?)\b", lowered):
        return "department"
    elif re.search(r"\bcourses?\b", lowered):
        return "course"
    return "department"

def extract_having_clause(text: str):
    """
    Extracts HAVING condition: (metric_expr, operator, threshold).
    E.g.
    'Show branches with more than 10 students' -> ('COUNT(*)', '>', 10.0)
    'Find departments whose average salary exceeds ₹50,000' -> ('AVG(salary)', '>', 50000.0)
    'Find students enrolled in more than one course' -> ('COUNT(course)', '>', 1.0)
    """
    lowered = text.lower()

    # 0. Multi-course enrollment condition: "more than one course", "enrolled in more than 2 courses"
    m_multi_course = re.search(r"\b(?:enrolled\s+in\s+)?(?:more\s+than|greater\s+than|>)\s+(one|\d+)\s+courses?\b", lowered)
    if m_multi_course:
        val = parse_num_word_or_digit(m_multi_course.group(1))
        return "COUNT(course)", ">", float(val)

    # 1. Having student/record count condition: "more than 10 students", "fewer than 5 students"
    m_cnt_gt = re.search(r"\b(?:with\s+)?(?:more\s+than|greater\s+than|above|>|at\s+least|>=|exceeds?|not\s+less\s+than|not\s+fewer\s+than)\s+([0-9,]+)\s+students?\b", lowered)
    if m_cnt_gt:
        op = ">=" if any(w in m_cnt_gt.group(0) for w in ("least", "not less", "not fewer")) else ">"
        val = float(re.sub(r"[,₹$]", "", m_cnt_gt.group(1)))
        return "COUNT(*)", op, val

    m_cnt_lt = re.search(r"\b(?:with\s+)?(?:less\s+than|fewer\s+than|below|<|at\s+most|<=|not\s+more\s+than|not\s+greater\s+than)\s+([0-9,]+)\s+students?\b", lowered)
    if m_cnt_lt:
        op = "<=" if any(w in m_cnt_lt.group(0) for w in ("most", "not more", "not greater")) else "<"
        val = float(re.sub(r"[,₹$]", "", m_cnt_lt.group(1)))
        return "COUNT(*)", op, val

    # 2. Having aggregate metric condition: "average salary exceeds ₹50,000", "average cgpa > 8"
    m_agg = re.search(
        r"\b(?:average|avg|mean)\s+(salary|cgpa|marks?|fee)\s+(?:exceeds?|greater\s+than|more\s+than|above|>|at\s+least|>=|is\s+over|not\s+less\s+than)\s+[₹$]?\s*([0-9,]+(?:\.[0-9]+)?)\b",
        lowered
    )
    if m_agg:
        metric = m_agg.group(1)
        if metric in ("mark", "marks"):
            metric = "marks"
        op = ">=" if any(w in m_agg.group(0) for w in ("least", "not less")) else ">"
        val = float(re.sub(r"[,₹$]", "", m_agg.group(2)))
        return f"AVG({metric})", op, val

    m_agg_lt = re.search(
        r"\b(?:average|avg|mean)\s+(salary|cgpa|marks?|fee)\s+(?:less\s+than|fewer\s+than|below|<|at\s+most|<=|under|not\s+more\s+than|not\s+greater\s+than)\s+[₹$]?\s*([0-9,]+(?:\.[0-9]+)?)\b",
        lowered
    )
    if m_agg_lt:
        metric = m_agg_lt.group(1)
        if metric in ("mark", "marks"):
            metric = "marks"
        op = "<=" if any(w in m_agg_lt.group(0) for w in ("most", "not more", "not greater")) else "<"
        val = float(re.sub(r"[,₹$]", "", m_agg_lt.group(2)))
        return f"AVG({metric})", op, val

    return None, None, None
