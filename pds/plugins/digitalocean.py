"""DigitalOcean cloud provider plugin (Terraform-based)."""

from typing import Dict, List, Any
from pds.config.models import PDSConfig
from pds.plugins.base import CloudProvider, ProvisionType, InfrastructureInfo, ServerInfo


class DigitalOceanProvider(CloudProvider):
    """DigitalOcean cloud provider using Terraform."""
    
    @property
    def name(self) -> str:
        return "digitalocean"
    
    @property 
    def provision_type(self) -> ProvisionType:
        return ProvisionType.TERRAFORM
    
    @property
    def required_env_vars(self) -> List[str]:
        return ["DIGITALOCEAN_TOKEN"]
    
    def validate_config(self, config: PDSConfig) -> List[str]:
        """Validate DigitalOcean-specific configuration."""
        errors = []
        
        if not config.region:
            errors.append("Region is required for DigitalOcean provider")
            return errors
            
        # Validate region
        valid_regions = [
            "nyc1", "nyc3", "ams3", "sgp1", "lon1", 
            "fra1", "tor1", "blr1", "sfo3"
        ]
        if config.region not in valid_regions:
            errors.append(f"Invalid region: {config.region}. Valid: {valid_regions}")
        
        # Validate instance sizes
        if config.infrastructure.instances and config.infrastructure.size:
            valid_sizes = [
                "s-1vcpu-1gb", "s-1vcpu-2gb", "s-2vcpu-2gb", "s-2vcpu-4gb",
                "s-4vcpu-8gb", "s-6vcpu-16gb", "s-8vcpu-32gb"
            ]
            if config.infrastructure.size not in valid_sizes:
                errors.append(f"Invalid instance size: {config.infrastructure.size}")
        
        # Validate database configuration if present
        if config.infrastructure.database:
            db_type = config.infrastructure.database.type
            if db_type not in ["postgres", "mysql"]:
                errors.append(f"Unsupported database type for DO: {db_type}. Use postgres or mysql")
        
        return errors
    
    def generate_terraform(self, config: PDSConfig, env: str = "production") -> str:
        """Generate Terraform configuration for DigitalOcean."""
        tf_config = f'''
# DigitalOcean Provider
terraform {{
  required_providers {{
    digitalocean = {{
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }}
  }}
}}

provider "digitalocean" {{
  # Uses DIGITALOCEAN_TOKEN environment variable
}}

# SSH Key
resource "digitalocean_ssh_key" "{config.project}_key" {{
  name       = "{config.project}-{env}"
  public_key = file("~/.ssh/id_rsa.pub")
}}

# VPC
resource "digitalocean_vpc" "{config.project}_vpc" {{
  name     = "{config.project}-{env}"
  region   = "{config.region}"
  ip_range = "10.0.0.0/16"
}}

# Droplets
resource "digitalocean_droplet" "app" {{
  count  = {config.infrastructure.instances}
  image  = "ubuntu-22-04-x64"
  name   = "{config.project}-{env}-${{count.index + 1}}"
  region = "{config.region}"
  size   = "{config.infrastructure.size}"
  
  vpc_uuid = digitalocean_vpc.{config.project}_vpc.id
  ssh_keys = [digitalocean_ssh_key.{config.project}_key.fingerprint]
  
  tags = ["{config.project}", "{env}", "app"]
}}
'''
        
        # Add load balancer if multiple instances
        if config.infrastructure.instances > 1:
            tf_config += f'''
# Load Balancer
resource "digitalocean_loadbalancer" "{config.project}_lb" {{
  name   = "{config.project}-{env}-lb"
  region = "{config.region}"
  vpc_uuid = digitalocean_vpc.{config.project}_vpc.id

  forwarding_rule {{
    entry_protocol  = "https"
    entry_port      = 443
    target_protocol = "http"
    target_port     = 80
    tls_passthrough = false
  }}

  forwarding_rule {{
    entry_protocol  = "http"
    entry_port      = 80
    target_protocol = "http"
    target_port     = 80
  }}

  healthcheck {{
    protocol = "http"
    port     = 80
    path     = "/health"
  }}

  droplet_ids = digitalocean_droplet.app[*].id
}}
'''
        
        # Add database if configured
        if config.infrastructure.database:
            db_config = config.infrastructure.database
            tf_config += f'''
# Database
resource "digitalocean_database_cluster" "{config.project}_db" {{
  name       = "{config.project}-{env}-db"
  engine     = "{db_config.type}"
  version    = "{db_config.version or self._get_default_db_version(db_config.type)}"
  size       = "{db_config.size or 'db-s-1vcpu-1gb'}"
  region     = "{config.region}"
  node_count = 1
  
  tags = ["{config.project}", "{env}", "database"]
}}

resource "digitalocean_database_firewall" "{config.project}_db_fw" {{
  cluster_id = digitalocean_database_cluster.{config.project}_db.id
  
  dynamic "rule" {{
    for_each = digitalocean_droplet.app
    content {{
      type  = "droplet"
      value = rule.value.id
    }}
  }}
}}
'''
        
        # Add Redis if configured
        if config.infrastructure.redis and config.infrastructure.redis.enabled:
            tf_config += f'''
# Redis
resource "digitalocean_database_cluster" "{config.project}_redis" {{
  name       = "{config.project}-{env}-redis"
  engine     = "redis"
  version    = "7"
  size       = "{config.infrastructure.redis.size or 'db-s-1vcpu-1gb'}"
  region     = "{config.region}"
  node_count = 1
  
  tags = ["{config.project}", "{env}", "redis"]
}}
'''
        
        # Add outputs
        tf_config += f'''
# Outputs
output "droplet_ips" {{
  value = digitalocean_droplet.app[*].ipv4_address
}}

output "droplet_private_ips" {{
  value = digitalocean_droplet.app[*].ipv4_address_private
}}
'''
        
        if config.infrastructure.instances > 1:
            tf_config += f'''
output "load_balancer_ip" {{
  value = digitalocean_loadbalancer.{config.project}_lb.ip
}}
'''
        
        if config.infrastructure.database:
            tf_config += f'''
output "database_connection" {{
  value = digitalocean_database_cluster.{config.project}_db.private_uri
  sensitive = true
}}
'''
        
        if config.infrastructure.redis and config.infrastructure.redis.enabled:
            tf_config += f'''
output "redis_connection" {{
  value = digitalocean_database_cluster.{config.project}_redis.private_uri
  sensitive = true
}}
'''
        
        return tf_config
    
    def provision_infrastructure(self, config: PDSConfig, env: str = "production") -> InfrastructureInfo:
        """Provision DigitalOcean infrastructure using Terraform."""
        # This would run terraform and parse outputs
        # For now, return mock data
        
        servers = []
        for i in range(config.infrastructure.instances):
            servers.append(ServerInfo(
                ip=f"64.225.{i+1}.10",
                private_ip=f"10.0.0.{i+10}",
                hostname=f"{config.project}-{env}-{i+1}"
            ))
        
        return InfrastructureInfo(
            servers=servers,
            load_balancer_ip="64.225.100.1" if config.infrastructure.instances > 1 else None,
            database_connection="postgres://user:pass@db-host:25060/db" if config.infrastructure.database else None,
            redis_connection="redis://user:pass@redis-host:25061" if config.infrastructure.redis else None
        )
    
    def get_ansible_inventory(self, infra_info: InfrastructureInfo, config: PDSConfig) -> Dict[str, Any]:
        """Generate Ansible inventory for DigitalOcean servers."""
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
            inventory["all"]["children"]["app_servers"]["hosts"][f"app-{i+1}"] = {
                "ansible_host": server.ip,
                "ansible_user": server.ssh_user,
                "ansible_ssh_private_key_file": server.ssh_key_path,
                "private_ip": server.private_ip,
                "hostname": server.hostname
            }
        
        return inventory
    
    def get_ansible_vars(self, infra_info: InfrastructureInfo, config: PDSConfig, env: str = "production") -> Dict[str, Any]:
        """Get Ansible variables for DigitalOcean deployment."""
        return {
            "cloud_provider": "digitalocean",
            "project_name": config.project,
            "environment": env,
            "region": config.region,
            "server_count": len(infra_info.servers),
            "load_balancer_ip": infra_info.load_balancer_ip,
            "database_connection": infra_info.database_connection,
            "redis_connection": infra_info.redis_connection,
            "has_database": config.infrastructure.database is not None,
            "has_redis": config.infrastructure.redis and config.infrastructure.redis.enabled,
        }
    
    def _get_default_db_version(self, db_type: str) -> str:
        """Get default database version for type."""
        defaults = {
            "postgres": "15",
            "mysql": "8.0"
        }
        return defaults.get(db_type, "")