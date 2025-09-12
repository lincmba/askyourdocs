"""Tests for document loaders."""

import tempfile
from pathlib import Path

import pytest

from askyourdocs.document_loaders import get_document_loader, get_supported_extensions
from askyourdocs.document_loaders.text import TextLoader
from askyourdocs.document_loaders.code import CodeLoader


class TestDocumentLoaders:
    """Test document loader functionality."""
    
    def test_get_document_loader(self):
        """Test getting appropriate loader for extensions."""
        # PDF loader
        pdf_loader = get_document_loader(".pdf")
        assert pdf_loader is not None
        
        # Text loader
        text_loader = get_document_loader(".txt")
        assert text_loader is not None
        
        # Code loader
        code_loader = get_document_loader(".py")
        assert code_loader is not None
        
        # Unsupported extension
        unknown_loader = get_document_loader(".unknown")
        assert unknown_loader is None
    
    def test_supported_extensions(self):
        """Test getting supported extensions."""
        extensions = get_supported_extensions()
        assert isinstance(extensions, list)
        assert len(extensions) > 0
        assert ".pdf" in extensions
        assert ".txt" in extensions
        assert ".py" in extensions


class TestTextLoader:
    """Test text document loader."""
    
    def test_load_text_file(self):
        """Test loading plain text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test document.\nIt has multiple lines.\n")
            temp_path = Path(f.name)
        
        try:
            loader = TextLoader()
            documents = loader.load_data(temp_path)
            
            assert len(documents) == 1
            doc = documents[0]
            assert "test document" in doc.text
            assert doc.metadata["source_type"] == "text"
            assert doc.metadata["file_extension"] == ".txt"
            
        finally:
            temp_path.unlink()
    
    def test_load_markdown_file(self):
        """Test loading Markdown file."""
        markdown_content = """
# Test Document

This is a **test** document with *emphasis*.

## Section 1

- Item 1
- Item 2

[Link](https://example.com)

```python
print("Hello world")
```
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            temp_path = Path(f.name)
        
        try:
            loader = TextLoader()
            documents = loader.load_data(temp_path)
            
            assert len(documents) == 1
            doc = documents[0]
            assert "Test Document" in doc.text
            assert doc.metadata["file_extension"] == ".md"
            
        finally:
            temp_path.unlink()
    
    def test_load_json_file(self):
        """Test loading JSON file."""
        json_content = """
{
    "name": "Test Project",
    "version": "1.0.0",
    "dependencies": {
        "library1": "^1.0.0",
        "library2": "^2.0.0"
    }
}
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            temp_path = Path(f.name)
        
        try:
            loader = TextLoader()
            documents = loader.load_data(temp_path)
            
            assert len(documents) == 1
            doc = documents[0]
            assert "Test Project" in doc.text
            assert "dependencies" in doc.text
            
        finally:
            temp_path.unlink()


class TestCodeLoader:
    """Test code document loader."""
    
    def test_load_python_file(self):
        """Test loading Python file."""
        python_content = '''
"""
This is a test Python module.
It demonstrates code loading functionality.
"""

import os
import sys
from typing import List

class TestClass:
    """A test class."""
    
    def __init__(self):
        self.value = 42
    
    def test_method(self, param: str) -> str:
        """Test method with docstring."""
        # This is a comment
        return f"Hello {param}"

def test_function(items: List[str]) -> None:
    """Test function."""
    for item in items:
        print(item)  # Print each item

# Main execution
if __name__ == "__main__":
    test_function(["item1", "item2"])
'''
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_content)
            temp_path = Path(f.name)
        
        try:
            loader = CodeLoader()
            documents = loader.load_data(temp_path)
            
            assert len(documents) == 1
            doc = documents[0]
            assert "TestClass" in doc.text
            assert "test_function" in doc.text
            assert doc.metadata["source_type"] == "code"
            assert doc.metadata["language"] == "python"
            assert doc.metadata["has_comments"] is True
            assert doc.metadata["has_docstrings"] is True
            
        finally:
            temp_path.unlink()
    
    def test_detect_language(self):
        """Test language detection from file extension."""
        loader = CodeLoader()
        
        assert loader._detect_language(Path("test.py")) == "python"
        assert loader._detect_language(Path("test.js")) == "javascript"
        assert loader._detect_language(Path("test.java")) == "java"
        assert loader._detect_language(Path("test.unknown")) == "unknown"
    
    def test_can_handle(self):
        """Test checking if loader can handle extensions."""
        assert CodeLoader.can_handle(".py") is True
        assert CodeLoader.can_handle(".js") is True
        assert CodeLoader.can_handle(".java") is True
        assert CodeLoader.can_handle(".txt") is False
        assert CodeLoader.can_handle(".pdf") is False