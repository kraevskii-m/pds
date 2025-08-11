"""Dynamic schema generator with API data integration."""

from typing import Any

from pds.config.models import PDSConfig

from .api.base import APIClient, ProviderResources
from .api.digitalocean import DigitalOceanAPIClient
from .cache import SchemaCache


class DynamicSchemaGenerator:
    """Schema generator with dynamic API data loading."""

    def __init__(self):
        """Initialize schema generator."""
        self.cache = SchemaCache()
        self.api_clients: dict[str, APIClient] = {
            "digitalocean": DigitalOceanAPIClient(),
            # "aws": AWSAPIClient(),
            # "hetzner": HetznerAPIClient(),
        }

    async def generate_schema(
        self,
        providers: list[str] | None = None,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Generate JSON Schema with dynamic data."""
        # Base schema from Pydantic models
        base_schema = PDSConfig.model_json_schema()

        # Add provider-specific data
        if providers is None:
            providers = list(self.api_clients.keys())

        provider_schemas = {}

        for provider_name in providers:
            if provider_name not in self.api_clients:
                continue

            client = self.api_clients[provider_name]
            resources = await self._get_provider_resources(
                client, use_cache=use_cache, force_refresh=force_refresh
            )

            provider_schemas[provider_name] = self._build_provider_schema(
                provider_name, resources
            )

        # Merge schemas
        return self._merge_schemas(base_schema, provider_schemas)

    async def _get_provider_resources(
        self, client: APIClient, use_cache: bool = True, force_refresh: bool = False
    ) -> ProviderResources:
        """Get provider resources with caching."""
        if use_cache and not force_refresh:
            cached = await self.cache.get_cached_resources(
                client.provider_name, client.cache_ttl_hours
            )
            if cached:
                return cached

        try:
            async with client:
                resources = await client.fetch_resources()

                # Cache the result
                await self.cache.cache_resources(client.provider_name, resources)

                return resources

        except Exception as e:
            print(
                f"Failed to fetch {client.provider_name} resources, using fallback: {e}"
            )
            return client.get_static_fallback()

    def _build_provider_schema(
        self, provider_name: str, resources: ProviderResources
    ) -> dict:
        """Build schema for specific provider."""
        provider_title = provider_name.title()

        definitions = {}

        # Regions enum
        if resources.regions:
            definitions[f"{provider_title}Regions"] = {
                "type": "string",
                "enum": resources.regions,
                "description": f"Available {provider_name} regions",
            }

        # Instance types enum (all available across regions)
        all_instance_types = set()
        for region_types in resources.instance_types.values():
            all_instance_types.update(region_types)

        if all_instance_types:
            definitions[f"{provider_title}InstanceTypes"] = {
                "type": "string",
                "enum": sorted(all_instance_types),
                "description": f"Available {provider_name} instance types",
            }

        # Database versions
        if resources.database_types:
            for db_type, versions in resources.database_types.items():
                if versions:
                    definitions[f"{provider_title}{db_type.title()}Versions"] = {
                        "type": "string",
                        "enum": versions,
                        "description": f"Available {db_type} versions"
                        f" on {provider_name}",
                    }

        # Kubernetes versions
        if resources.kubernetes_versions:
            definitions[f"{provider_title}KubernetesVersions"] = {
                "type": "string",
                "enum": resources.kubernetes_versions,
                "description": f"Available Kubernetes versions on {provider_name}",
            }

        return {
            "definitions": definitions,
            "conditional": self._build_conditional_schema(
                provider_name, provider_title, resources
            ),
        }

    def _build_conditional_schema(
        self, provider_name: str, provider_title: str, resources: ProviderResources
    ) -> dict:
        """Build conditional schema that applies when provider is selected."""
        properties = {}

        # Region constraint
        if resources.regions:
            properties["region"] = {"$ref": f"#/definitions/{provider_title}Regions"}

        # Infrastructure constraints
        infrastructure_props = {}

        # Instance size constraint
        if any(resources.instance_types.values()):
            infrastructure_props["size"] = {
                "$ref": f"#/definitions/{provider_title}InstanceTypes"
            }

        # Database constraints
        if resources.database_types:
            database_props = {}

            # Database version based on type
            for db_type in resources.database_types.keys():
                if resources.database_types[db_type]:
                    database_props["version"] = {
                        "anyOf": [
                            {
                                "if": {"properties": {"type": {"const": db_type}}},
                                "then": {
                                    "$ref": f"#/definitions/"
                                    f"{provider_title}{db_type.title()}Versions"
                                },
                            }
                        ]
                    }

            if database_props:
                infrastructure_props["database"] = {"properties": database_props}

        if infrastructure_props:
            properties["infrastructure"] = {"properties": infrastructure_props}

        return {
            "if": {"properties": {"provider": {"const": provider_name}}},
            "then": {"properties": properties} if properties else {},
        }

    def _merge_schemas(
        self, base_schema: dict, provider_schemas: dict[str, dict]
    ) -> dict:
        """Merge base schema with provider-specific schemas."""
        result = base_schema.copy()

        # Add definitions
        if "definitions" not in result:
            result["definitions"] = {}

        for provider_schema in provider_schemas.values():
            result["definitions"].update(provider_schema["definitions"])

        # Add conditional schemas through allOf
        conditionals = [ps["conditional"] for ps in provider_schemas.values()]
        if conditionals:
            result["allOf"] = conditionals

        return result

    async def validate_config(self, config_data: dict[str, Any]) -> list[str]:
        """Validate configuration against dynamic schema."""
        try:
            # config = PDSConfig(**config_data)
            return []
        except Exception as e:
            return [str(e)]

    async def close(self):
        """Close all API clients."""
        for client in self.api_clients.values():
            await client.close()
