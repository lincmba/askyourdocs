"""
Document ingestion pipeline for AskYourDocs.

Handles document processing, chunking, embedding generation,
and incremental updates with change detection.
"""

import time
from pathlib import Path
from typing import List, Optional, Set

from llama_index.core import Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config
from .storage import VectorStoreManager
from ..document_loaders import get_document_loader
from ..utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


class DocumentChangeHandler(FileSystemEventHandler):
    """Handle file system events for automatic ingestion."""

    def __init__(self, ingestor: 'DocumentIngestor') -> None:
        self.ingestor = ingestor
        self.debounce_time = 2.0  # seconds
        self.pending_files: Set[Path] = set()
        self.last_event_time = 0.0

    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if self.ingestor._should_process_file(file_path):
            self.pending_files.add(file_path)
            self.last_event_time = time.time()

            # Process after debounce period
            self._schedule_processing()

    def on_created(self, event) -> None:
        """Handle file creation events."""
        self.on_modified(event)

    def _schedule_processing(self) -> None:
        """Schedule processing of pending files after debounce."""
        # This is a simplified debouncing mechanism
        # In production, you might want to use threading.Timer
        current_time = time.time()
        if current_time - self.last_event_time >= self.debounce_time:
            if self.pending_files:
                console.print(f"📁 [yellow]Processing {len(self.pending_files)} changed files...[/yellow]")
                self.ingestor._process_files(list(self.pending_files))
                self.pending_files.clear()


