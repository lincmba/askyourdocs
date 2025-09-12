"""
Document loaders for various file formats.

Provides unified interface for loading different document types
including PDF, Office documents, text files, and code files.
"""

from pathlib import Path
from typing import Optional, Type

from .code import CodeLoader
from .office import OfficeLoader
from .pdf import PDFLoader
from .text import TextLoader

# Mapping of file extensions to loader classes
LOADER_MAPPING = {
    # PDF documents
    ".pdf": PDFLoader,
    # Office documents
    ".docx": OfficeLoader,
    ".pptx": OfficeLoader,
    ".odt": OfficeLoader,
    ".odp": OfficeLoader,
    ".rtf": OfficeLoader,
    # Text documents
    ".txt": TextLoader,
    ".md": TextLoader,
    ".rst": TextLoader,
    ".csv": TextLoader,
    ".json": TextLoader,
    ".yaml": TextLoader,
    ".yml": TextLoader,
    ".html": TextLoader,
    ".xml": TextLoader,
    ".tex": TextLoader,
    # Code files
    ".py": CodeLoader,
    ".js": CodeLoader,
    ".ts": CodeLoader,
    ".jsx": CodeLoader,
    ".tsx": CodeLoader,
    ".java": CodeLoader,
    ".cpp": CodeLoader,
    ".c": CodeLoader,
    ".h": CodeLoader,
    ".hpp": CodeLoader,
    ".go": CodeLoader,
    ".rs": CodeLoader,
    ".php": CodeLoader,
    ".rb": CodeLoader,
    ".swift": CodeLoader,
    ".kt": CodeLoader,
    ".scala": CodeLoader,
    ".sh": CodeLoader,
    ".bash": CodeLoader,
    ".zsh": CodeLoader,
    ".fish": CodeLoader,
    ".sql": CodeLoader,
    ".r": CodeLoader,
    ".m": CodeLoader,
    ".lua": CodeLoader,
    ".pl": CodeLoader,
    ".pm": CodeLoader,
}


def get_document_loader(file_extension: str) -> Optional[Type]:
    """Get appropriate document loader for file extension."""
    loader_class = LOADER_MAPPING.get(file_extension.lower())
    return loader_class


def get_supported_extensions() -> list[str]:
    """Get list of all supported file extensions."""
    return list(LOADER_MAPPING.keys())


__all__ = [
    "PDFLoader",
    "OfficeLoader",
    "TextLoader",
    "CodeLoader",
    "get_document_loader",
    "get_supported_extensions",
    "LOADER_MAPPING",
]
