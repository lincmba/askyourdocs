"""Tests for query engine and retrieval functionality."""

from unittest.mock import Mock, patch

import pytest
from askyourdocs.core.config import Config
from askyourdocs.core.retrieval import QueryEngine


class TestQueryEngine:
    """Test query engine functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()

    @patch("askyourdocs.core.retrieval.VectorStoreManager")
    @patch("askyourdocs.core.retrieval.Settings")
    def test_query_engine_initialization(self, mock_settings, mock_storage):
        """Test QueryEngine initialization."""
        engine = QueryEngine(self.config)

        assert engine.config == self.config
        assert engine.storage_manager is not None
        mock_storage.assert_called_once_with(self.config)

    @patch("askyourdocs.core.retrieval.VectorStoreManager")
    @patch("askyourdocs.core.retrieval.Settings")
    @patch("askyourdocs.core.retrieval.Ollama")
    @patch("askyourdocs.core.retrieval.HuggingFaceEmbedding")
    def test_llamaindex_setup_ollama(
        self, mock_embedding, mock_ollama, mock_settings, mock_storage
    ):
        """Test LlamaIndex setup with Ollama provider."""
        self.config.model.provider = "ollama"
        self.config.model.name = "llama3.1:8b"

        engine = QueryEngine(self.config)

        # Verify Ollama LLM was configured
        mock_ollama.assert_called_once_with(
            model=self.config.model.name,
            base_url=self.config.model.base_url,
            temperature=self.config.model.temperature,
            request_timeout=self.config.model.timeout,
        )

        # Verify HuggingFace embedding was configured
        mock_embedding.assert_called_once_with(
            model_name=self.config.embedding.model,
            device=self.config.embedding.device,
            max_length=self.config.embedding.max_length,
        )

    @patch("askyourdocs.core.retrieval.VectorStoreManager")
    @patch("askyourdocs.core.retrieval.Settings")
    @patch("askyourdocs.core.retrieval.OpenAI")
    @patch("askyourdocs.core.retrieval.OpenAIEmbedding")
    def test_llamaindex_setup_openai(
        self, mock_embedding, mock_openai, mock_settings, mock_storage
    ):
        """Test LlamaIndex setup with OpenAI provider."""
        self.config.model.provider = "openai"
        self.config.model.name = "gpt-4"
        self.config.model.api_key = "test-key"
        self.config.embedding.provider = "openai"
        self.config.embedding.api_key = "test-key"

        engine = QueryEngine(self.config)

        # Verify OpenAI LLM was configured
        mock_openai.assert_called_once_with(
            model=self.config.model.name,
            api_key=self.config.model.api_key,
            api_base=self.config.model.api_base,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens,
        )

        # Verify OpenAI embedding was configured
        mock_embedding.assert_called_once_with(
            model=self.config.embedding.model,
            api_key=self.config.embedding.api_key,
            api_base=self.config.embedding.api_base,
        )

    def test_is_ready(self):
        """Test readiness check."""
        with patch("askyourdocs.core.retrieval.VectorStoreManager") as mock_storage:
            with patch("askyourdocs.core.retrieval.Settings"):
                mock_storage_instance = Mock()
                mock_storage_instance.is_ready.return_value = True
                mock_storage.return_value = mock_storage_instance

                engine = QueryEngine(self.config)
                assert engine.is_ready() is True

                mock_storage_instance.is_ready.return_value = False
                assert engine.is_ready() is False

    def test_query_validation(self):
        """Test query input validation."""
        with patch("askyourdocs.core.retrieval.VectorStoreManager"):
            with patch("askyourdocs.core.retrieval.Settings"):
                engine = QueryEngine(self.config)

                # Empty question should raise error
                with pytest.raises(ValueError, match="Question cannot be empty"):
                    engine.query("")

                with pytest.raises(ValueError, match="Question cannot be empty"):
                    engine.query("   ")

    def test_keyword_search(self):
        """Test keyword search functionality."""
        with patch("askyourdocs.core.retrieval.VectorStoreManager") as mock_storage:
            with patch("askyourdocs.core.retrieval.Settings"):
                # Mock storage and index
                mock_storage_instance = Mock()
                mock_index = Mock()
                mock_storage_instance.get_index.return_value = mock_index
                mock_storage.return_value = mock_storage_instance

                # Mock retriever and nodes
                with patch(
                    "askyourdocs.core.retrieval.VectorIndexRetriever"
                ) as mock_retriever:
                    mock_node = Mock()
                    mock_node.metadata = {"file_path": "test.txt"}
                    mock_node.text = "This is test content for search"
                    mock_node.score = 0.95

                    mock_retriever_instance = Mock()
                    mock_retriever_instance.retrieve.return_value = [mock_node]
                    mock_retriever.return_value = mock_retriever_instance

                    engine = QueryEngine(self.config)
                    results = engine.keyword_search("test", limit=5)

                    assert len(results) == 1
                    assert results[0]["file"] == "test.txt"
                    assert results[0]["score"] == 0.95
                    assert "test content" in results[0]["preview"]

    def test_get_similar_documents(self):
        """Test similar documents retrieval."""
        with patch("askyourdocs.core.retrieval.VectorStoreManager") as mock_storage:
            with patch("askyourdocs.core.retrieval.Settings"):
                # Mock storage and index
                mock_storage_instance = Mock()
                mock_index = Mock()
                mock_storage_instance.get_index.return_value = mock_index
                mock_storage.return_value = mock_storage_instance

                # Mock retriever and nodes
                with patch(
                    "askyourdocs.core.retrieval.VectorIndexRetriever"
                ) as mock_retriever:
                    mock_node = Mock()
                    mock_node.metadata = {
                        "file_path": "document.pdf",
                        "file_name": "document.pdf",
                    }
                    mock_node.text = "This is document content"
                    mock_node.score = 0.88

                    mock_retriever_instance = Mock()
                    mock_retriever_instance.retrieve.return_value = [mock_node]
                    mock_retriever.return_value = mock_retriever_instance

                    engine = QueryEngine(self.config)
                    results = engine.get_similar_documents("query", top_k=3)

                    assert len(results) == 1
                    assert results[0]["file_path"] == "document.pdf"
                    assert results[0]["file_name"] == "document.pdf"
                    assert results[0]["similarity_score"] == 0.88
                    assert "document content" in results[0]["content_preview"]
