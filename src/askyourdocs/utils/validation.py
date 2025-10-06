"""
Input validation utilities for AskYourDocs.

Provides validation functions for file paths, user input,
and security-related checks.
"""

import re
from pathlib import Path
from typing import Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


def validate_file_path(file_path: str, must_exist: bool = True) -> tuple[bool, str]:
    """
    Validate file path for security and existence.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = Path(file_path).resolve()

        # Security checks
        if ".." in str(path):
            return False, "Path traversal not allowed"

        if str(path).startswith("/proc") or str(path).startswith("/sys"):
            return False, "System directory access not allowed"

        # Existence check
        if must_exist and not path.exists():
            return False, f"Path does not exist: {path}"

        # Permission check
        if must_exist and not path.is_readable():
            return False, f"Path is not readable: {path}"

        return True, ""

    except Exception as e:
        return False, f"Invalid path: {e}"


def validate_question(question: str) -> tuple[bool, str]:
    """
    Validate user question for basic safety and quality.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not question or not question.strip():
        return False, "Question cannot be empty"

    question = question.strip()

    # Length checks
    if len(question) < 3:
        return False, "Question too short (minimum 3 characters)"

    if len(question) > 1000:
        return False, "Question too long (maximum 1000 characters)"

    # Basic content checks
    if question.count("?") > 5:
        return False, "Too many question marks"

    # Check for potentially harmful patterns
    harmful_patterns = [
        r"<script",
        r"javascript:",
        r"data:text/html",
        r"eval\s*\(",
        r"exec\s*\(",
    ]

    for pattern in harmful_patterns:
        if re.search(pattern, question, re.IGNORECASE):
            return False, "Question contains potentially harmful content"

    return True, ""


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing harmful content and limiting length.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes and control characters
    text = text.replace("\x00", "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text.strip())

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "..."

    return text


def validate_file_patterns(patterns: Optional[str]) -> tuple[bool, list[str], str]:
    """
    Validate and parse file include/exclude patterns.

    Returns:
        Tuple of (is_valid, parsed_patterns, error_message)
    """
    if not patterns:
        return True, [], ""

    try:
        pattern_list = [p.strip() for p in patterns.split(",")]

        # Basic validation of glob patterns
        valid_patterns = []
        for pattern in pattern_list:
            if not pattern:
                continue

            # Check for suspicious patterns
            if ".." in pattern:
                return False, [], "Path traversal not allowed in patterns"

            # Check for basic glob validity
            if pattern.startswith("/"):
                return False, [], "Absolute paths not allowed in patterns"

            valid_patterns.append(pattern)

        return True, valid_patterns, ""

    except Exception as e:
        return False, [], f"Invalid pattern format: {e}"


def validate_chunk_size(chunk_size: int) -> tuple[bool, str]:
    """
    Validate chunk size parameter.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if chunk_size <= 0:
        return False, "Chunk size must be positive"

    if chunk_size < 100:
        return False, "Chunk size too small (minimum 100 characters)"

    if chunk_size > 8000:
        return False, "Chunk size too large (maximum 8000 characters)"

    return True, ""


def validate_top_k(top_k: int) -> tuple[bool, str]:
    """
    Validate top_k parameter for retrieval.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if top_k <= 0:
        return False, "top_k must be positive"

    if top_k > 50:
        return False, "top_k too large (maximum 50)"

    return True, ""


def validate_similarity_threshold(threshold: float) -> tuple[bool, str]:
    """
    Validate similarity threshold parameter.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not 0.0 <= threshold <= 1.0:
        return False, "Similarity threshold must be between 0.0 and 1.0"

    return True, ""


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal, special chars)."""
    if not filename or filename in [".", ".."]:
        return False

    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False

    # Check for reserved names (Windows)
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    if filename.upper() in reserved_names:
        return False

    # Check for invalid characters
    invalid_chars = '<>:"|?*\x00'
    if any(char in filename for char in invalid_chars):
        return False

    return True


def get_safe_path(base_path: Path, relative_path: str) -> Optional[Path]:
    """
    Get safe resolved path that stays within base directory.

    Args:
        base_path: Base directory path
        relative_path: Relative path to resolve

    Returns:
        Safe resolved path or None if unsafe
    """
    try:
        base_path = base_path.resolve()
        target_path = (base_path / relative_path).resolve()

        # Ensure target is within base directory
        if base_path in target_path.parents or target_path == base_path:
            return target_path
        else:
            logger.warning(f"Unsafe path access attempted: {relative_path}")
            return None

    except Exception as e:
        logger.error(f"Path resolution failed: {e}")
        return None
