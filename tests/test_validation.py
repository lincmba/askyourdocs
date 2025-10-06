"""Tests for validation utilities."""


from askyourdocs.utils.validation import (
    is_safe_filename,
    sanitize_input,
    validate_chunk_size,
    validate_question,
    validate_similarity_threshold,
    validate_top_k,
)


class TestValidation:
    """Test validation functions."""

    def test_validate_question(self):
        """Test question validation."""
        # Valid questions
        valid, _ = validate_question("What is the main topic?")
        assert valid is True

        valid, _ = validate_question("How does authentication work in the system?")
        assert valid is True

        # Invalid questions
        valid, error = validate_question("")
        assert valid is False
        assert "empty" in error.lower()

        valid, error = validate_question("Hi")
        assert valid is False
        assert "too short" in error.lower()

        valid, error = validate_question("?" * 10)
        assert valid is False
        assert "question marks" in error.lower()

        # Potentially harmful content
        valid, error = validate_question("<script>alert('xss')</script>")
        assert valid is False
        assert "harmful" in error.lower()

    def test_sanitize_input(self):
        """Test input sanitization."""
        # Normal text
        result = sanitize_input("This is normal text.")
        assert result == "This is normal text."

        # Text with extra whitespace
        result = sanitize_input("  Multiple   spaces   ")
        assert result == "Multiple spaces"

        # Text with control characters
        result = sanitize_input("Text\x00with\x01control\x02chars")
        assert "Text" in result
        assert "\x00" not in result

        # Long text truncation
        long_text = "word " * 300
        result = sanitize_input(long_text, max_length=50)
        assert len(result) <= 53  # Accounting for "..."
        assert result.endswith("...")

    def test_validate_chunk_size(self):
        """Test chunk size validation."""
        # Valid sizes
        valid, _ = validate_chunk_size(1000)
        assert valid is True

        valid, _ = validate_chunk_size(500)
        assert valid is True

        # Invalid sizes
        valid, error = validate_chunk_size(0)
        assert valid is False
        assert "positive" in error.lower()

        valid, error = validate_chunk_size(50)
        assert valid is False
        assert "too small" in error.lower()

        valid, error = validate_chunk_size(10000)
        assert valid is False
        assert "too large" in error.lower()

    def test_validate_top_k(self):
        """Test top_k validation."""
        # Valid values
        valid, _ = validate_top_k(5)
        assert valid is True

        valid, _ = validate_top_k(10)
        assert valid is True

        # Invalid values
        valid, error = validate_top_k(0)
        assert valid is False
        assert "positive" in error.lower()

        valid, error = validate_top_k(-5)
        assert valid is False
        assert "positive" in error.lower()

        valid, error = validate_top_k(100)
        assert valid is False
        assert "too large" in error.lower()

    def test_validate_similarity_threshold(self):
        """Test similarity threshold validation."""
        # Valid thresholds
        valid, _ = validate_similarity_threshold(0.5)
        assert valid is True

        valid, _ = validate_similarity_threshold(0.0)
        assert valid is True

        valid, _ = validate_similarity_threshold(1.0)
        assert valid is True

        # Invalid thresholds
        valid, error = validate_similarity_threshold(-0.1)
        assert valid is False
        assert "between 0.0 and 1.0" in error

        valid, error = validate_similarity_threshold(1.5)
        assert valid is False
        assert "between 0.0 and 1.0" in error

    def test_is_safe_filename(self):
        """Test filename safety validation."""
        # Safe filenames
        assert is_safe_filename("document.pdf") is True
        assert is_safe_filename("my-file_v2.txt") is True
        assert is_safe_filename("report.docx") is True

        # Unsafe filenames
        assert is_safe_filename("../etc/passwd") is False
        assert is_safe_filename("dir/file.txt") is False
        assert is_safe_filename("CON") is False  # Windows reserved (exact match)
        assert is_safe_filename("file<test>.txt") is False
        assert is_safe_filename("") is False
        assert is_safe_filename(".") is False
        assert is_safe_filename("..") is False
