"""
AskYourDocs - Privacy-first, local-only document Q&A CLI tool.

A powerful CLI tool that transforms document collections into an intelligent
Q&A system using RAG (Retrieval Augmented Generation) technology.
"""

__version__ = "1.0.0"
__author__ = "AskYourDocs Team"
__email__ = "hello@askyourdocs.dev"
__description__ = "Privacy-first, local-only CLI tool for document Q&A"

from .core.config import Config, get_config
from .core.ingestion import DocumentIngestor
from .core.retrieval import QueryEngine
from .core.storage import VectorStoreManager

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "Config",
    "get_config",
    "DocumentIngestor",
    "QueryEngine",
    "VectorStoreManager",
]
