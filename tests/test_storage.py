"""Tests for vector storage functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from askyourdocs.core.config import Config
from askyourdocs.core.storage import VectorStoreManager


class TestVectorStoreManager:
    """Test vector storage management functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()

    def test_storage_manager_initialization(self):
        """Test VectorStoreManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            assert manager.config == self.config
            assert manager.collection_name == self.config.storage.collection_name
            assert manager.storage_path == Path(temp_dir)

    def test_resolve_storage_path(self):
        """Test storage path resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test absolute path
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)
            assert manager.storage_path == Path(temp_dir)

            # Test relative path with existing directory
            rel_path = ".test_storage"
            test_dir = Path.cwd() / rel_path
            test_dir.mkdir(exist_ok=True)

            try:
                self.config.storage.path = rel_path
                manager = VectorStoreManager(self.config)
                assert manager.storage_path == test_dir
            finally:
                if test_dir.exists():
                    test_dir.rmdir()

    @patch("askyourdocs.core.storage.chromadb.PersistentClient")
    def test_get_chroma_client(self, mock_client):
        """Test ChromaDB client creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            client = manager._get_chroma_client()

            mock_client.assert_called_once()
            assert manager._chroma_client is not None

    @patch("askyourdocs.core.storage.chromadb.PersistentClient")
    def test_get_vector_store(self, mock_client):
        """Test vector store creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            # Mock client and collection
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_client_instance.get_collection.side_effect = Exception("Not found")
            mock_client_instance.create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vector_store = manager._get_vector_store()

            # Should create collection if it doesn't exist
            mock_client_instance.create_collection.assert_called_once_with(
                name=self.config.storage.collection_name,
                metadata={"description": "AskYourDocs document collection"},
            )

    def test_get_document_count(self):
        """Test document count retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            with patch.object(manager, "_get_chroma_client") as mock_get_client:
                mock_client = Mock()
                mock_collection = Mock()
                mock_collection.count.return_value = 42
                mock_client.get_collection.return_value = mock_collection
                mock_get_client.return_value = mock_client

                count = manager.get_document_count()
                assert count == 42

    def test_get_stats(self):
        """Test storage statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            # Create some test files
            test_file = Path(temp_dir) / "test.db"
            test_file.write_text("test content")

            with patch.object(manager, "get_document_count", return_value=5):
                stats = manager.get_stats()

                assert stats["document_count"] == 5
                assert stats["chunk_count"] == 5
                assert "storage_size" in stats
                assert stats["storage_path"] == temp_dir
                assert stats["collection_name"] == self.config.storage.collection_name

    def test_is_ready(self):
        """Test readiness check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            with patch.object(manager, "get_document_count") as mock_count:
                # Not ready when no documents
                mock_count.return_value = 0
                assert manager.is_ready() is False

                # Ready when documents exist
                mock_count.return_value = 10
                assert manager.is_ready() is True

    def test_get_document_hash(self):
        """Test document hash generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            # Create test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            hash1 = manager.get_document_hash(test_file)
            assert len(hash1) == 32  # MD5 hash length

            # Same file should produce same hash
            hash2 = manager.get_document_hash(test_file)
            assert hash1 == hash2

            # Modified file should produce different hash
            test_file.write_text("modified content")
            hash3 = manager.get_document_hash(test_file)
            assert hash1 != hash3

    def test_is_document_indexed(self):
        """Test document indexing check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            with patch.object(manager, "_get_chroma_client") as mock_get_client:
                mock_client = Mock()
                mock_collection = Mock()

                # Document not indexed
                mock_collection.get.return_value = {"ids": []}
                mock_client.get_collection.return_value = mock_collection
                mock_get_client.return_value = mock_client

                assert manager.is_document_indexed(test_file) is False

                # Document is indexed
                mock_collection.get.return_value = {"ids": ["doc1"]}
                assert manager.is_document_indexed(test_file) is True

    @patch("askyourdocs.core.storage.VectorStoreIndex")
    @patch("askyourdocs.core.storage.StorageContext")
    def test_create_index(self, mock_storage_context, mock_index):
        """Test index creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            # Mock documents
            mock_docs = [Mock(), Mock()]

            with patch.object(manager, "_get_vector_store") as mock_get_store:
                mock_vector_store = Mock()
                mock_get_store.return_value = mock_vector_store

                mock_context = Mock()
                mock_storage_context.from_defaults.return_value = mock_context

                mock_index_instance = Mock()
                mock_index.from_documents.return_value = mock_index_instance

                result = manager.create_index(mock_docs)

                mock_index.from_documents.assert_called_once_with(
                    documents=mock_docs,
                    storage_context=mock_context,
                    show_progress=True,
                )
                assert result == mock_index_instance

    def test_reset(self):
        """Test storage reset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.storage.path = temp_dir
            manager = VectorStoreManager(self.config)

            # Create test storage directory
            storage_path = Path(temp_dir) / "storage"
            storage_path.mkdir()
            (storage_path / "test.db").write_text("test")

            manager.storage_path = storage_path

            # Reset should remove directory
            manager.reset()

            assert not storage_path.exists()
            assert manager._chroma_client is None
            assert manager._vector_store is None
            assert manager._index is None
