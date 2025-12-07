"""
LaTeX Validation Service using pylatexenc.

Validates LaTeX expressions in question text and options.
"""
import re
from typing import Tuple, List, Optional
from pylatexenc.latexwalker import LatexWalker, LatexWalkerError


def extract_latex_expressions(text: str) -> List[str]:
    """
    Extract all LaTeX expressions from text.
    
    Supports:
    - Inline: $...$ or \\(...\\)
    - Display: $$...$$ or \\[...\\]
    """
    expressions = []
    
    # Match $$...$$ (display math)
    display_pattern = r'\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]'
    for match in re.finditer(display_pattern, text):
        latex = match.group(1) or match.group(2)
        if latex:
            expressions.append(latex.strip())
    
    # Match $...$ (inline math) - but not $$
    # First remove $$...$$ to avoid matching
    text_without_display = re.sub(display_pattern, '', text)
    inline_pattern = r'\$([^\$]+?)\$|\\\(([^\)]+?)\\\)'
    for match in re.finditer(inline_pattern, text_without_display):
        latex = match.group(1) or match.group(2)
        if latex:
            expressions.append(latex.strip())
    
    return expressions


def validate_latex(latex_expr: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single LaTeX expression using pylatexenc.
    
    Args:
        latex_expr: LaTeX expression (without $ delimiters)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check for unbalanced braces first
        open_braces = latex_expr.count('{')
        close_braces = latex_expr.count('}')
        if open_braces != close_braces:
            return False, f"Unbalanced braces: {open_braces} opening and {close_braces} closing"
        
        # Check for unbalanced parentheses in commands like \left( \right)
        if r'\left' in latex_expr or r'\right' in latex_expr:
            left_count = latex_expr.count(r'\left')
            right_count = latex_expr.count(r'\right')
            if left_count != right_count:
                return False, f"Unbalanced \\left/\\right: {left_count} \\left and {right_count} \\right"
        
        # LatexWalker parses LaTeX and will raise error on invalid syntax
        walker = LatexWalker(latex_expr)
        nodes, pos, len_ = walker.get_latex_nodes()
        return True, None
    except LatexWalkerError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def validate_text_latex(text: str) -> Tuple[bool, List[str]]:
    """
    Validate all LaTeX expressions in a text.
    
    Args:
        text: Text potentially containing LaTeX expressions
        
    Returns:
        Tuple of (all_valid, list_of_errors)
    """
    if not text:
        return True, []
    
    expressions = extract_latex_expressions(text)
    
    if not expressions:
        # No LaTeX found, that's fine
        return True, []
    
    errors = []
    for expr in expressions:
        is_valid, error = validate_latex(expr)
        if not is_valid:
            errors.append(f"Invalid LaTeX '${expr}$': {error}")
    
    return len(errors) == 0, errors


def validate_question_latex(question_dict: dict) -> Tuple[bool, List[str]]:
    """
    Validate all LaTeX in a question (text and options).
    
    Args:
        question_dict: Question dictionary with 'text' and 'options'
        
    Returns:
        Tuple of (all_valid, list_of_errors)
    """
    all_errors = []
    
    # Validate question text
    text = question_dict.get('text', '')
    is_valid, errors = validate_text_latex(text)
    if not is_valid:
        all_errors.extend([f"[Question text] {e}" for e in errors])
    
    # Validate options
    options = question_dict.get('options', [])
    for i, opt in enumerate(options):
        if isinstance(opt, str):
            is_valid, errors = validate_text_latex(opt)
            if not is_valid:
                all_errors.extend([f"[Option {i+1}] {e}" for e in errors])
    
    # Validate correct_answers for fill_in_blanks
    correct_answers = question_dict.get('correct_answers', [])
    for i, ans in enumerate(correct_answers):
        if isinstance(ans, str):
            is_valid, errors = validate_text_latex(ans)
            if not is_valid:
                all_errors.extend([f"[Answer {i+1}] {e}" for e in errors])
    
    return len(all_errors) == 0, all_errors
