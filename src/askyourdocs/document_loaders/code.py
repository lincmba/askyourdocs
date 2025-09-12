"""
Code file loader for AskYourDocs.

Handles source code files in various programming languages,
extracting comments, docstrings, and code structure.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from llama_index.core import Document

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CodeLoader:
    """Loader for source code files."""

    def __init__(self) -> None:
        # Language-specific comment patterns
        self.comment_patterns = {
            "python": {
                "single": r"#.*$",
                "multi_start": r'"""',
                "multi_end": r'"""',
                "docstring": r'""".*?"""',
            },
            "javascript": {
                "single": r"//.*$",
                "multi_start": r"/\*",
                "multi_end": r"\*/",
            },
            "java": {
                "single": r"//.*$",
                "multi_start": r"/\*",
                "multi_end": r"\*/",
                "javadoc": r"/\*\*.*?\*/",
            },
            "cpp": {
                "single": r"//.*$",
                "multi_start": r"/\*",
                "multi_end": r"\*/",
            },
            "shell": {
                "single": r"#.*$",
            },
            "sql": {
                "single": r"--.*$",
                "multi_start": r"/\*",
                "multi_end": r"\*/",
            },
        }

        # File extension to language mapping
        self.extension_language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
            ".fish": "shell",
            ".sql": "sql",
            ".r": "r",
            ".m": "matlab",
            ".lua": "lua",
            ".pl": "perl",
            ".pm": "perl",
        }

    def load_data(self, file_path: Path) -> List[Document]:
        """Load and parse code file."""
        try:
            content = self._read_code_file(file_path)

            if not content.strip():
                logger.warning(f"Empty code file: {file_path}")
                return []

            # Detect language
            language = self._detect_language(file_path)

            # Extract different components
            components = self._extract_code_components(content, language)

            # Create enriched document content
            enriched_content = self._create_enriched_content(
                file_path, content, components, language
            )

            # Create document
            doc = Document(
                text=enriched_content,
                metadata={
                    "source_type": "code",
                    "file_extension": file_path.suffix.lower(),
                    "loader": "CodeLoader",
                    "language": language,
                    "line_count": content.count("\n") + 1,
                    "character_count": len(content),
                    "has_comments": len(components["comments"]) > 0,
                    "has_docstrings": len(components["docstrings"]) > 0,
                },
            )

            logger.debug(f"Loaded code file: {file_path}")
            return [doc]

        except Exception as e:
            logger.error(f"Failed to load code file {file_path}: {e}")
            raise RuntimeError(f"Code file loading failed: {e}")

    def _read_code_file(self, file_path: Path) -> str:
        """Read code file with encoding detection."""
        encodings = ["utf-8", "utf-16", "iso-8859-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Fallback to binary read with error handling
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return content.decode("utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"Failed to read code file {file_path}: {e}")

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        extension = file_path.suffix.lower()
        return self.extension_language_map.get(extension, "unknown")

    def _extract_code_components(
        self, content: str, language: str
    ) -> Dict[str, List[str]]:
        """Extract comments, docstrings, and other components."""
        components = {
            "comments": [],
            "docstrings": [],
            "functions": [],
            "classes": [],
            "imports": [],
        }

        try:
            if language in self.comment_patterns:
                patterns = self.comment_patterns[language]

                # Extract single-line comments
                if "single" in patterns:
                    comments = re.findall(patterns["single"], content, re.MULTILINE)
                    components["comments"].extend(
                        [c.strip("# ").strip() for c in comments]
                    )

                # Extract multi-line comments/docstrings
                if "docstring" in patterns:
                    docstrings = re.findall(patterns["docstring"], content, re.DOTALL)
                    components["docstrings"].extend(
                        [d.strip('"""').strip() for d in docstrings]
                    )
                elif "multi_start" in patterns and "multi_end" in patterns:
                    multi_pattern = (
                        f"{patterns['multi_start']}(.*?){patterns['multi_end']}"
                    )
                    multi_comments = re.findall(multi_pattern, content, re.DOTALL)
                    components["comments"].extend([c.strip() for c in multi_comments])

            # Language-specific extractions
            if language == "python":
                self._extract_python_components(content, components)
            elif language in ["javascript", "typescript"]:
                self._extract_js_components(content, components)
            elif language == "java":
                self._extract_java_components(content, components)

        except Exception as e:
            logger.warning(f"Failed to extract code components: {e}")

        return components

    def _extract_python_components(
        self, content: str, components: Dict[str, List[str]]
    ) -> None:
        """Extract Python-specific components."""
        # Functions
        func_pattern = r"def\s+(\w+)\s*\([^)]*\):"
        functions = re.findall(func_pattern, content)
        components["functions"].extend(functions)

        # Classes
        class_pattern = r"class\s+(\w+)(?:\([^)]*\))?:"
        classes = re.findall(class_pattern, content)
        components["classes"].extend(classes)

        # Imports
        import_pattern = r"(?:^from\s+[\w.]+\s+import\s+.+|^import\s+[\w.]+)"
        imports = re.findall(import_pattern, content, re.MULTILINE)
        components["imports"].extend(imports)

    def _extract_js_components(
        self, content: str, components: Dict[str, List[str]]
    ) -> None:
        """Extract JavaScript/TypeScript components."""
        # Functions
        func_patterns = [
            r"function\s+(\w+)\s*\(",
            r"const\s+(\w+)\s*=\s*(?:async\s+)?\(",
            r"(\w+)\s*:\s*(?:async\s+)?function",
        ]

        for pattern in func_patterns:
            functions = re.findall(pattern, content)
            components["functions"].extend(functions)

        # Classes
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+\w+)?"
        classes = re.findall(class_pattern, content)
        components["classes"].extend(classes)

        # Imports
        import_patterns = [
            r'import\s+.*?\s+from\s+["\']([^"\']+)["\']',
            r'const\s+.*?\s+=\s+require\(["\']([^"\']+)["\']\)',
        ]

        for pattern in import_patterns:
            imports = re.findall(pattern, content)
            components["imports"].extend(imports)

    def _extract_java_components(
        self, content: str, components: Dict[str, List[str]]
    ) -> None:
        """Extract Java-specific components."""
        # Methods
        method_pattern = (
            r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)"
        )
        methods = re.findall(method_pattern, content)
        components["functions"].extend(methods)

        # Classes
        class_pattern = r"(?:public|private)?\s*class\s+(\w+)"
        classes = re.findall(class_pattern, content)
        components["classes"].extend(classes)

        # Imports
        import_pattern = r"import\s+([\w.]+);"
        imports = re.findall(import_pattern, content)
        components["imports"].extend(imports)

    def _create_enriched_content(
        self,
        file_path: Path,
        content: str,
        components: Dict[str, List[str]],
        language: str,
    ) -> str:
        """Create enriched content with metadata and structure."""
        lines = [
            f"File: {file_path.name}",
            f"Language: {language}",
            f"Path: {file_path}",
            "",
        ]

        # Add component summaries
        if components["functions"]:
            lines.append(f"Functions: {', '.join(components['functions'][:10])}")

        if components["classes"]:
            lines.append(f"Classes: {', '.join(components['classes'][:10])}")

        if components["imports"]:
            lines.append(f"Dependencies: {', '.join(components['imports'][:10])}")

        if components["comments"]:
            lines.append(f"Comments: {len(components['comments'])} found")

        lines.extend(["", "=" * 50, "", content])

        # Add extracted comments and docstrings at the end for searchability
        if components["docstrings"]:
            lines.extend(["", "=== DOCUMENTATION ===", ""])
            lines.extend(components["docstrings"])

        if components["comments"]:
            lines.extend(["", "=== COMMENTS ===", ""])
            lines.extend(components["comments"])

        return "\n".join(lines)

    @staticmethod
    def can_handle(file_extension: str) -> bool:
        """Check if this loader can handle the file extension."""
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".swift",
            ".kt",
            ".scala",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".sql",
            ".r",
            ".m",
            ".lua",
            ".pl",
            ".pm",
        }
        return file_extension.lower() in code_extensions
