"""Manual provider plugin for user-managed servers."""

from typing import Any

from pds.config.models import PDSConfig
from pds.plugins.base import (
    CloudProvider,
    InfrastructureInfo,
    ProvisionType,
    ServerInfo,
)


class ManualProvider(CloudProvider):
    """Manual provider for existing servers or manual VM creation."""

    @property
    def name(self) -> str:
        return "manual"

    @property
    def provision_type(self) -> ProvisionType:
        return ProvisionType.MANUAL

    @property
    def required_env_vars(self) -> list[str]:
        return []  # No API keys needed for manual

    def validate_config(self, config: PDSConfig) -> list[str]:
        """Validate manual provider configuration."""
        errors = []

        if not config.infrastructure.servers:
            errors.append("Manual provider requires 'servers' list in infrastructure config")
            return errors

        # Validate each server config
        for i, server in enumerate(config.infrastructure.servers):
            if not server.ip:
                errors.append(f"Server {i + 1}: IP address is required")

            if not server.user:
                errors.append(f"Server {i + 1}: SSH user is required")

            # TODO: Could add SSH connectivity test here

        return errors

    def provision_infrastructure(self, config: PDSConfig, env: str = "production") -> InfrastructureInfo:
        """Parse existing server configuration for manual provider."""
        servers = []

        for i, server_config in enumerate(config.infrastructure.servers):
            servers.append(ServerInfo(
                ip=server_config.ip,
                ssh_user=server_config.user,
                ssh_key_path=server_config.ssh_key or "~/.ssh/id_rsa",
                ssh_port=server_config.port,
                hostname=f"{config.project}-{env}-{i + 1}",
                tags={"provider": "manual", "project": config.project, "env": env}
            ))

        # For manual provider, load balancer IP might be manually configured
        load_balancer_ip = None
        if config.networking and config.networking.load_balancer and config.networking.load_balancer.external_ip:
            load_balancer_ip = config.networking.load_balancer.external_ip

        # Database connections for manual setup
        database_connection = None
        if config.infrastructure.database:
            db = config.infrastructure.database
            if db.host and db.user and db.password and db.name:
                port = db.port or (5432 if db.type == "postgres" else 3306)
                if db.type == "postgres":
                    database_connection = f"postgresql://{db.user}:{db.password}@{db.host}:{port}/{db.name}"
                else:
                    database_connection = f"mysql://{db.user}:{db.password}@{db.host}:{port}/{db.name}"

        # Redis connection for manual setup
        redis_connection = None
        if config.infrastructure.redis and config.infrastructure.redis.enabled:
            redis = config.infrastructure.redis
            if redis.host:
                port = redis.port or 6379
                if redis.password:
                    redis_connection = f"redis://:{redis.password}@{redis.host}:{port}"
                else:
                    redis_connection = f"redis://{redis.host}:{port}"

        return InfrastructureInfo(
            servers=servers,
            load_balancer_ip=load_balancer_ip,
            database_connection=database_connection,
            redis_connection=redis_connection
        )

    def get_ansible_inventory(self, infra_info: InfrastructureInfo, config: PDSConfig) -> dict[str, Any]:
        """Generate Ansible inventory for manual servers."""
        inventory = {
            "all": {
                "children": {
                    "app_servers": {
                        "hosts": {}
                    }
                }
            }
        }

        for i, server in enumerate(infra_info.servers):
            inventory["all"]["children"]["app_servers"]["hosts"][f"server-{i + 1}"] = {
                "ansible_host": server.ip,
                "ansible_user": server.ssh_user,
                "ansible_ssh_private_key_file": server.ssh_key_path,
                "ansible_port": server.ssh_port,
                "hostname": server.hostname
            }

        return inventory

    def get_ansible_vars(self, infra_info: InfrastructureInfo, config: PDSConfig, env: str = "production") -> dict[
        str, Any]:
        """Get Ansible variables for manual deployment."""
        return {
            "cloud_provider": "manual",
            "project_name": config.project,
            "environment": env,
            "server_count": len(infra_info.servers),
            "load_balancer_ip": infra_info.load_balancer_ip,
            "database_connection": infra_info.database_connection,
            "redis_connection": infra_info.redis_connection,
            "has_database": config.infrastructure.database is not None,
            "has_redis": config.infrastructure.redis and config.infrastructure.redis.enabled,
            "manual_setup": True,
        }
