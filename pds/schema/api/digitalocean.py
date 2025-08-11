"""DigitalOcean API client for fetching live configuration data."""

import asyncio
import os
from typing import Any

from .base import APIClient, ProviderResources


class DigitalOceanAPIClient(APIClient):
    """Async DigitalOcean API client for config retrieval."""

    BASE_URL = "https://api.digitalocean.com/v2"

    @property
    def provider_name(self) -> str:
        """:return:"""
        return "digitalocean"

    def get_auth_config(self) -> dict[str, str]:
        """:return:"""
        return {"DIGITALOCEAN_TOKEN": "Personal Access Token from DO dashboard"}

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        token = os.getenv("DIGITALOCEAN_TOKEN")
        if not token:
            raise ValueError(
                "DIGITALOCEAN_TOKEN environment variable is required. "
                "Get your token at https://cloud.digitalocean.com/account/api/tokens"
            )

        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def fetch_resources(self) -> ProviderResources:
        """Get data from DigitalOcean API."""
        # Check if we have auth token, if not return fallback immediately
        token = os.getenv("DIGITALOCEAN_TOKEN")
        if not token:
            print("No DIGITALOCEAN_TOKEN found, using static fallback data")
            return self.get_static_fallback()

        try:
            regions_task = self._fetch_regions()
            sizes_task = self._fetch_sizes()
            db_options_task = self._fetch_database_options()
            k8s_versions_task = self._fetch_kubernetes_versions()

            regions_data, sizes_data, db_data, k8s_versions = await asyncio.gather(
                regions_task,
                sizes_task,
                db_options_task,
                k8s_versions_task,
                return_exceptions=True,
            )

            # Use fallback data for failed requests
            fallback = self.get_static_fallback()

            if isinstance(regions_data, Exception):
                print(f"Failed to fetch regions: {regions_data}")
                regions_data = fallback.regions

            if isinstance(sizes_data, Exception):
                print(f"Failed to fetch sizes: {sizes_data}")
                sizes_data = []  # Will use fallback instance_types

            if isinstance(db_data, Exception):
                print(f"Failed to fetch database options: {db_data}")
                db_data = fallback.database_types

            if isinstance(k8s_versions, Exception):
                print(f"Failed to fetch k8s versions: {k8s_versions}")
                k8s_versions = fallback.kubernetes_versions

            # Group sizes by region, fallback to static data if sizes failed
            if sizes_data:
                instance_types = self._group_sizes_by_region(regions_data, sizes_data)
            else:
                instance_types = fallback.instance_types

            return ProviderResources(
                regions=regions_data,
                instance_types=instance_types,
                database_types=db_data,
                kubernetes_versions=k8s_versions,
            )

        except Exception as e:
            print(f"Failed to fetch DO resources: {e}")
            return self.get_static_fallback()

    async def _fetch_regions(self) -> list[str]:
        """Fetch available regions from DigitalOcean API."""
        response = await self._request_with_retry(
            "GET", f"{self.BASE_URL}/regions", headers=self._get_headers()
        )

        data = response.json()
        regions = data["regions"]

        available_regions = [
            r["slug"] for r in regions if r["available"] and "features" in r
        ]

        return sorted(available_regions)

    async def _fetch_sizes(self) -> list[dict[str, Any]]:
        """Droplet sizes."""
        response = await self._request_with_retry(
            "GET", f"{self.BASE_URL}/sizes", headers=self._get_headers()
        )

        data = response.json()
        sizes = data["sizes"]

        available_sizes = [s for s in sizes if s["available"] and s["regions"]]

        return available_sizes

    def _group_sizes_by_region(
        self, regions: list[str], sizes: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Group sizes by region."""
        instance_types = {}

        for region in regions:
            available_sizes = []

            for size in sizes:
                if region in size.get("regions", []):
                    available_sizes.append(size["slug"])

            if available_sizes:
                instance_types[region] = sorted(available_sizes)

        all_sizes = list({s["slug"] for s in sizes})
        instance_types["*"] = sorted(all_sizes)

        return instance_types

    async def _fetch_database_options(self) -> dict[str, list[str]]:
        """Fetch database options."""
        try:
            response = await self._request_with_retry(
                "GET", f"{self.BASE_URL}/databases/options", headers=self._get_headers()
            )

            data = response.json()
            options = data.get("options", {})
            db_types = {}

            for engine in options.get("engines", []):
                engine_name = engine["name"].lower()
                versions = [v["slug"] for v in engine.get("versions", [])]
                if versions:
                    db_types[engine_name] = sorted(versions, reverse=True)

            return db_types

        except Exception as e:
            print(f"Failed to fetch DB options: {e}")
            return {
                "postgres": ["16", "15", "14", "13", "12"],
                "mysql": ["8.0"],
                "redis": ["7", "6"],
            }

    async def _fetch_kubernetes_versions(self) -> list[str]:
        """Fetch kubernetes versions."""
        try:
            response = await self._request_with_retry(
                "GET",
                f"{self.BASE_URL}/kubernetes/options",
                headers=self._get_headers(),
            )

            data = response.json()
            options = data.get("options", {})

            versions = []
            for version_info in options.get("versions", []):
                versions.append(version_info["slug"])

            return sorted(versions, reverse=True)

        except Exception as e:
            print(f"Failed to fetch k8s versions: {e}")
            return ["1.30", "1.29", "1.28"]  # Fallback

    def get_static_fallback(self) -> ProviderResources:
        """Get static fallback resources."""
        static_regions = [
            "nyc1",
            "nyc3",
            "ams3",
            "sgp1",
            "lon1",
            "fra1",
            "tor1",
            "blr1",
            "sfo3",
        ]

        static_sizes = [
            "s-1vcpu-1gb",
            "s-1vcpu-2gb",
            "s-2vcpu-2gb",
            "s-2vcpu-4gb",
            "s-4vcpu-8gb",
            "s-6vcpu-16gb",
        ]

        instance_types = dict.fromkeys(static_regions, static_sizes)
        instance_types["*"] = static_sizes

        return ProviderResources(
            regions=static_regions,
            instance_types=instance_types,
            database_types={
                "postgres": ["16", "15", "14", "13", "12"],
                "mysql": ["8.0"],
                "redis": ["7", "6"],
            },
            kubernetes_versions=["1.30", "1.29", "1.28"],
        )
