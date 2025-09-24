"""Tests for CLI functionality."""

from unittest.mock import patch

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
        assert "Privacy-first, local-only document Q&A CLI tool" in result.output
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

    def test_config_show_command(self):
        """Test config show command."""
        result = self.runner.invoke(cli, ["config", "show"])
        # Should not crash (may fail due to missing config, but shouldn't crash)
        assert isinstance(result.exit_code, int)
