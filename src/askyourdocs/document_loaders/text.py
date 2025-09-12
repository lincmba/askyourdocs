"""
Text document loader for AskYourDocs.

Handles plain text, Markdown, reStructuredText, CSV, JSON, YAML,
HTML, XML, LaTeX, and other text-based formats.
"""

import csv
import json
from pathlib import Path
from typing import List

import yaml
from llama_index.core import Document

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TextLoader:
    """Loader for text-based documents."""

    def __init__(self) -> None:
        self.encoding_fallbacks = ["utf-8", "utf-16", "iso-8859-1", "cp1252"]

    def load_data(self, file_path: Path) -> List[Document]:
        """Load and parse text document."""
        try:
            file_extension = file_path.suffix.lower()

            # Read file content with encoding detection
            content = self._read_file_content(file_path)

            if not content.strip():
                logger.warning(f"Empty content in {file_path}")
                return []

            # Process based on file type
            if file_extension == ".csv":
                content = self._process_csv(content)
            elif file_extension in [".json"]:
                content = self._process_json(content)
            elif file_extension in [".yaml", ".yml"]:
                content = self._process_yaml(content)
            elif file_extension in [".html", ".xml"]:
                content = self._process_markup(content)
            elif file_extension == ".md":
                content = self._process_markdown(content)

            # Create document
            doc = Document(
                text=content,
                metadata={
                    "source_type": "text",
                    "file_extension": file_extension,
                    "loader": "TextLoader",
                    "character_count": len(content),
                    "line_count": content.count("\n") + 1,
                },
            )

            logger.debug(f"Loaded text document: {file_path}")
            return [doc]

        except Exception as e:
            logger.error(f"Failed to load text document {file_path}: {e}")
            raise RuntimeError(f"Text document loading failed: {e}")

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content with encoding detection."""
        for encoding in self.encoding_fallbacks:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # If all encodings fail, read as binary and decode with errors
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return content.decode("utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {e}")

    def _process_csv(self, content: str) -> str:
        """Process CSV content into readable text."""
        try:
            lines = content.strip().split("\n")
            reader = csv.reader(lines)

            processed_lines = []
            headers = None

            for i, row in enumerate(reader):
                if i == 0:
                    headers = row
                    processed_lines.append("Headers: " + ", ".join(row))
                    processed_lines.append("-" * 40)
                else:
                    if headers and len(row) == len(headers):
                        row_text = []
                        for header, value in zip(headers, row):
                            if value.strip():
                                row_text.append(f"{header}: {value}")
                        if row_text:
                            processed_lines.append(" | ".join(row_text))
                    else:
                        processed_lines.append(", ".join(row))

            return "\n".join(processed_lines)

        except Exception as e:
            logger.warning(f"Failed to process CSV: {e}")
            return content

    def _process_json(self, content: str) -> str:
        """Process JSON content into readable text."""
        try:
            data = json.loads(content)

            # Convert to readable format
            if isinstance(data, dict):
                return self._dict_to_text(data)
            elif isinstance(data, list):
                return self._list_to_text(data)
            else:
                return str(data)

        except Exception as e:
            logger.warning(f"Failed to process JSON: {e}")
            return content

    def _process_yaml(self, content: str) -> str:
        """Process YAML content into readable text."""
        try:
            data = yaml.safe_load(content)

            if isinstance(data, dict):
                return self._dict_to_text(data)
            elif isinstance(data, list):
                return self._list_to_text(data)
            else:
                return str(data)

        except Exception as e:
            logger.warning(f"Failed to process YAML: {e}")
            return content

    def _process_markup(self, content: str) -> str:
        """Process HTML/XML content by removing tags."""
        try:
            # Simple tag removal - in production you might use BeautifulSoup
            import re

            # Remove HTML/XML tags
            content = re.sub(r"<[^>]+>", "", content)
            # Clean up whitespace
            content = re.sub(r"\s+", " ", content)
            return content.strip()
        except Exception as e:
            logger.warning(f"Failed to process markup: {e}")
            return content

    def _process_markdown(self, content: str) -> str:
        """Process Markdown content."""
        try:
            # Remove Markdown syntax for cleaner text
            import re

            # Remove headers
            content = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
            # Remove bold/italic
            content = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", content)
            content = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", content)
            # Remove links but keep text
            content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
            # Remove code blocks
            content = re.sub(r"```[^`]*```", "", content, flags=re.DOTALL)
            content = re.sub(r"`([^`]+)`", r"\1", content)

            return content.strip()

        except Exception as e:
            logger.warning(f"Failed to process Markdown: {e}")
            return content

    def _dict_to_text(self, data: dict, prefix: str = "") -> str:
        """Convert dictionary to readable text."""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._dict_to_text(value, prefix + "  "))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                lines.append(self._list_to_text(value, prefix + "  "))
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)

    def _list_to_text(self, data: list, prefix: str = "") -> str:
        """Convert list to readable text."""
        lines = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                lines.append(f"{prefix}Item {i + 1}:")
                lines.append(self._dict_to_text(item, prefix + "  "))
            elif isinstance(item, list):
                lines.append(f"{prefix}Item {i + 1}:")
                lines.append(self._list_to_text(item, prefix + "  "))
            else:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)

    @staticmethod
    def can_handle(file_extension: str) -> bool:
        """Check if this loader can handle the file extension."""
        supported = [
            ".txt",
            ".md",
            ".rst",
            ".csv",
            ".json",
            ".yaml",
            ".yml",
            ".html",
            ".xml",
            ".tex",
        ]
        return file_extension.lower() in supported
