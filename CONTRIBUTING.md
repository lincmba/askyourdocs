# Contributing to AskYourDocs

Thank you for your interest in contributing to AskYourDocs! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+ installed
- Git for version control
- Ollama installed and running
- Basic familiarity with RAG concepts

### Development Setup

1. **Prerequisites**:
   - Python 3.10+ installed
   - Poetry installed (`curl -sSL https://install.python-poetry.org | python3 -`)
   - Git for version control
   - Ollama installed and running (for testing)

2. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/yourusername/askyourdocs.git
   cd askyourdocs
   ```

3. **Install dependencies with Poetry**:
   ```bash
   # Install all dependencies including dev tools
   poetry install --extras "all"
   
   # Run a basic command
    poetry run askyourdocs config show
   ```

4. **Alternative: Install with pip**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev,gpu,remote]"
   ```

5. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

6. **Run tests to verify setup**:
   ```bash
   poetry run pytest
   # or just: pytest (if in poetry shell)
   ```

## 🏗️ Project Structure

```
askyourdocs/
├── src/askyourdocs/          # Main package
│   ├── core/                 # Core functionality
│   ├── document_loaders/     # File format loaders
│   ├── utils/               # Utility functions
│   └── utils/               # Utility functions
├── tests/                   # Test suite
└── pyproject.toml          # Poetry package configuration
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=askyourdocs

# Generate HTML coverage report
poetry run pytest --cov=askyourdocs --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run tests with verbose output
pytest -v
```

### Writing Tests

- Write tests for all new functionality
- Aim for >90% test coverage
- Use meaningful test names that describe the behavior
- Mock external dependencies (Ollama, file system when appropriate)
- Include both positive and negative test cases

Example test structure:
```python
class TestNewFeature:
    """Test new feature functionality."""
    
    def test_valid_input(self):
        """Test behavior with valid input."""
        # Test implementation
        pass
    
    def test_invalid_input(self):
        """Test error handling with invalid input."""
        # Test implementation
        pass
```

## 📝 Code Style

We use several tools to maintain code quality:

### Formatting
```bash
# Format code with Black
poetry run black src/ tests/

# Lint and fix with Ruff
poetry run ruff check src/ tests/
poetry run ruff check --fix src/ tests/
```

### Linting
```bash
# Lint with Ruff
poetry run ruff check src/ tests/

# Type checking with MyPy
poetry run mypy src/

# Run all checks
poetry run pre-commit run --all-files
```

### Pre-commit Hooks

The pre-commit configuration automatically runs:
- Black (code formatting)
- Ruff (linting)
- MyPy (type checking)
- Poetry dependency checks
- Basic file checks

## 📋 Contributing Guidelines

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Ensure quality checks pass**:
   ```bash
   poetry run pytest
   poetry run pre-commit run --all-files
   ```

### Commit Message Format

We follow conventional commits format:

- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

Example: `feat: add support for Excel file ingestion`

### Code Review Process

All contributions go through code review:

1. **Automated checks** must pass (tests, linting, type checking)
2. **Manual review** by maintainers
3. **Integration testing** for significant changes
4. **Documentation updates** if needed

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment information**:
   - Python version
   - Poetry version (if using Poetry)
   - AskYourDocs version
   - Operating system
   - Ollama version
5. **Log output** (if available)
6. **Sample files** (if relevant and non-confidential)

## 💡 Feature Requests

For new features, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and motivation
3. **Propose a solution** if you have ideas
4. **Consider backwards compatibility**
5. **Think about configuration options**


## 🏷️ Areas for Contribution

### High Priority
- **Additional file format support** (Excel, Jupyter notebooks, etc.)
- **Performance optimizations** for large document collections
- **Advanced chunking strategies** (semantic, hierarchical)
- **Query result ranking improvements**
- **Remote LLM provider integrations** (Cohere, Together AI, etc.)
- **Configuration validation and error handling**

### Medium Priority
- **Integration with other LLM providers** (OpenAI, Anthropic)
- **Advanced document preprocessing** (OCR, table extraction)
- **Plugin system** for custom document loaders
- **Web interface** (optional GUI)
- **Conversation history and context**
- **Batch processing tools**

### Documentation
- **Tutorial articles** for specific use cases
- **Video guides** for getting started
- **API documentation** improvements
- **Troubleshooting guides** for common issues
- **Configuration examples** for different use cases
- **Performance tuning guides**

## 🔒 Security

### Reporting Security Issues

Please DO NOT file public issues for security vulnerabilities. Instead:

1. Email security@askyourdocs.dev
2. Include detailed information about the vulnerability
3. Provide steps to reproduce if possible
4. Allow time for patch development before public disclosure

### Security Guidelines

- Never commit API keys or sensitive data
- Validate all user inputs
- Use safe file handling practices
- Follow principle of least privilege
- Keep dependencies updated

## 📞 Getting Help

- **Documentation**: Check the README and docs first
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: File issues for bugs and feature requests
- **Discord**: Join our community Discord (link in README)

## 🎯 Development Tips

### Working with LlamaIndex

- Understand the Settings global configuration system
- Understand the Document/Node/Index architecture
- Use the Settings global configuration appropriately
- Test with different chunk sizes and overlap settings
- Monitor memory usage with large document sets

### ChromaDB Integration

- Test with different providers (local vs remote)
- Validate API key handling and security
- Test error scenarios (network issues, invalid keys)
- Monitor token usage for remote providers

### ChromaDB Integration

- Understand collection management
- Test persistence and loading
- Monitor vector store size and performance
- Handle concurrent access properly

### CLI Development

- Follow Poetry best practices for dependency management
- Use Rich for all terminal output
- Provide helpful error messages
- Include progress indicators for long operations
- Test commands with various input combinations

### Performance Considerations

- Test with both local and remote models
- Profile memory usage with large datasets
- Optimize embedding batch processing
- Consider lazy loading for large indices
- Test startup time optimization

## 📈 Release Process

1. **Version bump** in `pyproject.toml` and `__init__.py`
2. **Update CHANGELOG.md** with new features/fixes
3. **Run quality checks**: `poetry run pre-commit run --all-files`
4. **Build package**: `poetry build`
3. **Tag release** with semantic version
5. **Automated PyPI deployment** via GitHub Actions
5. **Update documentation** if needed

Thank you for contributing to AskYourDocs! 🙏