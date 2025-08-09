"""Pydantic models for PDS configuration."""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Manual server configuration."""

    ip: str = Field(description="Server IP address")
    user: str = Field(default="root", description="SSH user")
    ssh_key: str | None = Field(
        default="~/.ssh/id_rsa", description="SSH private key path"
    )
    port: int = Field(default=22, description="SSH port")


class InfrastructureConfig(BaseModel):
    """Infrastructure configuration."""

    # For Terraform/API providers
    instances: int | None = Field(default=1, ge=1, description="Number of instances")
    size: str | None = Field(description="Instance size/type")
    volume_size: int | None = Field(default=20, description="Volume size in GB")

    # For manual providers
    servers: list[ServerConfig] | None = Field(description="Manual server list")

    class Database(BaseModel):
        type: str = Field(description="Database type (postgres, mysql)")
        version: str | None = None
        size: str | None = None
        # For manual setup
        host: str | None = None
        port: int | None = None
        name: str | None = None
        user: str | None = None
        password: str | None = None

    class Redis(BaseModel):
        enabled: bool = False
        size: str | None = None
        # For manual setup
        host: str | None = None
        port: int | None = None
        password: str | None = None

    database: Database | None = None
    redis: Redis | None = None


class NetworkingConfig(BaseModel):
    """Networking and proxy configuration."""

    class LoadBalancer(BaseModel):
        algorithm: str = "round_robin"
        health_check: str = "/health"
        # For manual setup - can specify existing LB
        external_ip: str | None = None

    class SSL(BaseModel):
        enabled: bool = True
        force_https: bool = True
        # For manual certs
        cert_path: str | None = None
        key_path: str | None = None

    proxy: str = Field(
        default="caddy", description="Proxy type (caddy, nginx, traefik)"
    )
    load_balancer: LoadBalancer = LoadBalancer()
    ssl: SSL = SSL()
    rate_limiting: dict | None = None


class SecurityConfig(BaseModel):
    """Security configuration."""

    fail2ban: bool = True
    ufw_rules: list[dict] | None = None
    ssh_keys: list[str] | None = None


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    class Metrics(BaseModel):
        netdata: bool = False

    class Logs(BaseModel):
        centralized: bool = False

    type: str = Field(
        default="none",
        description="Monitoring type (uptime-kuma, prometheus-grafana, none)",
    )
    metrics: Metrics = Metrics()
    logs: Logs = Logs()
    alerts: dict[str, str] | None = None


class ApplicationConfig(BaseModel):
    """Single application configuration."""

    repo: str = Field(description="Git repository URL")
    branch: str = "main"
    type: str = Field(description="App type (static, service, api)")

    # Build configuration
    build_command: str | None = None
    build_output: str | None = None
    dockerfile: str | None = None

    # Runtime configuration
    port: int | None = None
    health_check: str | None = None
    env: dict[str, str] | None = None
    secrets: list[str] | None = None


class DomainConfig(BaseModel):
    """Domain routing configuration."""

    domain: str
    target: str | None = None  # Application name
    redirect: str | None = None  # Redirect to another domain


class EnvironmentConfig(BaseModel):
    """Environment-specific overrides."""

    instances: int | None = None
    size: str | None = None
    servers: list[ServerConfig] | None = None
    domains: list[str] | None = None
    # Can override any top-level config


class PDSConfig(BaseModel):
    """Main PDS configuration model."""

    project: str = Field(description="Project name")
    provider: str = Field(description="Cloud provider (digitalocean, manual, etc.)")
    region: str | None = Field(description="Cloud region (not needed for manual)")

    infrastructure: InfrastructureConfig
    networking: NetworkingConfig | None = NetworkingConfig()
    security: SecurityConfig | None = SecurityConfig()
    monitoring: MonitoringConfig | None = MonitoringConfig()

    applications: dict[str, ApplicationConfig]
    domains: list[str | DomainConfig] | None = None
    environments: dict[str, EnvironmentConfig] | None = None

    def model_post_init(self, __context) -> None:
        """Validate configuration after initialization."""
        # Validate that manual provider has servers or instances
        if self.provider == "manual":
            if not self.infrastructure.servers:
                raise ValueError(
                    "Manual provider requires 'servers' list in infrastructure"
                )
        else:
            if not self.infrastructure.instances:
                raise ValueError(
                    f"Provider '{self.provider}' requires 'instances' count in infrastructure"
                )
