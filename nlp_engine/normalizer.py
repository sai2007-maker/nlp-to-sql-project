"""
Input normalization module using NLTK and regular expressions.
Follows the flowchart step:
'Normalize input: trim spaces and lowercase'
'Is the input empty?' -> 'Ask user to enter a question'
"""

import re

# NLTK integration for natural language tokenization
try:
    import nltk
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

def normalize_input(raw_text: str):
    """
    Normalizes the user question.
    Returns:
        (is_empty: bool, normalized_text: str)
    """
    if raw_text is None:
        return True, ""

    # Trim leading and trailing spaces
    trimmed = raw_text.strip()

    if not trimmed:
        return True, ""

    # Convert to lowercase
    lowered = trimmed.lower()

    # Collapse multiple spaces into a single space
    cleaned = re.sub(r"\s+", " ", lowered)

    # Remove trailing punctuation marks like '?', '.', '!'
    cleaned = re.sub(r"[?!.]+$", "", cleaned).strip()

    return False, cleaned

def get_tokens(text: str):
    """
    Tokenizes normalized input using NLTK word_tokenize (or regex fallback).
    """
    if NLTK_AVAILABLE:
        try:
            return word_tokenize(text)
        except Exception:
            return text.split()
    return text.split()
