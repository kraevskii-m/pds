# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDS (Please Deploy Stuff) is a Python CLI tool that provides a universal deployment solution for web applications across different cloud providers and server types. It combines Terraform/OpenTofu for infrastructure provisioning, Ansible for server configuration, and supports three distinct provisioning models:

1. **TERRAFORM** - Full cloud provider integration (DigitalOcean, AWS, etc.)
2. **API** - Custom API-based providers (Contabo, OVH without Terraform)  
3. **MANUAL** - User-provided existing servers with Ansible-only deployment

## Development Commands

### Testing and Quality Assurance
```bash
# Run tests across Python versions
nox -s tests

# Run all quality checks (recommended before commits)
nox

# Individual checks
nox -s lint          # Ruff linting and formatting
nox -s typecheck     # Pyright type checking
nox -s security      # Bandit security scan + Safety dependency check
nox -s docs          # Pydocstyle documentation checks

# Run tests manually  
uv run pytest

# Type check manually
pyright
```

### Development Environment
```bash
# Setup development environment
uv sync --dev

# Install pre-commit hooks (recommended)
pre-commit install

# Run the CLI during development (use module path until entry point is fixed)
uv run python -m pds.cli.main --help

# Test schema autocompletion system
uv run python -m pds.cli.main schema generate --output pds-schema.json
uv run python -m pds.cli.main schema status
```

### Code Quality Standards
- **Linting**: Uses Ruff with line length of 88 characters
- **Type checking**: Pyright with strict mode
- **Documentation**: Google docstring convention
- **Security**: Bandit for security scanning, Safety for dependency checks

## Architecture Overview

### Core Components

**Configuration System** (`pds/config/`):
- `models.py` contains Pydantic models defining the complete configuration schema
- Main config class is `PDSConfig` with nested models for infrastructure, networking, security, etc.
- Supports environment-specific overrides and validation

**Plugin System** (`pds/plugins/`):
- `base.py` defines abstract base classes for all plugin types
- Three plugin types: `CloudProvider`, `ProxyPlugin`, `MonitoringPlugin`
- Global `PluginRegistry` manages all plugins
- Supports provider-specific hooks and lifecycle events

**Provider Types**:
- **TERRAFORM providers**: Generate and execute Terraform configurations (digitalocean.py)
- **API providers**: Make direct API calls for provisioning (planned)
- **MANUAL providers**: Work with existing user-provided servers (manual.py)

**YAML Autocompletion System** (`pds/schema/`):
- **Production-ready intelligent autocompletion** for `pds.yaml` files
- `api/` contains async API clients (httpx) for fetching live provider data
- `cache.py` provides intelligent caching with TTL and fallback mechanisms
- `generator.py` combines Pydantic schemas with dynamic API data into JSON Schema
- Supports all major editors: VS Code, IntelliJ, Neovim, etc.
- CLI commands: `pds schema generate`, `install`, `status`, `validate`

### Key Design Patterns

**Universal Provider Interface**: All providers implement the same `CloudProvider` base class but handle provisioning differently based on their `ProvisionType`. This allows consistent CLI experience regardless of the underlying infrastructure method.

**Configuration Validation**: The Pydantic models include cross-field validation (e.g., manual providers require `servers` list, others require `instances` count).

**Plugin Architecture**: Extensible system where new providers, proxies, and monitoring solutions can be added without core changes.

## Development Status & Roadmap

**Current Status**: Early development phase - **CLI entry point implementation** for deployment commands is the current focus.

**Completed Components**:
- Project structure and plugin system architecture
- Pydantic configuration models with validation  
- Base plugin interfaces and registry system
- DigitalOcean provider (terraform-based) and Manual provider implementations
- **🎉 YAML Autocompletion System** - Production-ready intelligent autocompletion with live API data

**Phase 1 Priorities (Core MVP)**:
- Complete CLI entry point with all commands
- Configuration file loader with YAML parsing
- Core deployment engine
- Terraform and Ansible executor wrappers
- Basic console output and logging

**Missing Core Infrastructure**:
- Core deployment commands (deploy, status, destroy, etc.) in CLI
- YAML configuration file parser for deployment operations
- Actual Terraform execution (init, plan, apply)
- Ansible playbooks for server setup, Docker, app deployment, proxy setup
- State management system
- Error handling and rollback mechanisms

## Development Guidelines

When working on this codebase:

1. **Focus on deployment CLI commands** - Schema system is complete, now need deploy/status/destroy commands
2. **Follow the plugin architecture** - New providers should extend the base classes in `pds/plugins/base.py`
3. **Use the existing Pydantic models** - Configuration should validate against `pds/config/models.py`
4. **Leverage the schema system** - Use `pds/schema/` components for configuration validation
5. **Prioritize the three provisioning types** - Ensure compatibility with TERRAFORM, API, and MANUAL providers
6. **Test with real providers** - Integration tests should work with actual cloud services
7. **Use async/httpx** - All new API clients should follow the pattern in `pds/schema/api/`

## Important Notes

- Uses `uv` for dependency management instead of pip/poetry
- Targets Python 3.11+ with modern syntax (union types with `|`)
- Security-first approach with fail2ban, firewall rules, and SSL by default
- Single `pds.yaml` configuration file defines entire infrastructure and deployment pipeline
- Built on proven tools: Terraform/OpenTofu + Ansible + Docker
- **NEW**: Full async architecture with httpx for all API operations
- **NEW**: Intelligent YAML autocompletion with live API data from cloud providers

## Schema System Usage

The autocompletion system is production-ready. To use it:

```bash
# Generate schema with live API data (requires DIGITALOCEAN_TOKEN)
pds schema generate --live --output pds-schema.json

# Install in VS Code
pds schema install --editor vscode

# Check cache status
pds schema status

# Validate configuration
pds schema validate pds.yaml
```