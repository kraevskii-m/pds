"""Base interfaces for API clients with async support."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ProviderResources:
    """Resources available from a provider."""

    regions: list[str] = field(default_factory=list)
    instance_types: dict[str, list[str]] = field(
        default_factory=dict
    )  # region -> [types]
    database_types: dict[str, list[str]] = field(
        default_factory=dict
    )  # engine -> [versions]
    kubernetes_versions: list[str] | None = None
    storage_types: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching."""
        return {
            "regions": self.regions,
            "instance_types": self.instance_types,
            "database_types": self.database_types,
            "kubernetes_versions": self.kubernetes_versions,
            "storage_types": self.storage_types,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderResources":
        """Create from dictionary (from cache)."""
        return cls(
            regions=data.get("regions", []),
            instance_types=data.get("instance_types", {}),
            database_types=data.get("database_types", {}),
            kubernetes_versions=data.get("kubernetes_versions"),
            storage_types=data.get("storage_types"),
        )


class APIClient(ABC):
    """Base class for async API clients."""

    def __init__(self):
        """Initialise the API client."""
        self._client: httpx.AsyncClient | None = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (e.g., 'digitalocean')."""
        pass

    @property
    def cache_ttl_hours(self) -> int:
        """Cache TTL in hours. Default is 6 hours."""
        return 6

    @property
    def timeout(self) -> float:
        """Request timeout in seconds."""
        return 30.0

    @property
    def max_retries(self) -> int:
        """Maximum number of retries for failed requests."""
        return 3

    @abstractmethod
    async def fetch_resources(self) -> ProviderResources:
        """Fetch provider resources from API."""
        pass

    @abstractmethod
    def get_auth_config(self) -> dict[str, str]:
        """Return authentication requirements."""
        pass

    def get_static_fallback(self) -> ProviderResources:
        """Get static fallback when API is unavailable."""
        return ProviderResources(
            regions=["unknown"],
            instance_types={"unknown": ["standard"]},
            database_types={"postgres": ["15"]},
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout), follow_redirects=True
            )
        return self._client

    async def _request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except (httpx.RequestError, httpx.TimeoutException):
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        raise httpx.RequestError("Max retries exceeded")

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """:return:"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit with exception handling.

        :param exc_type:
        :param exc_val:
        :param exc_tb:
        """
        await self.close()
