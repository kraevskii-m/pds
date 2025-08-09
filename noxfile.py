"""Nox configuration for testing across Python versions."""

import nox


@nox.session(python=["3.11", "3.12", "3.13"])
def tests(session):
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest")


@nox.session
def lint(session):
    """Run linting checks."""
    session.install("-e", ".[dev]")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session):
    """Run type checking."""
    session.install("-e", ".[dev]")
    session.run("pyright")


@nox.session
def security(session):
    """Run security checks."""
    session.install("-e", ".[dev]")
    session.run("bandit", "-r", "pds")
    session.run("safety", "check", "--json")


@nox.session
def docs(session):
    """Check documentation style."""
    session.install("-e", ".[dev]")
    session.run("pydocstyle", "pds")