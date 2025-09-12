"""
Query engine and retrieval system for AskYourDocs.

Handles query processing, context retrieval, response generation,
and streaming responses using LlamaIndex.
"""

import time
from typing import Any, Dict, Generator, List, Optional

from llama_index.core import Settings
from llama_index.core.base.response.schema import StreamingResponse
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import (
    ResponseMode,
    get_response_synthesizer,
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.azure_openai import AzureOpenAI
from rich.console import Console

from .config import Config
from .storage import VectorStoreManager
from ..utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


class QueryEngine:
    """Handles document querying and response generation."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.storage_manager = VectorStoreManager(config)

        self._setup_llamaindex()
        self._query_engine: Optional[RetrieverQueryEngine] = None

    def _setup_llamaindex(self) -> None:
        """Configure LlamaIndex global settings."""
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
                # Default to HuggingFace for local processing
                embed_model = HuggingFaceEmbedding(
                    model_name=self.config.embedding.model,
                    device=self.config.embedding.device,
                    max_length=self.config.embedding.max_length,
                )

            Settings.embed_model = embed_model

            # Configure LLM based on provider
            if self.config.model.provider == "ollama":
                Settings.llm = Ollama(
                    model=self.config.model.name,
                    base_url=self.config.model.base_url,
                    temperature=self.config.model.temperature,
                    request_timeout=self.config.model.timeout,
                )
            elif self.config.model.provider == "openai":
                if not self.config.model.api_key:
                    raise ValueError("OpenAI API key required for OpenAI models")
                Settings.llm = OpenAI(
                    model=self.config.model.name,
                    api_key=self.config.model.api_key,
                    api_base=self.config.model.api_base,
                    temperature=self.config.model.temperature,
                    max_tokens=self.config.model.max_tokens,
                )
            elif self.config.model.provider == "anthropic":
                if not self.config.model.api_key:
                    raise ValueError("Anthropic API key required for Anthropic models")
                Settings.llm = Anthropic(
                    model=self.config.model.name,
                    api_key=self.config.model.api_key,
                    temperature=self.config.model.temperature,
                    max_tokens=self.config.model.max_tokens,
                )
            elif self.config.model.provider == "azure":
                if (
                    not self.config.model.api_key
                    or not self.config.model.azure_endpoint
                ):
                    raise ValueError(
                        "Azure OpenAI API key and endpoint required for Azure models"
                    )
                Settings.llm = AzureOpenAI(
                    model=self.config.model.name,
                    api_key=self.config.model.api_key,
                    azure_endpoint=self.config.model.azure_endpoint,
                    api_version=self.config.model.api_version or "2024-02-15-preview",
                    temperature=self.config.model.temperature,
                    max_tokens=self.config.model.max_tokens,
                )
            else:
                raise ValueError(
                    f"Unsupported LLM provider: {self.config.model.provider}"
                )

            # Configure chunking
            Settings.chunk_size = self.config.chunking.chunk_size
            Settings.chunk_overlap = self.config.chunking.chunk_overlap

            logger.info("LlamaIndex configuration completed")

        except Exception as e:
            logger.error(f"Failed to setup LlamaIndex: {e}")
            raise RuntimeError(f"LlamaIndex setup failed: {e}")

    def _get_query_engine(self) -> RetrieverQueryEngine:
        """Get or create query engine."""
        if self._query_engine is None:
            index = self.storage_manager.get_index()
            if index is None:
                raise RuntimeError("No vector index available. Run ingestion first.")

            # Create retriever
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=self.config.retrieval.top_k,
            )

            # Create response synthesizer
            response_synthesizer = get_response_synthesizer(
                response_mode=ResponseMode(self.config.llamaindex.response_mode),
                streaming=self.config.llamaindex.streaming,
            )

            # Create query engine
            self._query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
            )

        return self._query_engine

    def is_ready(self) -> bool:
        """Check if query engine is ready."""
        return self.storage_manager.is_ready()

    def query(self, question: str) -> Any:
        """Execute query and return response."""
        if not question.strip():
            raise ValueError("Question cannot be empty")

        try:
            start_time = time.time()

            query_engine = self._get_query_engine()
            response = query_engine.query(question)

            query_time = time.time() - start_time
            logger.info(f"Query completed in {query_time:.2f}s")

            return response

        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)

            # Check for common issues and provide helpful errors
            if "connection" in str(e).lower():
                raise RuntimeError(
                    "Failed to connect to Ollama. Please ensure Ollama is running:\n"
                    "  1. Start Ollama: 'ollama serve'\n"
                    "  2. Download model: 'ollama pull llama3.1:8b'\n"
                    "  3. Test connection: 'curl http://localhost:11434/api/tags'"
                )
            elif "model" in str(e).lower():
                raise RuntimeError(
                    f"Model '{self.config.model.name}' not available. "
                    f"Download it with: 'ollama pull {self.config.model.name}'"
                )
            else:
                raise RuntimeError(f"Query execution failed: {e}")

    def stream_query(self, question: str) -> Generator[str, None, None]:
        """Execute streaming query and yield response chunks."""
        if not question.strip():
            raise ValueError("Question cannot be empty")

        try:
            # Enable streaming for this query
            original_streaming = self.config.llamaindex.streaming
            self.config.llamaindex.streaming = True

            # Reset query engine to pick up streaming config
            self._query_engine = None

            query_engine = self._get_query_engine()
            response = query_engine.query(question)

            if isinstance(response, StreamingResponse):
                for chunk in response.response_gen:
                    yield chunk
            else:
                # Fallback for non-streaming response
                yield str(response.response)

            # Restore original streaming setting
            self.config.llamaindex.streaming = original_streaming
            self._query_engine = None

        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            raise RuntimeError(f"Streaming query failed: {e}")

    def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform fast keyword search without LLM."""
        try:
            # This is a simplified implementation
            # In production, you'd implement BM25 or similar

            index = self.storage_manager.get_index()
            if index is None:
                return []

            # Use retriever for similarity search
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=limit,
            )

            nodes = retriever.retrieve(query)

            results = []
            for node in nodes:
                results.append(
                    {
                        "file": node.metadata.get("file_path", "Unknown"),
                        "score": getattr(node, "score", 0.0),
                        "preview": node.text[:200].replace("\n", " ") + "...",
                        "metadata": node.metadata,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def get_similar_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Get documents similar to query without generating response."""
        try:
            index = self.storage_manager.get_index()
            if index is None:
                return []

            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=top_k,
            )

            nodes = retriever.retrieve(query)

            results = []
            for node in nodes:
                results.append(
                    {
                        "file_path": node.metadata.get("file_path", "Unknown"),
                        "file_name": node.metadata.get("file_name", "Unknown"),
                        "similarity_score": getattr(node, "score", 0.0),
                        "content_preview": node.text[:300],
                        "metadata": node.metadata,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to get similar documents: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection to LLM and embedding models."""
        try:
            # Test LLM connection
            llm = Settings.llm
            if hasattr(llm, "complete"):
                test_response = llm.complete("Hello")
                if not test_response or not test_response.text:
                    return False

            # Test embedding model
            embed_model = Settings.embed_model
            if hasattr(embed_model, "get_text_embedding"):
                test_embedding = embed_model.get_text_embedding("test")
                if not test_embedding or len(test_embedding) == 0:
                    return False

            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_chat_history(self) -> List[ChatMessage]:
        """Get chat history for conversation context."""
        # This would be implemented for conversational features
        return []

    def clear_chat_history(self) -> None:
        """Clear chat history."""
        # This would be implemented for conversational features
        pass
