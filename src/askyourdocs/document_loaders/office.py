"""
Microsoft Office and OpenDocument loader for AskYourDocs.

Handles Word documents (.docx), PowerPoint presentations (.pptx),
OpenDocument formats (.odt, .odp), and RTF files.
"""

from pathlib import Path
from typing import List

from llama_index.core import Document
from llama_index.readers.file import DocxReader, PptxReader

from ..utils.logging import get_logger

logger = get_logger(__name__)


class OfficeLoader:
    """Loader for Office and OpenDocument formats."""

    def __init__(self) -> None:
        self.docx_reader = DocxReader()
        self.pptx_reader = PptxReader()

    def load_data(self, file_path: Path) -> List[Document]:
        """Load and parse Office document."""
        try:
            file_extension = file_path.suffix.lower()

            if file_extension in [".docx", ".odt"]:
                documents = self._load_word_document(file_path)
            elif file_extension in [".pptx", ".odp"]:
                documents = self._load_presentation(file_path)
            elif file_extension == ".rtf":
                documents = self._load_rtf_document(file_path)
            else:
                raise ValueError(f"Unsupported Office format: {file_extension}")

            # Enrich with metadata
            for doc in documents:
                doc.metadata.update(
                    {
                        "source_type": "office",
                        "file_extension": file_extension,
                        "loader": "OfficeLoader",
                    }
                )

            logger.debug(f"Loaded Office document: {file_path}")
            return documents

        except Exception as e:
            logger.error(f"Failed to load Office document {file_path}: {e}")
            raise RuntimeError(f"Office document loading failed: {e}")

    def _load_word_document(self, file_path: Path) -> List[Document]:
        """Load Word/ODT document."""
        try:
            if file_path.suffix.lower() == ".docx":
                return self.docx_reader.load_data(file_path)
            else:
                # For ODT, fall back to text extraction
                return self._extract_text_content(file_path)
        except Exception as e:
            logger.warning(f"Failed to load Word document with DocxReader: {e}")
            return self._extract_text_content(file_path)

    def _load_presentation(self, file_path: Path) -> List[Document]:
        """Load PowerPoint/ODP presentation."""
        try:
            if file_path.suffix.lower() == ".pptx":
                return self.pptx_reader.load_data(file_path)
            else:
                # For ODP, fall back to text extraction
                return self._extract_text_content(file_path)
        except Exception as e:
            logger.warning(f"Failed to load presentation with PptxReader: {e}")
            return self._extract_text_content(file_path)

    def _load_rtf_document(self, file_path: Path) -> List[Document]:
        """Load RTF document."""
        # RTF is a complex format, for now we'll try basic text extraction
        return self._extract_text_content(file_path)

    def _extract_text_content(self, file_path: Path) -> List[Document]:
        """Fallback text extraction for unsupported Office formats."""
        try:
            # This is a basic fallback - in production you might want
            # to use libraries like python-docx2txt, pypandoc, or textract
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if content.strip():
                doc = Document(
                    text=content,
                    metadata={
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                    },
                )
                return [doc]
            else:
                logger.warning(f"No text content found in {file_path}")
                return []

        except Exception as e:
            logger.error(f"Fallback text extraction failed for {file_path}: {e}")
            return []

    @staticmethod
    def can_handle(file_extension: str) -> bool:
        """Check if this loader can handle the file extension."""
        supported = [".docx", ".pptx", ".odt", ".odp", ".rtf"]
        return file_extension.lower() in supported