class DocumentIngestor:
    """Handles document ingestion and processing pipeline."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.storage_manager = VectorStoreManager(config)

        # Setup LlamaIndex settings before any processing
        self._setup_llamaindex()

        self.node_parser = self._create_node_parser()

        # Supported file extensions
        self.supported_extensions = {
            ".pdf", ".docx", ".pptx", ".odt", ".odp", ".rtf",
            ".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml",
            ".html", ".xml", ".tex", ".py", ".js", ".java", ".cpp",
            ".c", ".h", ".go", ".rs", ".php", ".rb", ".swift", ".kt"
        }

    def _setup_llamaindex(self) -> None:
        """Configure LlamaIndex global settings for ingestion."""
        try:
            # Configure embeddings based on provider
            if self.config.embedding.provider == "huggingface":
                embed_model = HuggingFaceEmbedding(
                    model_name=self.config.embedding.model,
                    device=self.config.embedding.device,
                    max_length=self.config.embedding.max_length,
                )
            elif self.config.embedding.provider == "openai":
                if not self.config.embedding.api_key:
                    raise ValueError("OpenAI API key required for OpenAI embeddings")
                embed_model = OpenAIEmbedding(
                    model=self.config.embedding.model,
                    api_key=self.config.embedding.api_key,
                    api_base=self.config.embedding.api_base,
                )
            else:
                # Default to HuggingFace
                embed_model = HuggingFaceEmbedding(
                    model_name=self.config.embedding.model,
                    device=self.config.embedding.device,
                    max_length=self.config.embedding.max_length,
                )

            Settings.embed_model = embed_model

            # Configure chunking
            Settings.chunk_size = self.config.chunking.chunk_size
            Settings.chunk_overlap = self.config.chunking.chunk_overlap

            logger.info("LlamaIndex configuration completed for ingestion")

        except Exception as e:
            logger.error(f"Failed to setup LlamaIndex: {e}")
            raise RuntimeError(f"LlamaIndex setup failed: {e}")

    def _create_node_parser(self) -> SentenceSplitter:
        """Create node parser based on configuration."""
        return SentenceSplitter(
            chunk_size=self.config.chunking.chunk_size,
            chunk_overlap=self.config.chunking.chunk_overlap,
            separator=" ",
            paragraph_separator="\n\n",
            secondary_chunking_regex="[.!?]+",
        )

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        if file_path.suffix.lower() not in self.supported_extensions:
            return False

        if file_path.name.startswith("."):
            return False

        # Skip common non-document files
        skip_patterns = {
            "__pycache__", ".git", ".svn", ".hg", "node_modules",
            ".DS_Store", "Thumbs.db", ".env", ".log"
        }

        for pattern in skip_patterns:
            if pattern in str(file_path):
                return False

        return True

    def _filter_files(
        self,
        files: List[Path],
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Path]:
        """Filter files based on include/exclude patterns."""
        filtered_files = []

        for file_path in files:
            # Apply include patterns
            if include_patterns:
                included = False
                for pattern in include_patterns:
                    if file_path.match(pattern.strip()):
                        included = True
                        break
                if not included:
                    continue

            # Apply exclude patterns
            if exclude_patterns:
                excluded = False
                for pattern in exclude_patterns:
                    if file_path.match(pattern.strip()):
                        excluded = True
                        break
                if excluded:
                    continue

            if self._should_process_file(file_path):
                filtered_files.append(file_path)

        return filtered_files

    def _discover_files(self, directory: Path) -> List[Path]:
        """Discover all processable files in directory."""
        files = []

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file() and self._should_process_file(file_path):
                    files.append(file_path)

        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory}: {e}")

        return files

    def _load_document(self, file_path: Path) -> Optional[Document]:
        """Load and parse a single document."""
        try:
            loader = get_document_loader(file_path.suffix.lower())
            if not loader:
                logger.warning(f"No loader available for {file_path.suffix}")
                return None

            documents = loader().load_data(file_path)
            if not documents:
                logger.warning(f"No content extracted from {file_path}")
                return None

            # Use first document and enrich metadata
            doc = documents[0]
            doc.metadata.update({
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "file_type": file_path.suffix.lower(),
                "document_hash": self.storage_manager.get_document_hash(file_path),
                "ingestion_time": time.time(),
            })

            return doc

        except Exception as e:
            logger.error(f"Failed to load document {file_path}: {e}")
            return None

    def _process_files(self, file_paths: List[Path]) -> List[Document]:
        """Process multiple files with progress tracking."""
        documents = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task("Processing documents...", total=len(file_paths))

            for file_path in file_paths:
                progress.update(task, description=f"Processing {file_path.name}")

                doc = self._load_document(file_path)
                if doc:
                    documents.append(doc)

                progress.advance(task)

        logger.info(f"Successfully processed {len(documents)}/{len(file_paths)} files")
        return documents

    def ingest_directory(
        self,
        path: Path,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        force_rebuild: bool = False
    ) -> None:
        """Ingest documents from a directory or single file."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Handle single file
        if path.is_file():
            if self._should_process_file(path):
                console.print(f"📄 [bold]Processing single file:[/bold] {path}")
                files_to_process = [path]
            else:
                console.print(f"⚠️  [yellow]File type not supported: {path.suffix}[/yellow]")
                return
        else:
            # Handle directory
            console.print(f"📁 [bold]Scanning directory:[/bold] {path}")

            # Discover files
            all_files = self._discover_files(path)
            files_to_process = self._filter_files(all_files, include_patterns, exclude_patterns)

        if not files_to_process:
            console.print("⚠️  [yellow]No supported documents found[/yellow]")
            return

        console.print(f"📄 Found {len(files_to_process)} documents to process")

        # Filter for incremental processing
        if not force_rebuild:
            new_files = []
            for file_path in files_to_process:
                if not self.storage_manager.is_document_indexed(file_path):
                    new_files.append(file_path)
            files_to_process = new_files

            if not files_to_process:
                console.print("✅ [green]All documents are already indexed[/green]")
                return

        console.print(f"⚡ Processing {len(files_to_process)} {'new ' if not force_rebuild else ''}documents")

        # Process documents
        documents = self._process_files(files_to_process)

        if not documents:
            console.print("⚠️  [yellow]No documents were successfully processed[/yellow]")
            return

        # Create or update index
        with console.status("[bold blue]Building vector index..."):
            existing_index = self.storage_manager.get_index()

            if existing_index and not force_rebuild:
                self.storage_manager.add_documents(documents)
            else:
                # Include existing documents if force rebuild
                if force_rebuild and existing_index:
                    # This is a simplified approach - in production you might
                    # want to re-process existing documents too
                    pass

                self.storage_manager.create_index(documents)

        # Track ingested path
        self.storage_manager.add_ingested_path(path)

        console.print(f"🎉 [bold green]Successfully indexed {len(documents)} documents![/bold green]")

    def refresh_index(self) -> None:
        """Refresh index with incremental updates."""
        # For now, this is a placeholder for incremental refresh logic
        # In a full implementation, this would:
        # 1. Check for modified files
        # 2. Remove outdated documents from index
        # 3. Re-process changed files
        # 4. Update index efficiently

        console.print("🔄 [blue]Incremental refresh not yet implemented[/blue]")
        console.print("💡 Use [bold]askyourdocs ingest --force[/bold] to rebuild the index")

    def watch_directory(
        self,
        directory: Path,
        include_patterns: Optional[str] = None,
        exclude_patterns: Optional[str] = None
    ) -> None:
        """Watch directory for changes and auto-ingest."""
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Initial ingestion
        include_list = include_patterns.split(",") if include_patterns else None
        exclude_list = exclude_patterns.split(",") if exclude_patterns else None

        self.ingest_directory(directory, include_list, exclude_list)

        # Set up file watcher
        event_handler = DocumentChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(directory), recursive=True)

        try:
            observer.start()
            console.print(f"👀 [bold]Watching {directory} for changes...[/bold]")

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            observer.stop()
            console.print("\n🛑 [yellow]Stopped watching directory[/yellow]")

        observer.join()
