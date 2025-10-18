"""Cache addon for caching responses."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from .base_addon import BaseAddon, AddonContext


class CacheAddon(BaseAddon):
    """
    Addon for caching API responses.
    
    Features:
    - In-memory cache with configurable TTL
    - LRU eviction when max size is reached
    - Cache key based on prompt, model, and parameters
    - Cache statistics (hits, misses, size)
    
    Example:
        ```python
        cache = CacheAddon(
            max_size=100,
            ttl_seconds=3600  # 1 hour
        )
        
        # Use in session
        session.add_addon(cache)
        
        # Check stats
        stats = cache.get_stats()
        print(f"Cache hits: {stats['hits']}, misses: {stats['misses']}")
        ```
    """
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: Optional[int] = 3600,
    ):
        """
        Initialize cache addon.
        
        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time-to-live in seconds (None for no expiration)
        """
        super().__init__()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order: list[str] = []  # For LRU
        self._hits = 0
        self._misses = 0
    
    def get_name(self) -> str:
        """Get addon name."""
        return "Cache Addon"
    
    def get_description(self) -> str:
        """Get addon description."""
        return f"Caches responses (max: {self.max_size}, TTL: {self.ttl_seconds}s)"
    
    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        **kwargs: Any
    ) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: The prompt
            model: Model name
            **kwargs: Additional parameters
        
        Returns:
            Cache key hash
        """
        # Create deterministic key from prompt, model, and sorted kwargs
        key_data = {
            "prompt": prompt,
            "model": model,
            "params": {k: v for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _is_expired(self, cached_item: dict[str, Any]) -> bool:
        """
        Check if cached item is expired.
        
        Args:
            cached_item: Cached item with timestamp
        
        Returns:
            True if expired
        """
        if self.ttl_seconds is None:
            return False
        
        cached_time = cached_item["timestamp"]
        expiry_time = cached_time + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
    
    def _update_access(self, key: str) -> None:
        """Update access order for LRU."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def pre_request(
        self,
        prompt: str,
        context: AddonContext
    ) -> Optional[str]:
        """
        Check cache before making request.
        
        Args:
            prompt: The prompt
            context: Addon context
        
        Returns:
            Cached response content if found, None otherwise
        """
        # Generate cache key
        cache_key = self._generate_cache_key(
            prompt,
            context.model,
            provider=context.provider,
        )
        
        # Check if in cache
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            
            # Check if expired
            if self._is_expired(cached_item):
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._misses += 1
                return None
            
            # Cache hit
            self._hits += 1
            self._update_access(cache_key)
            
            # Store cache info in context
            context.custom["cache_hit"] = True
            context.custom["cache_key"] = cache_key
            
            # Return cached content
            return cached_item["response"]["content"]
        
        # Cache miss
        self._misses += 1
        context.custom["cache_hit"] = False
        context.custom["cache_key"] = cache_key
        
        return None
    
    async def post_request(
        self,
        response: dict[str, Any],
        context: AddonContext
    ) -> dict[str, Any]:
        """
        Cache the response after successful request.
        
        Args:
            response: Response from provider
            context: Addon context
        
        Returns:
            Original response
        """
        # Only cache if it wasn't a cache hit
        if not context.custom.get("cache_hit", False):
            cache_key = context.custom.get("cache_key")
            
            if cache_key:
                # Evict if at max size
                if len(self._cache) >= self.max_size:
                    self._evict_lru()
                
                # Store in cache
                self._cache[cache_key] = {
                    "response": response,
                    "timestamp": datetime.now(),
                }
                self._update_access(cache_key)
        
        return response
    
    def clear_cache(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._access_order.clear()
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_size": self.max_size,
        }
    
    def get_cache_size(self) -> int:
        """Get current number of cached items."""
        return len(self._cache)

