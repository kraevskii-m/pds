"""Pydantic models for PDS configuration."""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Manual server configuration."""
    ip: str = Field(description="Server IP address")
    user: str = Field(default="root", description="SSH user")
    ssh_key: Optional[str] = Field(default="~/.ssh/id_rsa", description="SSH private key path")
    port: int = Field(default=22, description="SSH port")


class InfrastructureConfig(BaseModel):
    """Infrastructure configuration."""
    # For Terraform/API providers
    instances: Optional[int] = Field(default=1, ge=1, description="Number of instances")
    size: Optional[str] = Field(description="Instance size/type")
    volume_size: Optional[int] = Field(default=20, description="Volume size in GB")
    
    # For manual providers
    servers: Optional[List[ServerConfig]] = Field(description="Manual server list")
    
    class Database(BaseModel):
        type: str = Field(description="Database type (postgres, mysql)")
        version: Optional[str] = None
        size: Optional[str] = None
        # For manual setup
        host: Optional[str] = None
        port: Optional[int] = None
        name: Optional[str] = None
        user: Optional[str] = None
        password: Optional[str] = None
    
    class Redis(BaseModel):
        enabled: bool = False
        size: Optional[str] = None
        # For manual setup
        host: Optional[str] = None
        port: Optional[int] = None
        password: Optional[str] = None
    
    database: Optional[Database] = None
    redis: Optional[Redis] = None


class NetworkingConfig(BaseModel):
    """Networking and proxy configuration."""
    
    class LoadBalancer(BaseModel):
        algorithm: str = "round_robin"
        health_check: str = "/health"
        # For manual setup - can specify existing LB
        external_ip: Optional[str] = None
    
    class SSL(BaseModel):
        enabled: bool = True
        force_https: bool = True
        # For manual certs
        cert_path: Optional[str] = None
        key_path: Optional[str] = None
    
    proxy: str = Field(default="caddy", description="Proxy type (caddy, nginx, traefik)")
    load_balancer: LoadBalancer = LoadBalancer()
    ssl: SSL = SSL()
    rate_limiting: Optional[Dict] = None


class SecurityConfig(BaseModel):
    """Security configuration."""
    fail2ban: bool = True
    ufw_rules: Optional[List[Dict]] = None
    ssh_keys: Optional[List[str]] = None


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    
    class Metrics(BaseModel):
        netdata: bool = False
    
    class Logs(BaseModel):
        centralized: bool = False
    
    type: str = Field(default="none", description="Monitoring type (uptime-kuma, prometheus-grafana, none)")
    metrics: Metrics = Metrics()
    logs: Logs = Logs()
    alerts: Optional[Dict[str, str]] = None


class ApplicationConfig(BaseModel):
    """Single application configuration."""
    repo: str = Field(description="Git repository URL")
    branch: str = "main"
    type: str = Field(description="App type (static, service, api)")
    
    # Build configuration
    build_command: Optional[str] = None
    build_output: Optional[str] = None
    dockerfile: Optional[str] = None
    
    # Runtime configuration  
    port: Optional[int] = None
    health_check: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    secrets: Optional[List[str]] = None


class DomainConfig(BaseModel):
    """Domain routing configuration."""
    domain: str
    target: Optional[str] = None  # Application name
    redirect: Optional[str] = None  # Redirect to another domain


class EnvironmentConfig(BaseModel):
    """Environment-specific overrides."""
    instances: Optional[int] = None
    size: Optional[str] = None
    servers: Optional[List[ServerConfig]] = None
    domains: Optional[List[str]] = None
    # Can override any top-level config


class PDSConfig(BaseModel):
    """Main PDS configuration model."""
    project: str = Field(description="Project name")
    provider: str = Field(description="Cloud provider (digitalocean, manual, etc.)")
    region: Optional[str] = Field(description="Cloud region (not needed for manual)")
    
    infrastructure: InfrastructureConfig
    networking: Optional[NetworkingConfig] = NetworkingConfig()
    security: Optional[SecurityConfig] = SecurityConfig()  
    monitoring: Optional[MonitoringConfig] = MonitoringConfig()
    
    applications: Dict[str, ApplicationConfig]
    domains: Optional[List[Union[str, DomainConfig]]] = None
    environments: Optional[Dict[str, EnvironmentConfig]] = None
    
    def model_post_init(self, __context) -> None:
        """Validate configuration after initialization."""
        # Validate that manual provider has servers or instances
        if self.provider == "manual":
            if not self.infrastructure.servers:
                raise ValueError("Manual provider requires 'servers' list in infrastructure")
        else:
            if not self.infrastructure.instances:
                raise ValueError(f"Provider '{self.provider}' requires 'instances' count in infrastructure")