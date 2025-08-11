"""Async caching system for API data with file-based storage."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import platformdirs

from .api.base import ProviderResources


class SchemaCache:
    """Async cache for schema API data."""

    def __init__(self, cache_dir: Path | None = None):
        """:param cache_dir:"""
        if cache_dir is None:
            cache_dir = Path(platformdirs.user_cache_dir("pds", "pds"))

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_cache_file(self, provider: str) -> Path:
        """Get cache file path for provider."""
        return self.cache_dir / f"{provider}_resources.json"

    def _get_lock(self, provider: str) -> asyncio.Lock:
        """Get or create lock for provider to avoid race conditions."""
        if provider not in self._locks:
            self._locks[provider] = asyncio.Lock()
        return self._locks[provider]

    async def get_cached_resources(
        self, provider: str, ttl_hours: int = 6
    ) -> ProviderResources | None:
        """Get cached data if still valid."""
        cache_file = self._get_cache_file(provider)

        if not cache_file.exists():
            return None

        lock = self._get_lock(provider)
        async with lock:
            try:
                async with aiofiles.open(cache_file) as f:
                    content = await f.read()
                    cached_data = json.loads(content)

                cached_time = datetime.fromisoformat(cached_data["timestamp"])
                if datetime.now() - cached_time > timedelta(hours=ttl_hours):
                    return None  # Cache expired

                return ProviderResources.from_dict(cached_data["resources"])

            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                print(f"Failed to read cache for {provider}: {e}")
                return None

    async def cache_resources(
        self, provider: str, resources: ProviderResources
    ) -> None:
        """Save resources to cache asynchronously."""
        cache_file = self._get_cache_file(provider)

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "resources": resources.to_dict(),
        }

        lock = self._get_lock(provider)
        async with lock:
            try:
                # Atomic write using temporary file
                temp_file = cache_file.with_suffix(".tmp")

                async with aiofiles.open(temp_file, "w") as f:
                    await f.write(json.dumps(cache_data, indent=2))

                # Atomic rename
                temp_file.replace(cache_file)

            except OSError as e:
                print(f"Failed to cache resources for {provider}: {e}")

    async def clear_cache(self, provider: str | None = None) -> int:
        """Clear provider cache or all cache. Returns number of files deleted."""
        cleared_count = 0

        if provider:
            cache_file = self._get_cache_file(provider)
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    cleared_count = 1
                except OSError as e:
                    print(f"Failed to clear cache for {provider}: {e}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*_resources.json"):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except OSError as e:
                    print(f"Failed to delete {cache_file}: {e}")

        return cleared_count

    async def get_cache_info(self) -> dict[str, dict[str, Any]]:
        """Get cache status information."""
        cache_info = {}

        for cache_file in self.cache_dir.glob("*_resources.json"):
            provider_name = cache_file.stem.replace("_resources", "")

            try:
                async with aiofiles.open(cache_file) as f:
                    content = await f.read()
                    cached_data = json.loads(content)

                cached_time = datetime.fromisoformat(cached_data["timestamp"])
                age_hours = (datetime.now() - cached_time).total_seconds() / 3600

                cache_info[provider_name] = {
                    "timestamp": cached_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "age_hours": round(age_hours, 1),
                    "file_size": cache_file.stat().st_size,
                    "regions_count": len(cached_data["resources"].get("regions", [])),
                    "instance_types_count": sum(
                        len(types)
                        for types in cached_data["resources"]
                        .get("instance_types", {})
                        .values()
                    ),
                }

            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                cache_info[provider_name] = {"error": str(e), "status": "corrupted"}

        return cache_info

    async def cleanup_old_cache(self, max_age_days: int = 7) -> int:
        """Delete old cache files. Returns number of files deleted."""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0

        for cache_file in self.cache_dir.glob("*_resources.json"):
            try:
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)

                if file_mtime < cutoff_time:
                    cache_file.unlink()
                    cleaned_count += 1

            except OSError as e:
                print(f"Failed to check/delete {cache_file}: {e}")

        return cleaned_count
