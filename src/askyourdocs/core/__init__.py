"""
Core functionality for AskYourDocs.

This module contains the main components for document ingestion,
retrieval, storage management, and configuration.
"""

from .config import Config, ConfigManager, get_config
from .ingestion import DocumentIngestor
from .retrieval import QueryEngine
from .storage import VectorStoreManager

__all__ = [
    "Config",
    "get_config",
    "ConfigManager",
    "DocumentIngestor",
    "QueryEngine",
    "VectorStoreManager",
]
