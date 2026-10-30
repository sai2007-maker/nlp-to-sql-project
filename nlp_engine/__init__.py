"""
NLP Engine package initialization.
Provides a unified pipeline function parse_query(question)
implementing the flowchart's NLP stages.
"""

from .normalizer import normalize_input
from .intent_classifier import classify_intent, Intent
from .entity_extractor import (
    extract_department,
    extract_marks_filter,
    extract_top_n,
    extract_student_name,
    extract_aggregate_type,
)
from .sql_templates import generate_sql

def parse_query(raw_text: str):
    """
    Executes the NLP pipeline on user input:
    1. Trims spaces & lowercases
    2. Checks for empty input
    3. Identifies intent using rules & regex
    4. Extracts entities
    5. Selects predefined SQL template with parameters
    """
    is_empty, normalized_text = normalize_input(raw_text)

    if is_empty:
        return {
            "status": "empty",
            "message": "Input is empty. Please enter an English question.",
            "intent": None,
            "sql": None,
            "params": None,
            "entities": {}
        }

    intent = classify_intent(normalized_text)

    if intent == Intent.NO_MATCH:
        return {
            "status": "unsupported",
            "message": "Unsupported question. I can answer questions about listing students, filtering by marks, finding top students, filtering by department, computing averages or counts, and searching by student name.",
            "intent": Intent.NO_MATCH,
            "normalized_query": normalized_text,
            "sql": None,
            "params": None,
            "entities": {}
        }

    sql, params, desc, entities = generate_sql(intent, normalized_text)

    return {
        "status": "success",
        "intent": intent,
        "normalized_query": normalized_text,
        "sql": sql,
        "params": params,
        "description": desc,
        "entities": entities
    }
