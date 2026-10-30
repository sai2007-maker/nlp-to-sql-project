"""
Intent classification module using NLP rules, semantic keyword signals, and regular expressions.
Directly implements the flowchart's 6 intents + NO_MATCH fallback.
Understands flexible, natural English queries without requiring rigid template wording.
"""

import re
from .entity_extractor import (
    extract_department,
    extract_marks_filter,
    extract_range_filter,
    extract_student_name,
    extract_name_prefix,
    extract_target_table,
)

class Intent:
    LIST_STUDENTS = "LIST_STUDENTS"
    MARKS_FILTER = "MARKS_FILTER"
    TOP_N = "TOP_N"
    DEPARTMENT = "DEPARTMENT"
    AVERAGE_OR_COUNT = "AVERAGE_OR_COUNT"
    NAME_SEARCH = "NAME_SEARCH"
    NO_MATCH = "NO_MATCH"

def classify_intent(normalized_text: str):
    """
    Classifies the user query into one of the 7 predefined intents.
    Uses multi-stage semantic and entity signal detection.
    """
    text = normalized_text.strip()

    # 1. Check for Student Scoring / Earning Above/Below Average Subqueries
    text_lower = text.lower()
    is_above_below_avg = bool(re.search(r"\b(?:scoring|scored|with\s+marks?|earning|who\s+scored)\s+(?:above|below|more\s+than|greater\s+than|less\s+than|exceeding)\s+(?:the\s+)?(?:average|avg|mean)\s+(?:marks?|scores?|cgpa|salary)\b", text_lower))
    if is_above_below_avg and "course" not in text_lower:
        return Intent.MARKS_FILTER

    # 2. Check for Average or Count (Aggregate Intent)
    # E.g. "what is the average marks", "avg score", "how many students", "count students", "calculate the total number of courses", "find the minimum and maximum course fees", "what is the highest mark obtained"
    is_min_max = bool(re.search(r"\b(?:min(?:imum)?\s+and\s+max(?:imum)?|max(?:imum)?\s+and\s+min(?:imum)?|lowest\s+and\s+highest|highest\s+and\s+lowest)\b", text_lower))
    is_std_agg = bool(re.search(r"\b(?:average|avg|mean|how many|total students|total courses|total count|how many in)\b", text_lower))
    is_count = bool(re.search(r"\b(?:count|counting|calculate\s+(?:the\s+)?total|total\s+number\s+of)\b", text_lower))
    is_dept_with_emp = bool(re.search(r"\bdepartments?\s+with\s+(?:its\s+|their\s+)?employees?\b", text_lower))
    is_group_by = bool(
        ((re.search(r"\b(?:in\s+each|for\s+each|each|per|by)\s+(?:branch(?:es)?|departments?|depts?|courses?|subjects?)\b", text_lower) or
          re.search(r"\b(?:branches|departments|depts)\s+(?:with|whose|having)\b", text_lower)) and
         not is_dept_with_emp)
    )
    is_having_clause = bool(
        (re.search(r"\b(?:with\s+)?(?:more\s+than|greater\s+than|less\s+than|fewer\s+than|exceeds?)\s+[₹$]?\s*[0-9,]+\s*(?:students?|salary|marks?|cgpa)?\b", text_lower) and
         re.search(r"\b(?:branches|departments|depts)\b", text_lower)) or
        re.search(r"\b(?:more\s+than|greater\s+than|>)\s+(?:one|\d+)\s+courses?\b", text_lower) or
        re.search(r"\bcourses?\s+with\s+more\s+enrollments?\s+than\s+(?:the\s+)?average\b", text_lower) or
        re.search(r"\bstudents?\s+enrolled\s+in\s+all\s+(?:available\s+)?courses?\b", text_lower)
    )
    is_ranking_request = bool(re.search(r"\b(?:who|which student|students?\s+with|top\s+\d+|\d+\s+top|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+students?)\b", text_lower))
    is_scalar_min_max = bool(re.search(r"\b(?:what\s+is\s+(?:the\s+)?(?:highest|lowest|maximum|max|minimum|min)\s+(?:marks?|cgpa|gpa|fees?|cost|price|credits?)|find\s+(?:the\s+)?(?:highest|lowest|maximum|max|minimum|min)\s+(?:marks?|cgpa|gpa|fees?|cost|price|credits?)|(?:highest|lowest|maximum|minimum)\s+(?:marks?|scores?|fees?)\s+obtained)\b", text_lower))

    if is_min_max or is_std_agg or is_count or is_group_by or is_having_clause or (is_scalar_min_max and not is_ranking_request):
        return Intent.AVERAGE_OR_COUNT

    # 3. Check for Top N Intent
    # E.g. "top 3 students", "who is the topper", "best 5 students", "highest marks", "five students with highest marks", "three cheapest courses"
    top_n_pattern = r"\b(?:top\s+\d+|\d+\s+top|top\s+students?|toppers?|highest\s+marks?|highest\s+\d+|best\s+\d+|best\s+students?|top\s+scorer|rank\s+1|number\s+1|cheapest|lowest\s+marks?|bottom\s+\d+|lowest\s+\d+|(?:the\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:students?|courses?|scorers?|toppers?|cheapest|best|highest|lowest)|(?:first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s*[- ]\s*(?:highest|best|topper|lowest|cheapest|maximum|minimum|cgpa|marks?))\b"
    if re.search(top_n_pattern, text):
        return Intent.TOP_N

    # 3. Check for Marks / Range Filter Intent
    # E.g. "marks greater than 80", "who scored above 85", "students with marks < 70", "between 70 and 90 marks"
    op, threshold = extract_marks_filter(text)
    if op is not None and threshold is not None:
        return Intent.MARKS_FILTER

    r_low, r_high = extract_range_filter(text)
    if r_low is not None and r_high is not None:
        return Intent.MARKS_FILTER

    # 4. Check for Student Name Search Intent
    # E.g. "show student vikram rathod", "who is priya", "names start with A", "search for aarav"
    prefix = extract_name_prefix(text)
    if prefix is not None:
        return Intent.NAME_SEARCH

    name = extract_student_name(text)
    if name is not None:
        dept = extract_department(text)
        # Ensure the extracted name is not just the department name itself
        if not dept or name.lower() != dept.lower():
            return Intent.NAME_SEARCH

    # 5. Check for Department Intent
    # E.g. "students in Computer Science", "who is in cse", "mechanical branch", "civil engineering students"
    dept = extract_department(text)
    if dept is not None:
        return Intent.DEPARTMENT

    # 6. Check for List Intent (Supports default students and custom tables)
    target_table = extract_target_table(text)
    if target_table != "students":
        return Intent.LIST_STUDENTS

    list_signals = [
        # Join queries: explicit table join / merging
        r"\b(?:join|joining|joined|combine|combining|combined|merge)\b.*?\b(?:students?|courses?|tables?)\b",
        r"\b(?:inner\s+join|left\s+join|join|joining|joined)\b",
        r"\bstudents?\s+and\s+courses?\b",
        r"\bcourses?\s+and\s+students?\b",
        # Retrieval verbs + student(s) / course(s) with any column specifications (e.g. "show the names and grade of students", "arrange students by cgpa")
        r"\b(?:list|show|display|view|get|give|print|fetch|tell|arrange|sort|order|find)\b.*?\b(?:students?|courses?|departments?|employees?)\b",
        r"\b(?:sort|arrange|order)\b.*?\b(?:by|alphabetical(?:ly)?)\b",
        # Unenrolled students queries
        r"\b(?:not\s+enrolled|unenrolled|without\s+(?:any\s+)?courses?|haven't\s+enrolled|have\s+not\s+enrolled|no\s+courses?)\b",
        # Specific projection phrases without verbs (e.g. "names and cgpa of students")
        r"\b(?:names?|cgpa|gpa|grades?|marks?|courses?|credits?|departments?)\b.*?\b(?:of\s+(?:all\s+)?(?:the\s+)?(?:students?|courses?))\b",
        r"\b(?:student|course)\s+(?:names?|cgpa|gpa|grades?|marks?|records?|data|details|list)\b",
        r"\b(?:all\s+students?|all\s+student\s+records?|student\s+list|student\s+records?|student\s+data|everyone|all\s+records?)\b",
        r"\b(?:who are the students|tell me about the students|give me the list of students|show the class)\b",
        r"^students?$"
    ]
    for pat in list_signals:
        if re.search(pat, text):
            return Intent.LIST_STUDENTS

    # 7. Fallback: No Match (Display unsupported question message)
    return Intent.NO_MATCH
