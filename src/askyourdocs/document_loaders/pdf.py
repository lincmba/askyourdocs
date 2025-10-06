"""
PDF document loader for AskYourDocs.

Handles PDF document parsing and text extraction using PyPDF.
"""

from pathlib import Path

from llama_index.core import Document
from llama_index.readers.file import PDFReader

from ..utils.logging import get_logger

logger = get_logger(__name__)


class PDFLoader:
    """Loader for PDF documents."""

    def __init__(self) -> None:
        self.reader = PDFReader()

    def load_data(self, file_path: Path) -> list[Document]:
        """Load and parse PDF document."""
        try:
            documents = self.reader.load_data(file_path)

            # Enrich with metadata
            for doc in documents:
                doc.metadata.update(
                    {
                        "source_type": "pdf",
                        "file_extension": ".pdf",
                        "loader": "PDFLoader",
                    }
                )

            logger.debug(f"Loaded PDF document: {file_path}")
            return documents

        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            raise RuntimeError(f"PDF loading failed: {e}")

    @staticmethod
    def can_handle(file_extension: str) -> bool:
        """Check if this loader can handle the file extension."""
        return file_extension.lower() == ".pdf"
