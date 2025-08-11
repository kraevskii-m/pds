"""Schema CLI commands for generating YAML autocompletion."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pds.schema import DynamicSchemaGenerator

schema_app = typer.Typer(name="schema")
console = Console()


@schema_app.command("generate")
def generate_schema(
    output: str = typer.Option(
        "pds-schema.json", "--output", "-o", help="Output file path"
    ),
    providers: list[str] | None = typer.Option(
        None, "--provider", "-p", help="Specific providers to include"
    ),
    live: bool = typer.Option(
        False, "--live", help="Fetch live data from provider APIs"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Skip cache and force API calls"
    ),
    force_refresh: bool = typer.Option(False, "--refresh", help="Force refresh cache"),
):
    """Generate JSON Schema for pds.yaml autocompletion."""

    async def _generate():
        generator = DynamicSchemaGenerator()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                if live or force_refresh:
                    task = progress.add_task(
                        "Fetching live data from APIs...", total=None
                    )
                else:
                    task = progress.add_task("Generating schema...", total=None)

                schema = await generator.generate_schema(
                    providers=providers,
                    use_cache=not no_cache,
                    force_refresh=force_refresh,
                )

                progress.update(task, description="Writing schema file...")

                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    json.dump(schema, f, indent=2)

                progress.update(task, description="✅ Schema generated!", completed=100)

            console.print(
                f"✅ Schema saved to: [bold green]{output_path.absolute()}[/]"
            )

            if live:
                console.print("🌐 Used live API data")

            # Show providers included
            if providers:
                console.print(f"📦 Providers: {', '.join(providers)}")
            else:
                console.print("📦 All available providers included")

        except Exception as e:
            console.print(f"❌ Failed to generate schema: [red]{e}[/]")
            raise typer.Exit(1)

        finally:
            await generator.close()

    asyncio.run(_generate())


@schema_app.command("refresh")
def refresh_cache(
    provider: str | None = typer.Argument(
        None, help="Provider to refresh (all if not specified)"
    ),
):
    """Refresh API cache for providers."""

    async def _refresh():
        from pds.schema.cache import SchemaCache

        cache = SchemaCache()

        if provider:
            cleared = await cache.clear_cache(provider)
            if cleared:
                console.print(f"✅ Cache cleared for [bold]{provider}[/]")
            else:
                console.print(f"⚠️  No cache found for [bold]{provider}[/]")
        else:
            cleared = await cache.clear_cache()
            console.print(f"✅ Cleared cache for [bold]{cleared}[/] providers")

    asyncio.run(_refresh())


@schema_app.command("status")
def cache_status():
    """Show cache status for all providers."""

    async def _status():
        from pds.schema.cache import SchemaCache

        cache = SchemaCache()
        cache_info = await cache.get_cache_info()

        if not cache_info:
            console.print("📦 No cached data found")
            return

        table = Table(title="API Cache Status")
        table.add_column("Provider", style="bold")
        table.add_column("Status")
        table.add_column("Last Updated")
        table.add_column("Age (hours)")
        table.add_column("Regions")
        table.add_column("Size (KB)")

        for provider_name, info in cache_info.items():
            if "error" in info:
                table.add_row(provider_name, "❌ Corrupted", "-", "-", "-", "-")
            else:
                status = "✅ Cached" if info["age_hours"] < 6 else "⏰ Stale"
                size_kb = round(info["file_size"] / 1024, 1)

                table.add_row(
                    provider_name,
                    status,
                    info["timestamp"],
                    str(info["age_hours"]),
                    str(info["regions_count"]),
                    f"{size_kb}KB",
                )

        console.print(table)

    asyncio.run(_status())


@schema_app.command("install")
def install_schema(
    editor: str = typer.Option(
        "vscode", "--editor", "-e", help="Editor to install for (vscode, nvim)"
    ),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace directory"),
    schema_file: str = typer.Option(
        "pds-schema.json", "--schema", "-s", help="Schema file path"
    ),
):
    """Install schema configuration for editors."""
    workspace_path = Path(workspace).resolve()
    schema_path = Path(schema_file).resolve()

    if not schema_path.exists():
        console.print(f"❌ Schema file not found: [red]{schema_path}[/]")
        console.print("Run [bold]pds schema generate[/] first")
        raise typer.Exit(1)

    if editor == "vscode":
        vscode_dir = workspace_path / ".vscode"
        vscode_dir.mkdir(exist_ok=True)

        settings_file = vscode_dir / "settings.json"

        # Load existing settings or create new
        settings = {}
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
            except json.JSONDecodeError:
                console.print("⚠️  Existing settings.json is invalid, creating new one")

        # Add YAML schema mapping
        if "yaml.schemas" not in settings:
            settings["yaml.schemas"] = {}

        # Use relative path if schema is in workspace
        try:
            relative_schema = schema_path.relative_to(workspace_path)
            schema_key = f"./{relative_schema}"
        except ValueError:
            schema_key = str(schema_path)

        settings["yaml.schemas"][schema_key] = "pds.yaml"

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        console.print(f"✅ VS Code configuration updated: [green]{settings_file}[/]")
        console.print("💡 Restart VS Code to activate YAML autocompletion")

    elif editor == "nvim":
        console.print("📝 Add this to your Neovim LSP configuration:")
        console.print("")
        console.print(f"""[dim]require('lspconfig').yamlls.setup({{
  settings = {{
    yaml = {{
      schemas = {{
        ["{schema_path}"] = "pds.yaml"
      }}
    }}
  }}
}})[/]""")

    else:
        console.print(f"❌ Unsupported editor: [red]{editor}[/]")
        console.print("Supported editors: vscode, nvim")
        raise typer.Exit(1)


@schema_app.command("validate")
def validate_config(
    config_file: str = typer.Argument(
        "pds.yaml", help="Configuration file to validate"
    ),
):
    """Validate pds.yaml against generated schema."""

    async def _validate():
        config_path = Path(config_file)

        if not config_path.exists():
            console.print(f"❌ Config file not found: [red]{config_path}[/]")
            raise typer.Exit(1)

        try:
            import yaml

            with open(config_path) as f:
                config_data = yaml.safe_load(f)
        except Exception as e:
            console.print(f"❌ Failed to parse YAML: [red]{e}[/]")
            raise typer.Exit(1)

        generator = DynamicSchemaGenerator()

        try:
            errors = await generator.validate_config(config_data)

            if not errors:
                console.print("✅ Configuration is valid!")
            else:
                console.print("❌ Configuration validation errors:")
                for error in errors:
                    console.print(f"  • [red]{error}[/]")
                raise typer.Exit(1)

        finally:
            await generator.close()

    asyncio.run(_validate())

