"""Main CLI application."""

import typer

from .schema import schema_app

app = typer.Typer(help="PDS - Please Deploy Stuff")

# Add schema commands
app.add_typer(schema_app, name="schema", help="YAML schema generation and management")

@app.command()
def version():
    """Show PDS version."""
    from pds import __version__
    typer.echo(f"PDS version {__version__}")

if __name__ == "__main__":
    app()