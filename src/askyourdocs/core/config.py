"""
Configuration management for AskYourDocs.

Handles YAML-based configuration with XDG Base Directory compliance,
validation, and hierarchical config resolution with support for both
local and remote LLM providers.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, Field, validator
from rich.console import Console

from ..utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


class ModelConfig(BaseModel):
    """LLM model configuration with support for local and remote providers."""

    provider: str = "ollama"  # ollama, openai, anthropic, azure
    name: str = "tinyllama:1.1b"  # Default to lightweight model
    base_url: str = "http://localhost:11434"
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, gt=0)
    timeout: int = Field(300, gt=0)

    # API configuration for remote providers
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None

    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None

    @validator("provider")
    def validate_provider(cls, v: str) -> str:
        valid_providers = ["ollama", "openai", "anthropic", "azure"]
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v

    @validator("name")
    def validate_model_name(cls, v: str, values: dict[str, Any]) -> str:
        provider = values.get("provider", "ollama")

        # Validate model names based on provider
        if provider == "ollama":
            # Ollama models should be in format "model:tag" or just "model"
            if not v or len(v.strip()) == 0:
                raise ValueError("Ollama model name cannot be empty")
        elif provider == "openai":
            valid_openai_models = [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4-turbo-preview",
                "gpt-4-0125-preview",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
            ]
            # Allow any model starting with known prefixes for flexibility
            if not any(
                v.startswith(prefix.split("-")[0]) for prefix in valid_openai_models
            ):
                logger.warning(f"Unknown OpenAI model: {v}")
        elif provider == "azure":
            # Azure models are deployment-specific, so we allow any name
            pass

        return v


class EmbeddingConfig(BaseModel):
    """Embedding model configuration with local and remote options."""

    provider: str = "huggingface"  # huggingface, openai, local
    model: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    batch_size: int = Field(32, gt=0)
    max_length: int = Field(512, gt=0)

    # Remote embedding settings
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    @validator("device")
    def validate_device(cls, v: str) -> str:
        valid_devices = ["cpu", "cuda", "mps", "auto"]
        if v not in valid_devices:
            raise ValueError(f"Device must be one of {valid_devices}")
        return v

    @validator("provider")
    def validate_provider(cls, v: str) -> str:
        valid_providers = ["huggingface", "openai", "local"]
        if v not in valid_providers:
            raise ValueError(f"Embedding provider must be one of {valid_providers}")
        return v


class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

    strategy: str = "sentence"
    chunk_size: int = Field(1000, gt=0, le=8000)
    chunk_overlap: int = Field(200, ge=0)
    respect_boundaries: bool = True
    min_chunk_size: int = Field(100, gt=0)

    @validator("strategy")
    def validate_strategy(cls, v: str) -> str:
        valid_strategies = ["sentence", "recursive", "semantic", "fixed"]
        if v not in valid_strategies:
            raise ValueError(f"Strategy must be one of {valid_strategies}")
        return v

    @validator("chunk_overlap")
    def validate_overlap(cls, v: int, values: dict[str, Any]) -> int:
        chunk_size = values.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v


class RetrievalConfig(BaseModel):
    """Retrieval and search configuration."""

    top_k: int = Field(5, gt=0, le=50)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)
    rerank: bool = True
    retrieval_mode: str = "hybrid"
    max_context_length: int = Field(4000, gt=0)

    @validator("retrieval_mode")
    def validate_mode(cls, v: str) -> str:
        valid_modes = ["vector", "keyword", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"Retrieval mode must be one of {valid_modes}")
        return v


class StorageConfig(BaseModel):
    """Vector storage configuration."""

    backend: str = "chromadb"
    path: str = ".askyourdocs"
    compression: bool = True
    collection_name: str = "documents"
    persist_directory: Optional[str] = None

    @validator("backend")
    def validate_backend(cls, v: str) -> str:
        valid_backends = ["chromadb"]
        if v not in valid_backends:
            raise ValueError(f"Backend must be one of {valid_backends}")
        return v


class LlamaIndexConfig(BaseModel):
    """LlamaIndex-specific configuration."""

    response_mode: str = "compact"
    service_context_chunk_size: int = Field(1024, gt=0)
    similarity_top_k: int = Field(5, gt=0)
    streaming: bool = False

    @validator("response_mode")
    def validate_response_mode(cls, v: str) -> str:
        valid_modes = ["compact", "tree_summarize", "accumulate", "refine"]
        if v not in valid_modes:
            raise ValueError(f"Response mode must be one of {valid_modes}")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_file_size: str = "10MB"
    backup_count: int = 3

    @validator("level")
    def validate_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class Config(BaseModel):
    """Main configuration class with environment variable support."""

    model: ModelConfig = Field(default_factory=ModelConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llamaindex: LlamaIndexConfig = Field(default_factory=LlamaIndexConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Runtime properties
    config_path: Optional[Path] = Field(None, exclude=True)
    data_dir: Optional[Path] = Field(None, exclude=True)

    def __init__(self, **data):
        """Initialize config with environment variable resolution."""
        # Resolve environment variables for API keys
        if "model" in data:
            model_data = data["model"]
            if isinstance(model_data, dict):
                # Check for API keys in environment
                if not model_data.get("api_key"):
                    if model_data.get("provider") == "openai":
                        model_data["api_key"] = os.getenv("OPENAI_API_KEY")
                    elif model_data.get("provider") == "anthropic":
                        model_data["api_key"] = os.getenv("ANTHROPIC_API_KEY")
                    elif model_data.get("provider") == "azure":
                        model_data["api_key"] = os.getenv("AZURE_OPENAI_API_KEY")
                        model_data["azure_endpoint"] = os.getenv(
                            "AZURE_OPENAI_ENDPOINT"
                        )

        if "embedding" in data:
            embedding_data = data["embedding"]
            if isinstance(embedding_data, dict):
                if (
                    not embedding_data.get("api_key")
                    and embedding_data.get("provider") == "openai"
                ):
                    embedding_data["api_key"] = os.getenv("OPENAI_API_KEY")

        super().__init__(**data)

    def is_remote_provider(self) -> bool:
        """Check if using remote LLM provider."""
        return self.model.provider in ["openai", "anthropic", "azure"]

    def has_api_key(self) -> bool:
        """Check if API key is available for remote providers."""
        if not self.is_remote_provider():
            return True  # Local providers don't need API keys
        return bool(self.model.api_key)


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    def __init__(self) -> None:
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.yaml"
        self.data_dir = self._get_data_dir()

    def _get_config_dir(self) -> Path:
        """Get XDG-compliant configuration directory."""
        if config_home := os.environ.get("XDG_CONFIG_HOME"):
            return Path(config_home) / "askyourdocs"
        return Path.home() / ".config" / "askyourdocs"

    def _get_data_dir(self) -> Path:
        """Get XDG-compliant data directory."""
        if data_home := os.environ.get("XDG_DATA_HOME"):
            return Path(data_home) / "askyourdocs"
        return Path.home() / ".local" / "share" / "askyourdocs"

    def _create_default_config(self) -> None:
        """Create default configuration file with helpful comments."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        default_config = Config()

        # Update paths to use XDG directories
        if not default_config.logging.file:
            default_config.logging.file = str(self.data_dir / "logs" / "app.log")

        config_dict = default_config.model_dump(exclude={"config_path", "data_dir"})

        # Create config with helpful comments
        config_content = f"""# AskYourDocs Configuration
# This file controls all aspects of AskYourDocs behavior
# For more information, visit: https://docs.askyourdocs.dev

# LLM Model Configuration
model:
  provider: "{config_dict['model']['provider']}"  # ollama (local), openai, anthropic, azure
  name: "{config_dict['model']['name']}"  # Model name/identifier
  base_url: "{config_dict['model']['base_url']}"  # For local providers like Ollama
  temperature: {config_dict['model']['temperature']}  # Response creativity (0.0-2.0)
  max_tokens: {config_dict['model']['max_tokens']}  # Maximum response length
  timeout: {config_dict['model']['timeout']}  # Request timeout in seconds

  # Remote provider settings (only needed for OpenAI/Anthropic/Azure)
  # api_key: "your-api-key-here"  # Or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var
  # api_base: "https://api.openai.com/v1"  # Custom API endpoint
  # organization: "your-org-id"  # OpenAI organization ID

  # Azure-specific settings
  # azure_endpoint: "https://your-resource.openai.azure.com/"
  # azure_deployment: "your-deployment-name"

# Embedding Model Configuration
embedding:
  provider: "{config_dict['embedding']['provider']}"  # huggingface (local), openai
  model: "{config_dict['embedding']['model']}"  # Embedding model name
  device: "{config_dict['embedding']['device']}"  # cpu, cuda, mps, auto
  batch_size: {config_dict['embedding']['batch_size']}  # Batch size for processing
  max_length: {config_dict['embedding']['max_length']}  # Maximum token length

  # For OpenAI embeddings (optional)
  # api_key: "your-openai-api-key"

# Document Chunking Configuration
chunking:
  strategy: "{config_dict['chunking']['strategy']}"  # sentence, recursive, semantic, fixed
  chunk_size: {config_dict['chunking']['chunk_size']}  # Characters per chunk (100-8000)
  chunk_overlap: {config_dict['chunking']['chunk_overlap']}  # Overlap between chunks
  respect_boundaries: {str(config_dict['chunking']['respect_boundaries']).lower()}  # Respect sentence/paragraph boundaries
  min_chunk_size: {config_dict['chunking']['min_chunk_size']}  # Minimum chunk size

# Retrieval and Search Configuration
retrieval:
  top_k: {config_dict['retrieval']['top_k']}  # Number of chunks to retrieve (1-50)
  similarity_threshold: {config_dict['retrieval']['similarity_threshold']}  # Minimum similarity score (0.0-1.0)
  rerank: {str(config_dict['retrieval']['rerank']).lower()}  # Re-rank results for better relevance
  retrieval_mode: "{config_dict['retrieval']['retrieval_mode']}"  # vector, keyword, hybrid
  max_context_length: {config_dict['retrieval']['max_context_length']}  # Maximum context for LLM

# Vector Storage Configuration
storage:
  backend: "{config_dict['storage']['backend']}"  # chromadb (only supported backend)
  path: "{config_dict['storage']['path']}"  # Storage directory (.askyourdocs)
  compression: {str(config_dict['storage']['compression']).lower()}  # Enable compression
  collection_name: "{config_dict['storage']['collection_name']}"  # ChromaDB collection name

# LlamaIndex Framework Configuration
llamaindex:
  response_mode: "{config_dict['llamaindex']['response_mode']}"  # compact, tree_summarize, accumulate, refine
  service_context_chunk_size: {config_dict['llamaindex']['service_context_chunk_size']}  # Service context chunk size
  similarity_top_k: {config_dict['llamaindex']['similarity_top_k']}  # Similarity search results
  streaming: {str(config_dict['llamaindex']['streaming']).lower()}  # Enable streaming responses

# Logging Configuration
logging:
  level: "{config_dict['logging']['level']}"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "{config_dict['logging']['file']}"  # Log file path (null for no file logging)
  format: "{config_dict['logging']['format']}"  # Log message format
  max_file_size: "{config_dict['logging']['max_file_size']}"  # Maximum log file size
  backup_count: {config_dict['logging']['backup_count']}  # Number of backup log files

# Quick Setup Examples:
#
# For OpenAI (requires API key):
# model:
#   provider: "openai"
#   name: "gpt-4"
#   api_key: "sk-your-key-here"
#
# For Anthropic (requires API key):
# model:
#   provider: "anthropic"
#   name: "claude-3-sonnet-20240229"
#   api_key: "sk-ant-your-key-here"
#
# For Azure OpenAI (requires API key and endpoint):
# model:
#   provider: "azure"
#   name: "gpt-4"
#   api_key: "your-azure-key"
#   azure_endpoint: "https://your-resource.openai.azure.com/"
#   azure_deployment: "your-deployment-name"
"""

        with open(self.config_file, "w") as f:
            f.write(config_content)

        logger.info(f"Created default configuration at {self.config_file}")

    def load_config(self) -> Config:
        """Load configuration from file or create defaults."""
        if not self.config_file.exists():
            self._create_default_config()

        try:
            with open(self.config_file) as f:
                config_data = yaml.safe_load(f) or {}

            config = Config(**config_data)
            config.config_path = self.config_file
            config.data_dir = self.data_dir

            return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise RuntimeError(f"Configuration error: {e}")

    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        config_dict = config.model_dump(exclude={"config_path", "data_dir"})

        with open(self.config_file, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

        logger.info(f"Saved configuration to {self.config_file}")

    def get_value(self, key: str) -> Any:
        """Get configuration value by dot notation key."""
        config = self.load_config()
        config_dict = config.model_dump()

        keys = key.split(".")
        value = config_dict

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                raise KeyError(f"Configuration key '{key}' not found")

        return value

    def set_value(self, key: str, value: Union[str, int, float, bool]) -> None:
        """Set configuration value by dot notation key."""
        config = self.load_config()
        config_dict = config.model_dump(exclude={"config_path", "data_dir"})

        keys = key.split(".")
        current = config_dict

        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Convert string values to appropriate types
        if isinstance(value, str):
            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            elif "." in value and value.replace(".", "").replace("-", "").isdigit():
                value = float(value)

        current[keys[-1]] = value

        # Validate and save
        new_config = Config(**config_dict)
        new_config.config_path = config.config_path
        new_config.data_dir = config.data_dir

        self.save_config(new_config)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        if self.config_file.exists():
            backup_path = self.config_file.with_suffix(".yaml.backup")
            shutil.copy(self.config_file, backup_path)
            logger.info(f"Backed up existing config to {backup_path}")

        self._create_default_config()

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate current configuration and return issues."""
        issues = []

        try:
            config = self.load_config()

            # Check remote provider requirements
            if config.is_remote_provider() and not config.has_api_key():
                issues.append(
                    f"Remote provider '{config.model.provider}' requires API key"
                )

            # Check model availability for Ollama
            if config.model.provider == "ollama":
                try:
                    import requests

                    response = requests.get(
                        f"{config.model.base_url}/api/tags", timeout=5
                    )
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m["name"] for m in models]
                        if config.model.name not in model_names:
                            issues.append(
                                f"Ollama model '{config.model.name}' not found. Available: {model_names}"
                            )
                    else:
                        issues.append("Cannot connect to Ollama server")
                except Exception:
                    issues.append("Ollama server not accessible")

            # Check embedding model
            if config.embedding.provider == "huggingface":
                try:
                    pass

                    # This will download the model if not available
                    # SentenceTransformer(config.embedding.model)
                except Exception as e:
                    issues.append(
                        f"Embedding model '{config.embedding.model}' not available: {e}"
                    )

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Configuration validation failed: {e}"]


# Global configuration instance
_config_manager: Optional[ConfigManager] = None
_config: Optional[Config] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = get_config_manager().load_config()
    return _config


def reload_config() -> Config:
    """Reload configuration from file."""
    global _config
    _config = get_config_manager().load_config()
    return _config
