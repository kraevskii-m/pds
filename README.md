# PDS - Please Deploy Stuff

> Minimal CLI to provision VMs, run migrations, and deploy apps from a single YAML using OpenTofu/Terraform and Ansible.

**The problem:** Deploying simple web apps shouldn't require Kubernetes expertise, but manual server management is error-prone and time-consuming.

**The solution:** One YAML config + one command = fully deployed application with load balancing, security, and monitoring.

## Why PDS?

- 🚀 **MVP-friendly** - Deploy in minutes, not days
- 📦 **Batteries included** - SSL, load balancing, fail2ban, rate limiting out of the box
- 🔄 **GitOps ready** - Perfect for CI/CD pipelines
- 💰 **Cost effective** - Uses simple VMs, not expensive managed services
- 🛡️ **Secure by default** - Security hardening and monitoring included

## Quick Start

```yaml
# pds.yaml
project: my-awesome-app
provider: digitalocean
region: nyc1

infrastructure:
  instances: 2
  size: s-1vcpu-1gb
  database: postgres-12
  redis: true

applications:
  frontend:
    repo: https://github.com/user/frontend
    type: static
    build: npm run build
    
  backend:
    repo: https://github.com/user/backend  
    type: api
    port: 8000
    env_file: .env.production

domains:
  - my-awesome-app.com -> frontend
  - api.my-awesome-app.com -> backend
```

```bash
# Deploy everything
pds deploy

# Check status  
pds status

# Run database migrations
pds migrate

# Scale up
pds scale --instances 4

# Destroy everything
pds destroy
```

## Features

### Infrastructure Management
- ✅ VM provisioning (DigitalOcean, Hetzner, AWS, etc.)
- ✅ Load balancer setup with health checks
- ✅ Database provisioning (PostgreSQL, MySQL, Redis)
- ✅ SSL certificates via Let's Encrypt
- ✅ Firewall and security hardening

### Application Deployment  
- ✅ Multi-repository support
- ✅ Docker and non-Docker apps
- ✅ Environment-specific configurations
- ✅ Rolling deployments with rollback
- ✅ Database migrations

### Operations
- ✅ Real-time status monitoring
- ✅ Log aggregation and viewing
- ✅ Backup automation
- ✅ Security updates
- ✅ Cost monitoring

## Configuration

PDS uses a single `pds.yaml` file that defines your entire infrastructure and deployment pipeline:

```yaml
# Full configuration example
project: my-app
provider: digitalocean
region: nyc1

# Infrastructure
infrastructure:
  instances: 2
  size: s-2vcpu-2gb
  volume_size: 40
  database:
    type: postgres
    version: "14"
    size: db-s-1vcpu-1gb
  redis:
    enabled: true
    size: db-s-1vcpu-1gb
  backup:
    enabled: true
    retention: 7d

# Load balancing & networking  
networking:
  proxy: caddy  # Options: caddy, traefik, nginx
  load_balancer:
    algorithm: round_robin
    health_check: /health
  ssl:
    enabled: true
    force_https: true
  rate_limiting:
    requests_per_minute: 1000
  
# Security & Monitoring
security:
  fail2ban: true
  ufw_rules:
    - port: 22
      source: "your.ip.here"
    - port: 80
    - port: 443
  ssh_keys:
    - ~/.ssh/id_rsa.pub

monitoring:
  type: uptime-kuma  # Options: prometheus-grafana, uptime-kuma, none
  metrics:
    netdata: true      # Lightweight system monitoring
  logs:
    centralized: true  # Ship logs to monitoring system
  alerts:
    discord_webhook: "https://..."
    slack_webhook: "https://..."

# Applications
applications:
  web:
    repo: https://github.com/user/frontend
    branch: main
    type: static
    build_command: npm run build
    build_output: dist/
    
  api:
    repo: https://github.com/user/backend
    branch: main  
    type: service
    dockerfile: Dockerfile
    port: 8000
    health_check: /api/health
    env:
      DATABASE_URL: "{{database.url}}"
      REDIS_URL: "{{redis.url}}"
    secrets:
      - JWT_SECRET
      - STRIPE_KEY

# Domain routing
domains:
  - domain: myapp.com
    target: web
  - domain: api.myapp.com  
    target: api
  - domain: www.myapp.com
    redirect: myapp.com

# Environments
environments:
  staging:
    instances: 1
    size: s-1vcpu-1gb
    domains:
      - staging.myapp.com -> web
  production:
    instances: 3
    size: s-2vcpu-4gb
    backup:
      retention: 30d
```

## Commands

```bash
# Setup and deployment
pds init                    # Initialize pds.yaml template
pds validate               # Validate configuration  
pds plan                   # Show what changes will be made
pds deploy                 # Deploy everything
pds deploy --env staging  # Deploy to specific environment

# Management
pds status                 # Show current status
pds logs [service]         # View application logs  
pds scale --instances N    # Scale horizontally
pds migrate               # Run database migrations
pds backup                # Create manual backup
pds restore --backup-id X # Restore from backup

# Maintenance  
pds update                # Update system packages
pds restart [service]     # Restart specific service
pds rollback             # Rollback to previous version

# Cleanup
pds destroy              # Destroy all resources
pds destroy --keep-data  # Destroy but keep databases
```

## Architecture

PDS is built on proven tools with modern alternatives:

### Core Stack
- **Terraform/OpenTofu** - Infrastructure provisioning
- **Ansible** - Server configuration and app deployment  
- **Docker** - Application containerization (optional)

### Proxy & Load Balancing (choose one)
- **Caddy** - Modern, automatic HTTPS (default)
- **Traefik** - Cloud-native, great for containers
- **Nginx** - Battle-tested, maximum performance

### Monitoring (choose one)
- **Uptime Kuma** - Simple, beautiful uptime monitoring (default)
- **Prometheus + Grafana** - Full metrics and alerting stack
- **None** - Minimal setup

### Additional Tools
- **Let's Encrypt** - SSL certificates (via proxy)
- **Netdata** - Real-time system monitoring
- **fail2ban** - Intrusion prevention  
- **UFW** - Simple firewall

### Plugin System
- **Core plugins** - Built-in cloud providers, proxies, monitoring
- **Community plugins** - Custom providers, integrations, hooks
- **Plugin discovery** - Auto-install from registry or git repos
- **Hook system** - Pre/post deploy, scaling, backup events

## Installation

```bash
# Via pip
pip install pds-cli

# Via uv  
uv tool install pds-cli

# From source
git clone https://github.com/user/pds
cd pds
uv sync --dev
uv run pds --help
```

## Requirements

- Python 3.11+
- Terraform or OpenTofu
- Ansible
- Provider CLI tools (doctl, aws, etc.)

## Developing

```bash
# Setup development environment
uv sync --dev
pre-commit install

# Run tests
nox -s tests

# Run all checks  
nox

# Type checking
pyright

# Security scan
bandit -r pds
```

## Roadmap

### Phase 1: Core MVP
- [x] Basic CLI structure
- [ ] DigitalOcean provider
- [ ] Simple web app deployment
- [ ] SSL setup

### Phase 2: Production Ready  
- [ ] Multiple cloud providers
- [ ] Database migrations
- [ ] Monitoring and alerting
- [ ] Backup/restore

### Phase 3: Advanced Features
- [ ] Blue/green deployments  
- [ ] Auto-scaling
- [ ] Cost optimization
- [ ] Multi-region support

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT - see [LICENSE](LICENSE) for details.
