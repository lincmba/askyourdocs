"""Tests for document ingestion functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from askyourdocs.core.config import Config
from askyourdocs.core.ingestion import DocumentIngestor


class TestDocumentIngestor:
    """Test document ingestion functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        
    @patch("askyourdocs.core.ingestion.VectorStoreManager")
    @patch("askyourdocs.core.ingestion.Settings")
    def test_ingestor_initialization(self, mock_settings, mock_storage):
        """Test DocumentIngestor initialization."""
        ingestor = DocumentIngestor(self.config)
        
        assert ingestor.config == self.config
        assert ingestor.storage_manager is not None
        mock_storage.assert_called_once_with(self.config)
    
    def test_should_process_file(self):
        """Test file filtering logic."""
        with patch("askyourdocs.core.ingestion.VectorStoreManager"):
            with patch("askyourdocs.core.ingestion.Settings"):
                ingestor = DocumentIngestor(self.config)
                
                # Should process supported files
                assert ingestor._should_process_file(Path("document.pdf")) is True
                assert ingestor._should_process_file(Path("text.txt")) is True
                assert ingestor._should_process_file(Path("code.py")) is True
                
                # Should skip unsupported files
                assert ingestor._should_process_file(Path("image.jpg")) is False
                assert ingestor._should_process_file(Path(".hidden")) is False
                assert ingestor._should_process_file(Path("__pycache__/file.py")) is False
    
    def test_filter_files(self):
        """Test file filtering with patterns."""
        with patch("askyourdocs.core.ingestion.VectorStoreManager"):
            with patch("askyourdocs.core.ingestion.Settings"):
                ingestor = DocumentIngestor(self.config)
                
                files = [
                    Path("doc1.pdf"),
                    Path("doc2.txt"),
                    Path("temp/doc3.pdf"),
                    Path("code.py"),
                    Path("image.jpg"),
                ]
                
                # Test include patterns
                filtered = ingestor._filter_files(files, include_patterns=["*.pdf"])
                pdf_files = [f for f in filtered if f.suffix == ".pdf"]
                assert len(pdf_files) == 2
                
                # Test exclude patterns
                filtered = ingestor._filter_files(files, exclude_patterns=["temp/*"])
                temp_files = [f for f in filtered if "temp" in str(f)]
                assert len(temp_files) == 0
    
    @patch("askyourdocs.core.ingestion.get_document_loader")
    def test_load_document(self, mock_get_loader):
        """Test document loading."""
        with patch("askyourdocs.core.ingestion.VectorStoreManager") as mock_storage:
            with patch("askyourdocs.core.ingestion.Settings"):
                # Mock loader
                mock_loader_class = Mock()
                mock_loader_instance = Mock()
                mock_document = Mock()
                mock_document.metadata = {}
                
                mock_loader_class.return_value = mock_loader_instance
                mock_loader_instance.load_data.return_value = [mock_document]
                mock_get_loader.return_value = mock_loader_class
                
                # Mock storage manager
                mock_storage_instance = Mock()
                mock_storage_instance.get_document_hash.return_value = "test_hash"
                mock_storage.return_value = mock_storage_instance
                
                ingestor = DocumentIngestor(self.config)
                
                # Create test file
                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                    f.write(b"Test content")
                    test_file = Path(f.name)
                
                try:
                    doc = ingestor._load_document(test_file)
                    
                    assert doc is not None
                    assert "file_path" in doc.metadata
                    assert "file_name" in doc.metadata
                    assert "document_hash" in doc.metadata
                    
                finally:
                    test_file.unlink()

    def test_discover_files(self):
        """Test file discovery in directory."""
        with patch("askyourdocs.core.ingestion.VectorStoreManager"):
            with patch("askyourdocs.core.ingestion.Settings"):
                ingestor = DocumentIngestor(self.config)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # Create test files
                    (temp_path / "doc1.pdf").touch()
                    (temp_path / "doc2.txt").touch()
                    (temp_path / "image.jpg").touch()  # Should be filtered out
                    
                    # Create subdirectory with files
                    sub_dir = temp_path / "subdir"
                    sub_dir.mkdir()
                    (sub_dir / "doc3.md").touch()
                    
                    files = ingestor._discover_files(temp_path)
                    
                    # Should find supported files recursively
                    assert len(files) >= 3
                    extensions = {f.suffix for f in files}
                    assert ".pdf" in extensions
                    assert ".txt" in extensions
                    assert ".md" in extensions
                    assert ".jpg" not in extensions  # Should be filtered out


class TestDocumentChangeHandler:
    """Test file system change handler."""
    
    def test_change_handler_initialization(self):
        """Test change handler initialization."""
        with patch("askyourdocs.core.ingestion.VectorStoreManager"):
            with patch("askyourdocs.core.ingestion.Settings"):
                config = Config()
                ingestor = DocumentIngestor(config)
                
                from askyourdocs.core.ingestion import DocumentChangeHandler
                handler = DocumentChangeHandler(ingestor)
                
                assert handler.ingestor == ingestor
                assert handler.debounce_time == 2.0
                assert len(handler.pending_files) == 0
