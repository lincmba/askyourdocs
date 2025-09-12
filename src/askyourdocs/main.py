#!/usr/bin/env python3
"""
Main CLI entry point for AskYourDocs.

This module provides the Click-based command-line interface for all
AskYourDocs functionality including document ingestion, querying, and configuration.
"""

import sys
import traceback
from pathlib import Path
from typing import Optional, Tuple, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from . import __version__
from .core.config import get_config, ConfigManager
from .core.ingestion import DocumentIngestor
from .core.retrieval import QueryEngine
from .core.storage import VectorStoreManager
from .utils.logging import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, version: bool, verbose: bool) -> None:
    """
    AskYourDocs - Privacy-first, local-only document Q&A CLI tool.

    Transform your document collections into an intelligent Q&A system
    using advanced RAG technology. All processing happens locally.
    """
    if version:
        console.print(f"AskYourDocs v{__version__}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                Text.from_markup(
                    f"[bold blue]AskYourDocs v{__version__}[/bold blue]\n"
                    "[dim]Privacy-first document Q&A system[/dim]\n\n"
                    "Quick start:\n"
                    "  [bold]askyourdocs ingest[/bold]           Index documents\n"
                    '  [bold]askyourdocs ask "question"[/bold]   Ask questions\n'
                    "  [bold]askyourdocs status[/bold]          Check status\n\n"
                    "Use [bold]--help[/bold] with any command for more information."
                ),
                title="🔍📚 Welcome to AskYourDocs",
                border_style="blue",
            )
        )
        return

    # Set up logging based on verbosity
    setup_logging(verbose)

    # Ensure configuration exists
    try:
        get_config()
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("Run [bold]askyourdocs config reset[/bold] to restore defaults")
        sys.exit(1)


