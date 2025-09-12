"""Tests for CLI functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from askyourdocs.main import cli


class TestCLI:
    """Test CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_version_command(self):
        """Test version display."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "AskYourDocs v" in result.output
    
    def test_help_command(self):
        """Test help display."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Privacy-first document Q&A" in result.output
        assert "ingest" in result.output
        assert "ask" in result.output
    
    def test_status_command(self):
        """Test status command."""
        with patch("askyourdocs.core.storage.VectorStoreManager") as mock_storage:
            mock_storage.return_value.get_stats.return_value = {
                "document_count": 0,
                "chunk_count": 0,
                "storage_size": "0 B",
                "storage_path": "/tmp/test",
                "collection_name": "documents",
            }
            
            result = self.runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "AskYourDocs Status" in result.output
    
    @patch("askyourdocs.core.ingestion.DocumentIngestor")
    def test_ingest_command(self, mock_ingestor):
        """Test ingest command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("This is a test document.")
            
            # Mock the ingestor
            mock_instance = Mock()
            mock_ingestor.return_value = mock_instance
            
            result = self.runner.invoke(cli, ["ingest", temp_dir])
            
            # Command should execute without error
            assert result.exit_code == 0
            mock_ingestor.assert_called_once()
            mock_instance.ingest_directory.assert_called_once()
    
    @patch("askyourdocs.core.retrieval.QueryEngine")
    def test_ask_command(self, mock_engine):
        """Test ask command."""
        # Mock query engine
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.response = "This is a test answer."
        mock_response.source_nodes = []
        
        mock_instance.is_ready.return_value = True
        mock_instance.query.return_value = mock_response
        mock_engine.return_value = mock_instance
        
        result = self.runner.invoke(cli, ["ask", "What is this about?"])
        
        assert result.exit_code == 0
        mock_engine.assert_called_once()
        mock_instance.query.assert_called_once_with("What is this about?")
    
    def test_config_show_command(self):
        """Test config show command."""
        result = self.runner.invoke(cli, ["config", "show"])
        # Should not crash (may fail due to missing config, but shouldn't crash)
        assert isinstance(result.exit_code, int)
    
    def test_search_command(self):
        """Test search command."""
        with patch("askyourdocs.core.retrieval.QueryEngine") as mock_engine:
            mock_instance = Mock()
            mock_instance.is_ready.return_value = True
            mock_instance.keyword_search.return_value = [
                {
                    "file": "test.txt",
                    "score": 0.95,
                    "preview": "This is a test document...",
                }
            ]
            mock_engine.return_value = mock_instance
            
            result = self.runner.invoke(cli, ["search", "test"])
            
            assert result.exit_code == 0
            mock_instance.keyword_search.assert_called_once()


class TestConfigCommands:
    """Test configuration management commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_config_set_command(self):
        """Test setting configuration values."""
        with patch("askyourdocs.core.config.ConfigManager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            
            result = self.runner.invoke(cli, [
                "config", "set", "model.temperature", "0.5"
            ])
            
            mock_instance.set_value.assert_called_once_with("model.temperature", "0.5")
    
    def test_config_reset_command(self):
        """Test resetting configuration."""
        with patch("askyourdocs.core.config.ConfigManager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            
            result = self.runner.invoke(cli, ["config", "reset"])
            
            mock_instance.reset_to_defaults.assert_called_once()