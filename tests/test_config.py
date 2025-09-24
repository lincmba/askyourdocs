"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest
import yaml

from askyourdocs.core.config import Config, ConfigManager


class TestConfigManager:
    """Test configuration management functionality."""
    
    def test_default_config_creation(self):
        """Test creation of default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock XDG directories
            config_dir = Path(temp_dir) / "config"
            data_dir = Path(temp_dir) / "data"
            
            manager = ConfigManager()
            manager.config_dir = config_dir
            manager.config_file = config_dir / "config.yaml"
            manager.data_dir = data_dir
            
            config = manager.load_config()
            
            assert isinstance(config, Config)
            assert config.model.provider == "ollama"
            assert config.model.name == "tinyllama:1.1b"
            assert config.chunking.chunk_size == 1000
            assert manager.config_file.exists()

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config_data = {
            "model": {
                "provider": "ollama",
                "name": "llama3.1:8b",
                "temperature": 0.1,
            }
        }
        config = Config(**config_data)
        assert config.model.temperature == 0.1


    def test_config_get_set_value(self):
        """Test getting and setting configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"

            manager = ConfigManager()
            manager.config_dir = config_dir
            manager.config_file = config_dir / "config.yaml"

            # Create initial config
            config = manager.load_config()

            # Test getting value
            temperature = manager.get_value("model.temperature")
            assert temperature == 0.1

            # Test setting value
            manager.set_value("model.temperature", "0.5")
            new_temperature = manager.get_value("model.temperature")
            assert new_temperature == 0.5

            # Test setting boolean
            manager.set_value("chunking.respect_boundaries", "false")
            boundaries = manager.get_value("chunking.respect_boundaries")
            assert boundaries is False


class TestConfig:
    """Test configuration model validation."""

    def test_model_config_validation(self):
        """Test model configuration validation."""
        # Valid config
        model_config = {
            "provider": "ollama",
            "name": "claude-3-5-sonnet-20241022",
            "temperature": 0.5,
            "max_tokens": 1024,
        }

        config = Config(model=model_config)
        assert config.model.temperature == 0.5
        assert config.model.name == "claude-3-5-sonnet-20241022"
        
        # Invalid max_tokens (negative)
        with pytest.raises(ValueError):
            Config(model={"max_tokens": -1})
    
    def test_embedding_config_validation(self):
        """Test embedding configuration validation."""
        # Valid config
        embedding_config = {
            "model": "BAAI/bge-small-en-v1.5",
            "device": "cpu",
            "batch_size": 16,
        }
        
        config = Config(embedding=embedding_config)
        assert config.embedding.device == "cpu"
        
        # Invalid device
        with pytest.raises(ValueError):
            Config(embedding={"device": "invalid"})
    
    def test_chunking_config_validation(self):
        """Test chunking configuration validation."""
        # Valid config
        chunking_config = {
            "strategy": "sentence",
            "chunk_size": 1000,
            "chunk_overlap": 200,
        }
        
        config = Config(chunking=chunking_config)
        assert config.chunking.chunk_overlap == 200
        
        # Invalid strategy
        with pytest.raises(ValueError):
            Config(chunking={"strategy": "invalid"})
        
        # Invalid overlap (too large)
        with pytest.raises(ValueError):
            Config(chunking={"chunk_size": 1000, "chunk_overlap": 1000})
    
    def test_retrieval_config_validation(self):
        """Test retrieval configuration validation."""
        # Valid config
        retrieval_config = {
            "top_k": 5,
            "similarity_threshold": 0.8,
            "retrieval_mode": "hybrid",
        }
        
        config = Config(retrieval=retrieval_config)
        assert config.retrieval.retrieval_mode == "hybrid"
        
        # Invalid similarity threshold
        with pytest.raises(ValueError):
            Config(retrieval={"similarity_threshold": 1.5})
        
        # Invalid retrieval mode
        with pytest.raises(ValueError):
            Config(retrieval={"retrieval_mode": "invalid"})