def _check_prerequisites(config) -> Tuple[bool, List[str]]:
    """Check if all prerequisites are met for the current configuration."""
    issues = []

    # Check Ollama availability for local models
    if config.model.provider == "ollama":
        try:
            import requests

            response = requests.get(f"{config.model.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                issues.append("Ollama server not responding")
            else:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if config.model.name not in model_names:
                    issues.append(f"Model '{config.model.name}' not found in Ollama")
                    issues.append(
                        f"Available models: {', '.join(model_names) if model_names else 'None'}"
                    )
                    issues.append(f"Download with: ollama pull {config.model.name}")
        except Exception:
            issues.append("Cannot connect to Ollama server")
            issues.append("Start Ollama with: ollama serve")

    # Check API keys for remote providers
    elif config.is_remote_provider() and not config.has_api_key():
        provider = config.model.provider.upper()
        issues.append(f"{provider} API key required but not found")
        if provider == "OPENAI":
            issues.append("Set OPENAI_API_KEY environment variable or add to config")
        elif provider == "ANTHROPIC":
            issues.append("Set ANTHROPIC_API_KEY environment variable or add to config")
        elif provider == "AZURE":
            issues.append("Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")

    return len(issues) == 0, issues


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--include", help="File patterns to include (e.g., '*.pdf,*.docx')")
@click.option("--exclude", help="File patterns to exclude (e.g., 'temp/*')")
@click.option("--force", is_flag=True, help="Force rebuild of entire index")
@click.option("--watch", is_flag=True, help="Watch directory for changes")
@click.option("--chunk-size", type=int, help="Override chunk size")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def ingest(
    path: Path,
    include: Optional[str],
    exclude: Optional[str],
    force: bool,
    watch: bool,
    chunk_size: Optional[int],
    verbose: bool,
) -> None:
    """Index documents from PATH (directory or single file) into the vector database."""
    try:
        config = get_config()
        if chunk_size:
            config.chunking.chunk_size = chunk_size

        # Check prerequisites before starting
        prereqs_ok, issues = _check_prerequisites(config)
        if not prereqs_ok:
            console.print("❌ [red]Prerequisites not met:[/red]")
            for issue in issues:
                console.print(f"   • {issue}")
            console.print(
                "\n💡 [blue]Run 'askyourdocs status' for more information[/blue]"
            )
            sys.exit(1)

        setup_logging(verbose)

        with console.status("[bold blue]Initializing document ingestor..."):
            ingestor = DocumentIngestor(config)

        if watch:
            if path.is_file():
                console.print("❌ [red]Watch mode only works with directories[/red]")
                sys.exit(1)
            console.print(
                "👀 [bold]Watching for changes... Press Ctrl+C to stop[/bold]"
            )
            ingestor.watch_directory(path, include, exclude)
        else:
            ingestor.ingest_directory(
                path,
                include_patterns=include.split(",") if include else None,
                exclude_patterns=exclude.split(",") if exclude else None,
                force_rebuild=force,
            )

        console.print("✅ [bold green]Ingestion completed successfully![/bold green]")

    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        console.print(f"❌ [red]Ingestion failed: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("question", type=str)
@click.option("--top-k", type=int, help="Number of relevant chunks to retrieve")
@click.option(
    "--mode",
    type=click.Choice(["compact", "tree_summarize", "accumulate"]),
    help="Response generation mode",
)
@click.option("--stream", is_flag=True, help="Stream response as it's generated")
@click.option("--no-sources", is_flag=True, help="Don't show source citations")
@click.option("--threshold", type=float, help="Similarity threshold (0.0-1.0)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def ask(
    question: str,
    top_k: Optional[int],
    mode: Optional[str],
    stream: bool,
    no_sources: bool,
    threshold: Optional[float],
    verbose: bool,
) -> None:
    """Ask a question about your documents."""
    try:
        config = get_config()
        setup_logging(verbose)

        # Override config with command options
        if top_k:
            config.retrieval.top_k = top_k
        if threshold:
            config.retrieval.similarity_threshold = threshold
        if mode:
            config.llamaindex.response_mode = mode

        # Check prerequisites before querying
        prereqs_ok, issues = _check_prerequisites(config)
        if not prereqs_ok:
            console.print("❌ [red]Prerequisites not met:[/red]")
            for issue in issues:
                console.print(f"   • {issue}")
            sys.exit(1)

        with console.status("[bold blue]Initializing query engine..."):
            engine = QueryEngine(config)

        if not engine.is_ready():
            console.print(
                "❌ [red]No documents indexed. Run 'askyourdocs ingest' first.[/red]"
            )
            sys.exit(1)

        console.print(f"🤔 [bold]Question:[/bold] {question}")
        console.print()

        if stream:
            response = engine.stream_query(question)
            console.print("🤖 [bold]Answer:[/bold]")
            for chunk in response:
                console.print(chunk, end="")
            console.print("\n")
        else:
            with console.status("[bold blue]Thinking..."):
                response = engine.query(question)

            console.print("🤖 [bold]Answer:[/bold]")
            console.print(response.response)
            console.print()

        if not no_sources and hasattr(response, "source_nodes"):
            console.print("📚 [bold]Sources:[/bold]")
            for i, node in enumerate(response.source_nodes[:3], 1):
                source_file = node.metadata.get("file_path", "Unknown")
                score = node.score if hasattr(node, "score") else 0.0
                console.print(f"  {i}. {source_file} (score: {score:.3f})")
                if verbose:
                    preview = node.text[:100].replace("\n", " ")
                    console.print(f"     [dim]Preview: {preview}...[/dim]")

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        console.print(f"❌ [red]Query failed: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option("--reset", is_flag=True, help="Delete and rebuild from scratch")
@click.option("--optimize", is_flag=True, help="Optimize vector store")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def refresh(reset: bool, optimize: bool, verbose: bool) -> None:
    """Refresh the document index."""
    try:
        config = get_config()
        setup_logging(verbose)

        with console.status("[bold blue]Refreshing index..."):
            storage_manager = VectorStoreManager(config)

            if reset:
                storage_manager.reset()
                console.print("🔄 [yellow]Index reset complete[/yellow]")
            elif optimize:
                storage_manager.optimize()
                console.print("⚡ [green]Index optimization complete[/green]")
            else:
                # Incremental refresh
                ingestor = DocumentIngestor(config)
                ingestor.refresh_index()
                console.print("🔄 [green]Index refresh complete[/green]")

    except Exception as e:
        logger.error(f"Refresh failed: {e}", exc_info=True)
        console.print(f"❌ [red]Refresh failed: {e}[/red]")
        sys.exit(1)


@cli.command()
def status() -> None:
    """Show system status and statistics."""
    try:
        config = get_config()
        storage_manager = VectorStoreManager(config)
        stats = storage_manager.get_stats()

        # Check configuration validity
        config_manager = ConfigManager()
        config_valid, config_issues = config_manager.validate_config()

        status_text = Text()
        status_text.append("📊 AskYourDocs Status\n", style="bold blue")
        status_text.append(
            f"├── 📁 Documents: {stats['document_count']:,} files indexed\n"
        )
        status_text.append(f"├── 🧩 Chunks: {stats['chunk_count']:,} text chunks\n")
        status_text.append(f"├── 💾 Storage: {stats['storage_size']} vector data\n")
        status_text.append(
            f"├── 🧠 Model: {config.model.name} ({config.model.provider})\n"
        )
        status_text.append(f"├── 🔍 Embeddings: {config.embedding.model}\n")
        status_text.append(f"└── ⚙️ Config: {config.config_path}")

        console.print(Panel(status_text, title="System Status", border_style="blue"))

        # Show configuration issues
        if not config_valid:
            console.print("\n⚠️  [yellow]Configuration Issues:[/yellow]")
            for issue in config_issues:
                console.print(f"   • {issue}")

            # Provide helpful suggestions
            if config.model.provider == "ollama":
                console.print("\n💡 [blue]To fix Ollama issues:[/blue]")
                console.print("   1. Start Ollama: [bold]ollama serve[/bold]")
                console.print(
                    f"   2. Download model: [bold]ollama pull {config.model.name}[/bold]"
                )
                console.print("   3. List models: [bold]ollama list[/bold]")
            elif config.is_remote_provider():
                provider = config.model.provider.upper()
                console.print(f"\n💡 [blue]To fix {provider} issues:[/blue]")
                if provider == "OPENAI":
                    console.print(
                        "   1. Get API key: https://platform.openai.com/api-keys"
                    )
                    console.print(
                        "   2. Set environment: [bold]export OPENAI_API_KEY=your-key[/bold]"
                    )
                    console.print(
                        "   3. Or add to config: [bold]askyourdocs config set model.api_key your-key[/bold]"
                    )
                elif provider == "ANTHROPIC":
                    console.print(
                        "   1. Get API key: https://console.anthropic.com/settings/keys"
                    )
                    console.print(
                        "   2. Set environment: [bold]export ANTHROPIC_API_KEY=your-key[/bold]"
                    )
                    console.print(
                        "   3. Or add to config: [bold]askyourdocs config set model.api_key your-key[/bold]"
                    )
                elif provider == "AZURE":
                    console.print("   1. Get API key from Azure OpenAI resource")
                    console.print(
                        "   2. Set environment: [bold]export AZURE_OPENAI_API_KEY=your-key[/bold]"
                    )
                    console.print(
                        "   3. Set endpoint: [bold]export AZURE_OPENAI_ENDPOINT=your-endpoint[/bold]"
                    )

        # Health checks
        if not storage_manager.is_ready():
            console.print(
                "⚠️  [yellow]No documents indexed. Run 'askyourdocs ingest' to get started.[/yellow]"
            )
        else:
            console.print("✅ [green]System ready for queries![/green]")

    except Exception as e:
        console.print(f"❌ [red]Failed to get status: {e}[/red]")
        sys.exit(1)


@cli.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command("show")
@click.option("--section", help="Show specific config section")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json", "table"]),
    default="table",
    help="Output format",
)
def config_show(section: Optional[str], output_format: str) -> None:
    """Show current configuration."""
    try:
        config = get_config()
        manager = ConfigManager()

        if section:
            value = manager.get_value(section)
            if output_format == "json":
                import json

                console.print(json.dumps({section: value}, indent=2))
            else:
                console.print(f"[bold]{section}:[/bold] {value}")
        else:
            config_dict = config.model_dump()

            if output_format == "json":
                console.print_json(data=config_dict)
            elif output_format == "yaml":
                console.print(
                    yaml.dump(config_dict, default_flow_style=False, indent=2)
                )
            else:
                # Table format
                table = Table(title="AskYourDocs Configuration")
                table.add_column("Section", style="cyan", no_wrap=True)
                table.add_column("Setting", style="magenta")
                table.add_column("Value", style="green")

                for section_name, section_data in config_dict.items():
                    if isinstance(section_data, dict):
                        for key, value in section_data.items():
                            table.add_row(section_name, key, str(value))
                    else:
                        table.add_row("", section_name, str(section_data))

                console.print(table)

    except Exception as e:
        console.print(f"❌ [red]Failed to show config: {e}[/red]")
        sys.exit(1)


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    try:
        manager = ConfigManager()
        manager.set_value(key, value)
        console.print(f"✅ [green]Set {key} = {value}[/green]")

    except Exception as e:
        console.print(f"❌ [red]Failed to set config: {e}[/red]")
        sys.exit(1)


@config.command("reset")
def config_reset() -> None:
    """Reset configuration to defaults."""
    try:
        manager = ConfigManager()
        manager.reset_to_defaults()
        console.print("✅ [green]Configuration reset to defaults[/green]")

    except Exception as e:
        console.print(f"❌ [red]Failed to reset config: {e}[/red]")
        sys.exit(1)


@config.command("validate")
def config_validate() -> None:
    """Validate current configuration."""
    try:
        manager = ConfigManager()
        is_valid, issues = manager.validate_config()

        if is_valid:
            console.print("✅ [green]Configuration is valid![/green]")
        else:
            console.print("❌ [red]Configuration issues found:[/red]")
            for issue in issues:
                console.print(f"   • {issue}")

    except Exception as e:
        console.print(f"❌ [red]Failed to validate config: {e}[/red]")
        sys.exit(1)


@config.command("setup")
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "anthropic", "azure"]),
    help="LLM provider to configure",
)
def config_setup(provider: Optional[str]) -> None:
    """Interactive configuration setup."""
    try:
        manager = ConfigManager()

        if not provider:
            console.print("🔧 [bold]AskYourDocs Configuration Setup[/bold]")
            console.print("\nChoose your preferred LLM provider:")
            console.print("1. [green]Ollama[/green] - Local, private, free")
            console.print("2. [blue]OpenAI[/blue] - Remote, requires API key")
            console.print("3. [purple]Anthropic[/purple] - Remote, requires API key")
            console.print("4. [cyan]Azure OpenAI[/cyan] - Remote, requires API key")

            choice = console.input("\nEnter choice (1-4): ").strip()
            provider_map = {
                "1": "ollama",
                "2": "openai",
                "3": "anthropic",
                "4": "azure",
            }
            provider = provider_map.get(choice, "ollama")

        console.print(f"\n🔧 [bold]Configuring {provider.title()} provider...[/bold]")

        if provider == "ollama":
            # Ollama setup
            model_name = (
                console.input(f"Model name [tinyllama:1.1b]: ").strip()
                or "tinyllama:1.1b"
            )
            base_url = (
                console.input(f"Ollama URL [http://localhost:11434]: ").strip()
                or "http://localhost:11434"
            )

            manager.set_value("model.provider", provider)
            manager.set_value("model.name", model_name)
            manager.set_value("model.base_url", base_url)

        elif provider == "openai":
            # OpenAI setup
            api_key = console.input("OpenAI API Key: ").strip()
            model_name = (
                console.input("Model name [gpt-3.5-turbo]: ").strip() or "gpt-3.5-turbo"
            )

            if not api_key:
                console.print("❌ [red]API key is required for OpenAI[/red]")
                return

            manager.set_value("model.provider", provider)
            manager.set_value("model.name", model_name)
            manager.set_value("model.api_key", api_key)

        elif provider == "anthropic":
            # Anthropic setup
            api_key = console.input("Anthropic API Key: ").strip()
            model_name = (
                console.input("Model name [claude-3-5-sonnet-20241022]: ").strip()
                or "claude-3-5-sonnet-20241022"
            )

            if not api_key:
                console.print("❌ [red]API key is required for Anthropic[/red]")
                return

            manager.set_value("model.provider", provider)
            manager.set_value("model.name", model_name)
            manager.set_value("model.api_key", api_key)

        elif provider == "azure":
            # Azure OpenAI setup
            api_key = console.input("Azure OpenAI API Key: ").strip()
            endpoint = console.input("Azure OpenAI Endpoint: ").strip()
            deployment = console.input("Deployment name: ").strip()

            if not all([api_key, endpoint, deployment]):
                console.print(
                    "❌ [red]API key, endpoint, and deployment are required for Azure[/red]"
                )
                return

            manager.set_value("model.provider", provider)
            manager.set_value("model.api_key", api_key)
            manager.set_value("model.azure_endpoint", endpoint)
            manager.set_value("model.azure_deployment", deployment)

        console.print(
            f"✅ [green]Successfully configured {provider.title()} provider![/green]"
        )
        console.print("💡 Test your setup with: [bold]askyourdocs status[/bold]")

    except Exception as e:
        console.print(f"❌ [red]Setup failed: {e}[/red]")
        sys.exit(1)


