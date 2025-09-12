"""
Vector storage management for AskYourDocs.

Handles ChromaDB integration, index management, persistence,
and data export/import functionality.
"""

import hashlib
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from rich.console import Console

from .config import Config
from ..utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


class VectorStoreManager:
    """Manages vector storage operations and ChromaDB integration."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.storage_path = self._resolve_storage_path()
        self.collection_name = config.storage.collection_name

        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._vector_store: Optional[ChromaVectorStore] = None
        self._index: Optional[VectorStoreIndex] = None

    def _resolve_storage_path(self) -> Path:
        """Resolve storage path with smart discovery."""
        storage_path = self.config.storage.path

        # If relative path, try smart discovery
        if not Path(storage_path).is_absolute():
            # Check current directory first
            current_path = Path.cwd() / storage_path
            if current_path.exists():
                return current_path

            # Check parent directories
            for parent in Path.cwd().parents:
                parent_path = parent / storage_path
                if parent_path.exists():
                    return parent_path

            # Fall back to XDG data directory
            if self.config.data_dir:
                xdg_path = self.config.data_dir / storage_path
                return xdg_path

            # Default to current directory
            return current_path

        return Path(storage_path)

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._chroma_client is None:
            self.storage_path.mkdir(parents=True, exist_ok=True)

            settings = ChromaSettings(
                persist_directory=str(self.storage_path),
                is_persistent=True,
                anonymized_telemetry=False,
            )

            self._chroma_client = chromadb.PersistentClient(
                path=str(self.storage_path), settings=settings
            )

        return self._chroma_client

    def _get_vector_store(self) -> ChromaVectorStore:
        """Get or create ChromaDB vector store."""
        if self._vector_store is None:
            chroma_client = self._get_chroma_client()

            try:
                collection = chroma_client.get_collection(self.collection_name)
            except Exception:
                collection = chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "AskYourDocs document collection"},
                )

            self._vector_store = ChromaVectorStore(chroma_collection=collection)

        return self._vector_store

    def get_index(self) -> Optional[VectorStoreIndex]:
        """Get existing vector index or None if not available."""
        try:
            vector_store = self._get_vector_store()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Check if index has any data
            if self.get_document_count() == 0:
                return None

            self._index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, storage_context=storage_context
            )

            return self._index

        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}")
            return None

    def create_index(self, documents: List[Any]) -> VectorStoreIndex:
        """Create new vector index from documents."""
        vector_store = self._get_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        self._index = VectorStoreIndex.from_documents(
            documents=documents, storage_context=storage_context, show_progress=True
        )

        logger.info(f"Created index with {len(documents)} documents")
        return self._index

    def add_documents(self, documents: List[Any]) -> None:
        """Add documents to existing index."""
        if self._index is None:
            self._index = self.get_index()

        if self._index is None:
            raise RuntimeError("No index available. Create index first.")

        for doc in documents:
            self._index.insert(doc)

        logger.info(f"Added {len(documents)} documents to index")

    def get_document_count(self) -> int:
        """Get total number of indexed documents."""
        try:
            collection = self._get_chroma_client().get_collection(self.collection_name)
            return collection.count()
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            document_count = self.get_document_count()

            # Calculate storage size
            storage_size = 0
            if self.storage_path.exists():
                for file_path in self.storage_path.rglob("*"):
                    if file_path.is_file():
                        storage_size += file_path.stat().st_size

            # Format storage size
            if storage_size < 1024:
                storage_size_str = f"{storage_size} B"
            elif storage_size < 1024**2:
                storage_size_str = f"{storage_size / 1024:.1f} KB"
            elif storage_size < 1024**3:
                storage_size_str = f"{storage_size / 1024**2:.1f} MB"
            else:
                storage_size_str = f"{storage_size / 1024**3:.1f} GB"

            return {
                "document_count": document_count,
                "chunk_count": document_count,  # Approximate
                "storage_size": storage_size_str,
                "storage_path": str(self.storage_path),
                "collection_name": self.collection_name,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "storage_size": "Unknown",
                "storage_path": str(self.storage_path),
                "collection_name": self.collection_name,
            }

    def is_ready(self) -> bool:
        """Check if vector store is ready for queries."""
        return self.get_document_count() > 0

    def reset(self) -> None:
        """Delete all vector data and reset storage."""
        try:
            if self.storage_path.exists():
                shutil.rmtree(self.storage_path)

            self._chroma_client = None
            self._vector_store = None
            self._index = None

            logger.info("Vector store reset completed")

        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            raise RuntimeError(f"Reset failed: {e}")

    def optimize(self) -> None:
        """Optimize vector store for better performance."""
        try:
            # ChromaDB doesn't have explicit optimization, but we can
            # trigger garbage collection and defragmentation
            chroma_client = self._get_chroma_client()

            # Force persistence
            chroma_client.persist()

            logger.info("Vector store optimization completed")

        except Exception as e:
            logger.error(f"Failed to optimize vector store: {e}")
            raise RuntimeError(f"Optimization failed: {e}")

    def export_data(self, output_path: str, include_config: bool = False) -> None:
        """Export vector database to compressed archive."""
        try:
            output_file = Path(output_path)

            with tarfile.open(output_file, "w:gz") as tar:
                # Add vector store data
                if self.storage_path.exists():
                    tar.add(self.storage_path, arcname="vector_store")

                # Add configuration if requested
                if include_config and self.config.config_path:
                    tar.add(self.config.config_path, arcname="config.yaml")

            logger.info(f"Exported data to {output_file}")

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise RuntimeError(f"Export failed: {e}")

    def import_data(self, input_path: str, merge: bool = False) -> None:
        """Import vector database from compressed archive."""
        try:
            input_file = Path(input_path)

            if not input_file.exists():
                raise FileNotFoundError(f"Import file not found: {input_file}")

            # Backup existing data if merging
            if merge and self.storage_path.exists():
                backup_path = self.storage_path.with_suffix(".backup")
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(self.storage_path, backup_path)

            # Extract archive
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(input_file, "r:gz") as tar:
                    tar.extractall(temp_dir)

                temp_path = Path(temp_dir)
                vector_store_path = temp_path / "vector_store"

                if vector_store_path.exists():
                    if not merge:
                        # Replace existing data
                        if self.storage_path.exists():
                            shutil.rmtree(self.storage_path)

                    shutil.copytree(
                        vector_store_path, self.storage_path, dirs_exist_ok=merge
                    )

                # Import configuration if present
                config_path = temp_path / "config.yaml"
                if config_path.exists() and self.config.config_path:
                    shutil.copy(config_path, self.config.config_path)

            # Reset clients to pick up new data
            self._chroma_client = None
            self._vector_store = None
            self._index = None

            logger.info(f"Imported data from {input_file}")

        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            raise RuntimeError(f"Import failed: {e}")

    def get_document_hash(self, file_path: Path) -> str:
        """Generate hash for document content and metadata."""
        try:
            stat = file_path.stat()
            content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""

    def is_document_indexed(self, file_path: Path) -> bool:
        """Check if document is already indexed."""
        try:
            doc_hash = self.get_document_hash(file_path)
            if not doc_hash:
                return False

            collection = self._get_chroma_client().get_collection(self.collection_name)

            # Query by metadata hash
            results = collection.get(where={"document_hash": doc_hash}, limit=1)

            return len(results.get("ids", [])) > 0

        except Exception as e:
            logger.debug(f"Failed to check if document indexed: {e}")
            return False
