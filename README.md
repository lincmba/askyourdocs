# AskYourDocs 🔍📚

[![PyPI version](https://badge.fury.io/py/askyourdocs.svg)](https://badge.fury.io/py/askyourdocs)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AskYourDocs** is a privacy-first, local-only CLI tool that transforms your document collections into an intelligent Q&A system. Using advanced RAG (Retrieval Augmented Generation) technology, it allows you to ask natural language questions about your documents and get accurate, contextual answers with source citations.

## ✨ Key Features

- 🔒 **100% Privacy**: All processing happens locally, your documents never leave your machine
- 🧠 **Intelligent Q&A**: Ask natural language questions and get contextual answers
- 📄 **Multi-Format Support**: PDF, Word, PowerPoint, Markdown, code files, and more
- ⚡ **Fast Retrieval**: Hybrid search combining semantic and keyword matching
- 🎯 **Source Attribution**: Every answer includes citations to source documents
- 🔄 **Incremental Updates**: Only processes changed files for efficiency
- 🎨 **Beautiful CLI**: Rich terminal output with progress bars and colors
- ⚙️ **Highly Configurable**: YAML-based configuration for all settings

## 🚀 Quick Start

### Installation

#### Option 1: Install from PyPI (Recommended)
```bash
# Basic installation (local models only)
pip install askyourdocs

# With remote LLM support
pip install askyourdocs[remote]

# With GPU acceleration
pip install askyourdocs[gpu]

# Full installation with all features
pip install askyourdocs[all]
```

#### Option 2: Install with Poetry (Development)
```bash
# Clone the repository
git clone https://github.com/lincmba/askyourdocs.git
cd askyourdocs

# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install with all extras for development
poetry install --extras "all"

# Run a basic command
poetry run askyourdocs --help 
```

#### Option 3: Install from Source (Advanced)
```bash
# Clone the repository
git clone https://github.com/lincmba/askyourdocs.git
cd askyourdocs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install with optional dependencies
pip install -e ".[gpu,remote,dev]"
```

### Setup Prerequisites

#### For Local Processing (Recommended)

1. **Install Ollama** (for local LLM inference):
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Windows (WSL)
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama and download the default model**:
   ```bash
   # Start Ollama service
   ollama serve
   
   # In another terminal, download the default lightweight model
   ollama pull tinyllama:1.1b
   
   # Or download a more capable model (larger download)
   ollama pull llama3.1:8b
   ```

#### For Remote Processing (Optional)

If you prefer to use remote LLM providers, you'll need API keys:

**OpenAI Setup:**
```bash
# Install with OpenAI support
pip install askyourdocs[openai]

# Set your API key
export OPENAI_API_KEY="your-api-key-here"

# Configure for OpenAI
askyourdocs config setup --provider openai
```

**Anthropic Setup:**
```bash
# Install with Anthropic support
pip install askyourdocs[remote]
# 1. Install with remote provider support
pip install askyourdocs[remote]
export ANTHROPIC_API_KEY="your-api-key-here"
# 2. Get your API key from https://console.anthropic.com/
# Configure for Anthropic

# 3. Configure for Anthropic
askyourdocs config setup --provider anthropic

# Or set directly in config
askyourdocs config set model.provider anthropic
askyourdocs config set model.name claude-3-sonnet-20240229
askyourdocs config set model.api_key your-api-key-here
```

**Azure OpenAI Setup:**
```bash
# Install with Azure support
pip install askyourdocs[azure]

# Set your credentials
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"

# Configure for Azure
askyourdocs config setup --provider azure
```

### Basic Usage

1. **Index your documents**:
   ```bash
   # Index documents in current directory
   askyourdocs ingest
   
   # Index specific directory
   askyourdocs ingest ./my-documents
   
   # Index with progress and verbose output
   askyourdocs ingest ./docs --verbose
   ```

2. **Ask questions**:
   ```bash
   # Ask a question
   askyourdocs ask "What are the main conclusions in the research papers?"
   
   # Ask with specific number of sources
   askyourdocs ask "How does the API authentication work?" --top-k 5
   
   # Get detailed response with full sources
   askyourdocs ask "Summarize the project requirements" --verbose
   ```

3. **Interactive mode**:
   ```bash
   # Start interactive session
   askyourdocs interactive
   
   # In interactive mode:
   > What is the project timeline?
   > Can you explain the technical architecture?
   > exit
   ```

4. **Check system status**:
   ```bash
   # View system status and configuration
   askyourdocs status
   
   # Validate configuration
   askyourdocs config validate
   ```

5. **Configuration management**:
   ```bash
   # Interactive setup
   askyourdocs config setup
   
   # View configuration
   askyourdocs config show
   
   # Set specific values
   askyourdocs config set model.temperature 0.2
   askyourdocs config set retrieval.top_k 10
   ```

## 📖 Command Reference

### Core Commands

#### `ingest` - Index Documents
```bash
askyourdocs ingest [PATH] [OPTIONS]

# Examples:
askyourdocs ingest                          # Current directory
askyourdocs ingest ./documents             # Specific path
askyourdocs ingest --include "*.pdf,*.md"  # Filter file types
askyourdocs ingest --exclude "temp/*"      # Exclude patterns
askyourdocs ingest --force                 # Rebuild entire index
askyourdocs ingest --watch                 # Watch for changes
```

**Options:**
- `--include TEXT`: File patterns to include (e.g., "*.pdf,*.docx")
- `--exclude TEXT`: File patterns to exclude (e.g., "temp/*,*.log")
- `--force`: Force rebuild of entire index
- `--watch`: Watch directory for changes and auto-update
- `--chunk-size INTEGER`: Override chunk size for processing
- `--verbose`: Show detailed processing information

#### `ask` - Query Documents
```bash
askyourdocs ask "your question" [OPTIONS]

# Examples:
askyourdocs ask "What is the main thesis?"
askyourdocs ask "How do I configure the database?" --top-k 5
askyourdocs ask "Summarize key findings" --mode compact
askyourdocs ask "What are the requirements?" --stream
```

**Options:**
- `--top-k INTEGER`: Number of relevant chunks to retrieve (default: 5)
- `--mode TEXT`: Response mode (compact/tree_summarize/accumulate)
- `--stream`: Stream response as it's generated
- `--no-sources`: Don't show source citations
- `--threshold FLOAT`: Similarity threshold for retrieval (0.0-1.0)

#### `search` - Fast Keyword Search
```bash
askyourdocs search "keyword" [OPTIONS]

# Examples:
askyourdocs search "authentication"
askyourdocs search "machine learning" --limit 10
askyourdocs search "API" --format json
```

#### `refresh` - Rebuild Index
```bash
askyourdocs refresh [OPTIONS]

# Examples:
askyourdocs refresh                    # Rebuild current index
askyourdocs refresh --reset            # Delete and rebuild from scratch
askyourdocs refresh --optimize         # Optimize vector store
```

#### `status` - System Information
```bash
askyourdocs status

# Example output:
📊 AskYourDocs Status
├── 📁 Documents: 1,247 files indexed
├── 🧩 Chunks: 5,834 text chunks
├── 💾 Storage: 156.7 MB vector data
├── 🧠 Model: llama3.1:8b (Ollama)
├── 🔍 Embeddings: BAAI/bge-small-en-v1.5
└── ⚙️ Config: ~/.config/askyourdocs/config.yaml
```

### Configuration Commands

#### `config` - Manage Configuration
```bash
askyourdocs config [COMMAND] [OPTIONS]

# View current configuration
askyourdocs config show
askyourdocs config show --format yaml
askyourdocs config show --section model

# Set configuration values
askyourdocs config set model.name llama3.1:8b
askyourdocs config set chunking.chunk_size 1500
askyourdocs config set embedding.model "sentence-transformers/all-MiniLM-L6-v2"

# Interactive setup
askyourdocs config setup
askyourdocs config setup --provider openai

# Validate configuration
askyourdocs config validate

# Reset to defaults
askyourdocs config reset

# Show configuration file location
askyourdocs config path
```

### Advanced Commands

#### `interactive` - Interactive Mode
```bash
askyourdocs interactive [OPTIONS]

# Start interactive session with custom settings
askyourdocs interactive --top-k 3 --stream
```

#### `export` - Backup Data
```bash
askyourdocs export --output backup.tar.gz
askyourdocs export --output backup.tar.gz --include-config
```

#### `import` - Restore Data
```bash
askyourdocs import --input backup.tar.gz
askyourdocs import --input backup.tar.gz --merge
```

## 🛠️ Configuration

AskYourDocs uses a YAML configuration file located at `~/.config/askyourdocs/config.yaml`. You can customize all aspects of the tool:

### Local Models (Default - No API Key Required)
```yaml
model:
  provider: "ollama"           # Local Ollama server
  name: "tinyllama:1.1b"      # Lightweight model (fast, good for most tasks)
  base_url: "http://localhost:11434"
  temperature: 0.1            # Response creativity (0.0-2.0)
  max_tokens: 2048           # Maximum response length

embedding:
  provider: "huggingface"     # Local embeddings
  model: "BAAI/bge-small-en-v1.5"  # Fast, accurate embeddings
  device: "cpu"              # cpu/cuda/mps/auto
```

### Remote Models (API Key Required)

**OpenAI Configuration:**
```yaml
model:
  provider: "openai"
  name: "gpt-4"              # or gpt-3.5-turbo
  api_key: "sk-your-key-here"  # Or set OPENAI_API_KEY env var
  temperature: 0.1
  max_tokens: 2048

embedding:
  provider: "openai"         # Optional: use OpenAI embeddings
  model: "text-embedding-3-small"
  api_key: "sk-your-key-here"
```

**Anthropic Configuration:**
```yaml
model:
  provider: "anthropic"
  name: "claude-3-5-sonnet-20241022"  # Latest Claude model
  api_key: "sk-ant-your-key-here"  # Or set ANTHROPIC_API_KEY env var
  temperature: 0.1
  max_tokens: 2048

embedding:
  provider: "huggingface"  # Keep local embeddings for privacy
  model: "BAAI/bge-small-en-v1.5"
```

**Azure OpenAI Configuration:**
```yaml
model:
  provider: "azure"
  name: "gpt-4"
  api_key: "your-azure-key"
  azure_endpoint: "https://your-resource.openai.azure.com/"
  azure_deployment: "your-deployment-name"
```

### Advanced Configuration

**Document Processing:**
```yaml
chunking:
  strategy: "sentence"        # sentence/recursive/semantic/fixed
  chunk_size: 1000           # Characters per chunk (100-8000)
  chunk_overlap: 200         # Overlap between chunks
  respect_boundaries: true   # Respect sentence/paragraph boundaries
  min_chunk_size: 100        # Minimum chunk size
```

**Retrieval Settings:**
```yaml
retrieval:
  top_k: 5                   # Number of chunks to retrieve (1-50)
  similarity_threshold: 0.7   # Minimum similarity score (0.0-1.0)
  rerank: true               # Re-rank results for better relevance
  retrieval_mode: "hybrid"   # vector/keyword/hybrid
  max_context_length: 4000   # Maximum context for LLM
```

**Storage Settings:**
```yaml
storage:
  backend: "chromadb"        # Vector database backend
  path: ".askyourdocs"       # Storage directory
  compression: true          # Enable compression
  collection_name: "documents"  # Collection name
```

## 🎯 Examples

### Quick Start with Local Models
```yaml
# 1. Install and setup
pip install askyourdocs
ollama serve  # In one terminal
ollama pull tinyllama:1.1b  # In another terminal

# 2. Index your documents
askyourdocs ingest ./my-documents

# 3. Ask questions
askyourdocs ask "What are the key findings?"
```

### Using with OpenAI
```bash
# 1. Install with OpenAI support
pip install askyourdocs[openai]

# 2. Set up OpenAI
export OPENAI_API_KEY="your-api-key"
askyourdocs config setup --provider openai

# 4. Index and query your documents
askyourdocs ingest ./documents
askyourdocs ask "What are the key findings in these documents?"

# 5. Verify configuration
askyourdocs status
```

### Research Papers Analysis
```bash
# Index your research papers
askyourdocs ingest ./research-papers --include "*.pdf"

# Ask analytical questions
askyourdocs ask "What are the common methodologies across these studies?"
askyourdocs ask "Which papers mention transformer architecture?"
askyourdocs ask "Summarize the key findings about neural networks"
```

### Code Documentation
```bash
# Index your codebase documentation
askyourdocs ingest ./docs --include "*.md,*.rst"

# Query your docs
askyourdocs ask "How do I set up authentication?"
askyourdocs ask "What are the API rate limits?"
askyourdocs ask "Show me examples of database configuration"
```

### Legal Documents
```bash
# Index contracts and legal docs
askyourdocs ingest ./legal --include "*.pdf,*.docx"

# Ask specific questions
askyourdocs ask "What are the termination clauses?"
askyourdocs ask "What payment terms are specified?"
askyourdocs ask "Are there any liability limitations?"
```

## 🔧 Advanced Usage

### Custom Configuration
```bash
# Use a specific model
askyourdocs config set model.name "llama3.1:8b"

# Switch to OpenAI
askyourdocs config set model.provider "openai"
askyourdocs config set model.name "gpt-4"
askyourdocs config set model.api_key "your-key"

# Adjust chunk size for longer documents
askyourdocs config set chunking.chunk_size 1500

# Enable GPU acceleration for embeddings
askyourdocs config set embedding.device "cuda"

# Use OpenAI embeddings (requires API key)
askyourdocs config set embedding.provider "openai"

# Set custom storage location
askyourdocs config set storage.path "/my/custom/path"
```

### Monitoring and Maintenance
```bash
# Check system status
askyourdocs status

# Refresh index (incremental)
askyourdocs refresh

# Full rebuild (when changing chunk settings)
askyourdocs refresh --reset

# Optimize vector store
askyourdocs refresh --optimize
```

### Backup and Migration
```bash
# Create backup
askyourdocs export --output documents-backup.tar.gz --include-config

# Restore from backup
askyourdocs import --input documents-backup.tar.gz

# Merge with existing index
askyourdocs import --input additional-docs.tar.gz --merge
```

## 📁 Supported File Formats

| Category | Formats | Extensions |
|----------|---------|------------|
| **Documents** | PDF, Word, PowerPoint, OpenDocument | `.pdf`, `.docx`, `.pptx`, `.odt`, `.odp` |
| **Text** | Plain text, Markdown, reStructuredText | `.txt`, `.md`, `.rst`, `.csv` |
| **Code** | Source code, configuration files | `.py`, `.js`, `.java`, `.cpp`, `.yaml`, `.json` |
| **Structured** | HTML, XML, LaTeX, Jupyter | `.html`, `.xml`, `.tex`, `.ipynb` |

## 🏗️ Architecture

AskYourDocs uses a modern RAG architecture:

1. **Document Ingestion**: Files are processed and split into semantic chunks
2. **Embedding Generation**: Text chunks are converted to vector embeddings
3. **Vector Storage**: ChromaDB stores embeddings with metadata for fast retrieval
4. **Query Processing**: User questions are embedded and matched against stored vectors
5. **Context Retrieval**: Most relevant chunks are retrieved based on similarity
6. **Response Generation**: Local LLM generates answers using retrieved context

## 🛡️ Privacy & Security

- **Local Processing**: All operations happen on your machine
- **No Data Transmission**: Documents never leave your environment
- **Secure Storage**: Vector data stored locally with optional encryption
- **No Telemetry**: Zero tracking or analytics
- **Open Source**: Full transparency with auditable code

## 🔍 Troubleshooting

### Common Issues

**"Configuration issues found"**
```bash
# Check what's wrong
askyourdocs status
askyourdocs config validate

# Interactive setup
askyourdocs config setup
```

**"Ollama connection failed"**
```bash
# Check if Ollama is running
ollama list

# Start Ollama if not running
ollama serve

# Test connection
curl http://localhost:11434/api/tags

# Download the default model
ollama pull tinyllama:1.1b

# List available models
ollama list
```

**"No documents found"**
```bash
# Check current directory
askyourdocs ingest --verbose

# Specify path explicitly
askyourdocs ingest /path/to/documents

# Check supported formats
askyourdocs ingest --include "*.pdf,*.docx,*.txt"
```

**"Embedding model download failed"**
```bash
# Check internet connection and try again
askyourdocs refresh

# Use different model
askyourdocs config set embedding.model "sentence-transformers/all-MiniLM-L6-v2"
```

**"API key not found" (for remote providers)**
```bash
# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# For OpenAI
export OPENAI_API_KEY="your-key"

# Or set in config
askyourdocs config set model.provider anthropic
askyourdocs config set model.api_key "your-key"

# Verify setup
askyourdocs config validate
askyourdocs status
```

**Performance Issues**
```bash
# Reduce chunk size
askyourdocs config set chunking.chunk_size 800

# Reduce batch size
askyourdocs config set embedding.batch_size 16

# Optimize storage
askyourdocs refresh --optimize

# Switch to lighter model
askyourdocs config set model.name "tinyllama:1.1b"

# Use GPU acceleration (if available)
askyourdocs config set embedding.device "cuda"
```

### Getting Help

```bash
# Show general help
askyourdocs --help

# Show command-specific help
askyourdocs ask --help
askyourdocs ingest --help

# Show current configuration
askyourdocs config show

# Check system status
askyourdocs status
```

## 🧪 Development Setup

### Using Poetry (Recommended)

```bash
# Clone repository
git clone https://github.com/lincmba/askyourdocs.git
cd askyourdocs

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --extras "all"

# Run a basic command
 poetry run askyourdocs --help

# Install pre-commit hooks
pre-commit install
```

### Using pip (Alternative)

```bash
# Clone repository
git clone https://github.com/lincmba/askyourdocs.git
cd askyourdocs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev,gpu,remote]"

# Install pre-commit hooks
pre-commit install
```

### Development Commands

```bash
# Run with coverage
poetry run pytest
# or: pytest

# Run with coverage
poetry run pytest --cov=askyourdocs
# or: pytest --cov=askyourdocs

# Format code
poetry run black src/ tests/
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# Run all quality checks
poetry run pre-commit run --all-files

# Build package
poetry build

# Install locally for testing
poetry install
```

## 📊 Performance Benchmarks

Typical performance on modern hardware (16GB RAM, SSD):

| Operation | Small (100 docs) | Medium (1K docs) | Large (10K docs) |
|-----------|------------------|------------------|------------------|
| **Initial Ingestion** | 30 seconds | 5 minutes | 45 minutes |
| **Incremental Update** | 2 seconds | 15 seconds | 2 minutes |
| **Query Response** | 1-2 seconds | 1-3 seconds | 2-4 seconds |
| **Memory Usage** | 50MB | 150MB | 500MB |

### Model Comparison

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| **tinyllama:1.1b** | 637MB | Very Fast | Good | Quick queries, limited resources |
| **llama3.1:8b** | 4.7GB | Fast | Excellent | General purpose, best balance |
| **claude-3-5-sonnet** | Remote | Fast | Outstanding | Best reasoning, requires API key |
| **gpt-3.5-turbo** | Remote | Fast | Excellent | Remote option, requires API key |
| **gpt-4** | Remote | Medium | Outstanding | Best quality, requires API key |

*Note: Local models require initial download but then work offline. Remote models require internet and API costs.*

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LlamaIndex**: For the excellent RAG framework
- **ChromaDB**: For fast vector storage
- **Ollama**: For local LLM inference
- **Rich**: For beautiful terminal output
- **Click**: For the CLI framework

## 📞 Support
- 📧 **Email**: lincolncmba@gmail.com

---