@config.command("path")
def config_path() -> None:
    """Show configuration file path."""
    try:
        config = get_config()
        console.print(f"📄 Configuration file: [bold]{config.config_path}[/bold]")

    except Exception as e:
        console.print(f"❌ [red]Failed to get config path: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--limit", type=int, default=10, help="Maximum number of results")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def search(query: str, limit: int, output_format: str) -> None:
    """Fast keyword search through documents."""
    try:
        config = get_config()
        engine = QueryEngine(config)

        if not engine.is_ready():
            console.print(
                "❌ [red]No documents indexed. Run 'askyourdocs ingest' first.[/red]"
            )
            sys.exit(1)

        results = engine.keyword_search(query, limit=limit)

        if output_format == "json":
            import json

            console.print(json.dumps(results, indent=2))
        else:
            console.print(f"🔍 [bold]Search results for '{query}':[/bold]")
            for i, result in enumerate(results, 1):
                console.print(f"  {i}. {result['file']} (score: {result['score']:.3f})")
                console.print(f"     [dim]{result['preview']}[/dim]\n")

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        console.print(f"❌ [red]Search failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--top-k", type=int, help="Number of relevant chunks to retrieve")
@click.option("--stream", is_flag=True, help="Stream responses")
def interactive(top_k: Optional[int], stream: bool) -> None:
    """Start interactive Q&A session."""
    try:
        config = get_config()
        if top_k:
            config.retrieval.top_k = top_k

        engine = QueryEngine(config)

        if not engine.is_ready():
            console.print(
                "❌ [red]No documents indexed. Run 'askyourdocs ingest' first.[/red]"
            )
            sys.exit(1)

        console.print(
            Panel.fit(
                "🤖 [bold]Interactive Q&A Mode[/bold]\n"
                "Ask questions about your documents. Type 'exit' to quit.",
                title="AskYourDocs Interactive",
                border_style="green",
            )
        )

        while True:
            try:
                question = console.input("\n[bold blue]❓ Your question:[/bold blue] ")

                if question.lower() in ["exit", "quit", "q"]:
                    console.print("👋 [dim]Goodbye![/dim]")
                    break

                if not question.strip():
                    continue

                console.print()

                if stream:
                    response = engine.stream_query(question)
                    console.print("🤖 [bold]Answer:[/bold]")
                    for chunk in response:
                        console.print(chunk, end="")
                    console.print("\n")
                else:
                    with console.status("[bold blue]Thinking..."):
                        response = engine.query(question)

                    console.print("🤖 [bold]Answer:[/bold]")
                    console.print(response.response)

                    if hasattr(response, "source_nodes"):
                        console.print("\n📚 [bold]Sources:[/bold]")
                        for i, node in enumerate(response.source_nodes[:2], 1):
                            source_file = node.metadata.get("file_path", "Unknown")
                            console.print(f"  {i}. {source_file}")

            except KeyboardInterrupt:
                console.print("\n👋 [dim]Goodbye![/dim]")
                break

    except Exception as e:
        logger.error(f"Interactive mode failed: {e}", exc_info=True)
        console.print(f"❌ [red]Interactive mode failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file path (e.g., backup.tar.gz)",
)
@click.option("--include-config", is_flag=True, help="Include configuration in backup")
def export(output: str, include_config: bool) -> None:
    """Export vector database and optionally configuration."""
    try:
        config = get_config()
        storage_manager = VectorStoreManager(config)

        with console.status(f"[bold blue]Creating backup..."):
            storage_manager.export_data(output, include_config)

        console.print(f"✅ [green]Backup created: {output}[/green]")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        console.print(f"❌ [red]Export failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    required=True,
    help="Input backup file path",
)
@click.option("--merge", is_flag=True, help="Merge with existing data")
def import_data(input: str, merge: bool) -> None:
    """Import vector database from backup."""
    try:
        config = get_config()
        storage_manager = VectorStoreManager(config)

        with console.status(f"[bold blue]Importing backup..."):
            storage_manager.import_data(input, merge)

        console.print(f"✅ [green]Import completed: {input}[/green]")

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        console.print(f"❌ [red]Import failed: {e}[/red]")
        sys.exit(1)


# Alias import command to avoid Python keyword conflict
cli.add_command(import_data, name="import")


def main() -> None:
    """Main entry point with global exception handling."""
    try:
        cli()
    except Exception as e:
        console.print(f"❌ [red]Unexpected error: {e}[/red]")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
