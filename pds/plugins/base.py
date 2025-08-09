"""Base plugin interfaces for PDS with multi-type provider support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pds.config.models import PDSConfig


class ProvisionType(Enum):
    """Types of infrastructure provisioning."""

    TERRAFORM = "terraform"  # Full Terraform provider (DO, AWS, etc.)
    API = "api"  # Custom API calls + Ansible
    MANUAL = "manual"  # User-provided servers + Ansible only


@dataclass
class ServerInfo:
    """Information about a provisioned server."""

    ip: str
    private_ip: str | None = None
    ssh_user: str = "root"
    ssh_key_path: str = "~/.ssh/id_rsa"
    ssh_port: int = 22
    hostname: str | None = None
    tags: dict[str, str] = None


@dataclass
class InfrastructureInfo:
    """Complete infrastructure information after provisioning."""

    servers: list[ServerInfo]
    load_balancer_ip: str | None = None
    database_connection: str | None = None
    redis_connection: str | None = None
    outputs: dict[str, Any] = None  # Additional provider-specific outputs


class PluginHook:
    """Represents a plugin hook for lifecycle events."""

    def __init__(self, name: str, priority: int = 100):
        self.name = name
        self.priority = priority

    def execute(self, context: dict[str, Any]) -> None:
        """Execute the hook with given context."""
        pass


class CloudProvider(ABC):
    """Base class for cloud provider plugins supporting multiple provision types."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'digitalocean', 'manual')."""
        pass

    @property
    @abstractmethod
    def provision_type(self) -> ProvisionType:
        """How this provider provisions infrastructure."""
        pass

    @property
    def required_env_vars(self) -> list[str]:
        """Required environment variables for authentication.

        Can be empty for manual providers.
        """
        return []

    @abstractmethod
    def validate_config(self, config: PDSConfig) -> list[str]:
        """Validate provider-specific configuration.

        Returns:
            List of validation errors (empty if valid)

        """
        pass

    @abstractmethod
    def provision_infrastructure(
        self, config: PDSConfig, env: str = "production"
    ) -> InfrastructureInfo:
        """Provision infrastructure using the appropriate method for this provider.

        For TERRAFORM providers: Generate and run Terraform
        For API providers: Make API calls to create resources
        For MANUAL providers: Parse existing server configuration

        Returns:
            InfrastructureInfo with all server details

        """
        pass

    def generate_terraform(
        self, config: PDSConfig, env: str = "production"
    ) -> str | None:
        """Generate Terraform configuration (only for TERRAFORM providers)."""
        if self.provision_type == ProvisionType.TERRAFORM:
            raise NotImplementedError(
                "Terraform providers must implement generate_terraform"
            )
        return None

    @abstractmethod
    def get_ansible_inventory(
        self, infra_info: InfrastructureInfo, config: PDSConfig
    ) -> dict[str, Any]:
        """Generate Ansible inventory from infrastructure info."""
        pass

    @abstractmethod
    def get_ansible_vars(
        self, infra_info: InfrastructureInfo, config: PDSConfig, env: str = "production"
    ) -> dict[str, Any]:
        """Get Ansible variables for deployment."""
        pass

    def get_hooks(self) -> list[PluginHook]:
        """Get provider-specific hooks."""
        return []

    def cleanup_infrastructure(
        self, config: PDSConfig, env: str = "production"
    ) -> None:
        """Clean up provisioned infrastructure."""
        pass


class ProxyPlugin(ABC):
    """Base class for proxy/load balancer plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Proxy name (e.g., 'caddy')."""
        pass

    @abstractmethod
    def generate_config(
        self, config: PDSConfig, infra_info: InfrastructureInfo, env: str = "production"
    ) -> str:
        """Generate proxy configuration."""
        pass

    @abstractmethod
    def get_ansible_tasks(
        self, config: PDSConfig, infra_info: InfrastructureInfo, env: str = "production"
    ) -> list[dict]:
        """Get Ansible tasks for proxy setup."""
        pass


class MonitoringPlugin(ABC):
    """Base class for monitoring plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Monitoring system name (e.g., 'uptime-kuma')."""
        pass

    @abstractmethod
    def get_ansible_tasks(
        self, config: PDSConfig, infra_info: InfrastructureInfo, env: str = "production"
    ) -> list[dict]:
        """Get Ansible tasks for monitoring setup."""
        pass

    def get_dashboards(self) -> list[str]:
        """Get monitoring dashboard configurations."""
        return []


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self):
        self._providers: dict[str, CloudProvider] = {}
        self._proxies: dict[str, ProxyPlugin] = {}
        self._monitoring: dict[str, MonitoringPlugin] = {}

    def register_provider(self, provider: CloudProvider) -> None:
        """Register a cloud provider plugin."""
        self._providers[provider.name] = provider

    def register_proxy(self, proxy: ProxyPlugin) -> None:
        """Register a proxy plugin."""
        self._proxies[proxy.name] = proxy

    def register_monitoring(self, monitoring: MonitoringPlugin) -> None:
        """Register a monitoring plugin."""
        self._monitoring[monitoring.name] = monitoring

    def get_provider(self, name: str) -> CloudProvider | None:
        """Get provider plugin by name."""
        return self._providers.get(name)

    def get_proxy(self, name: str) -> ProxyPlugin | None:
        """Get proxy plugin by name."""
        return self._proxies.get(name)

    def get_monitoring(self, name: str) -> MonitoringPlugin | None:
        """Get monitoring plugin by name."""
        return self._monitoring.get(name)

    def list_providers(self) -> list[str]:
        """List available provider names."""
        return list(self._providers.keys())

    def list_proxies(self) -> list[str]:
        """List available proxy names."""
        return list(self._proxies.keys())

    def list_monitoring(self) -> list[str]:
        """List available monitoring names."""
        return list(self._monitoring.keys())


# Global plugin registry instance
plugin_registry = PluginRegistry()
