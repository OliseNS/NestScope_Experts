"""
Flood Intelligence Cache Manager
=================================

Persistent cache for flood intelligence data to enable instant loading
with background updates.

Cache Strategy:
1. Load from cache file instantly (< 100ms)
2. Trigger background update if cache is stale (> 5 minutes)
3. Update UI progressively as new data arrives
"""

import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import threading

logger = logging.getLogger(__name__)

# Cache file location
CACHE_DIR = Path("data/cache")
FLOOD_CACHE_FILE = CACHE_DIR / "flood_intelligence.json"

# Cache settings
CACHE_TTL_MINUTES = 5  # Cache is "fresh" for 5 minutes
CACHE_STALE_MINUTES = 30  # Cache is "stale" after 30 minutes (force refresh)


class FloodIntelligenceCache:
    """
    Manages persistent cache for flood intelligence data.

    Features:
    - Instant cache reads (< 100ms)
    - Background async updates
    - Progressive data loading
    """

    def __init__(self):
        self.cache_file = FLOOD_CACHE_FILE
        self.lock = threading.Lock()

        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get_cached_data(self) -> Optional[Dict]:
        """
        Get cached flood intelligence data.
        Returns None if no cache exists.

        Returns:
            Dict with 'data', 'timestamp', 'age_seconds'
        """
        try:
            if not self.cache_file.exists():
                logger.info("No flood intelligence cache found")
                return None

            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            # Calculate age
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            age = (datetime.now() - cached_time).total_seconds()

            cache_data['age_seconds'] = age
            cache_data['age_minutes'] = age / 60
            cache_data['is_fresh'] = age < (CACHE_TTL_MINUTES * 60)
            cache_data['is_stale'] = age > (CACHE_STALE_MINUTES * 60)

            logger.info(f"Loaded flood cache: {age/60:.1f} minutes old")
            return cache_data

        except Exception as e:
            logger.error(f"Error reading flood cache: {e}")
            return None

    def save_cache(self, data: Dict) -> bool:
        """
        Save flood intelligence data to cache.

        Args:
            data: Dictionary with priorities, zones, stats, etc.

        Returns:
            True if successful
        """
        try:
            with self.lock:
                cache_data = {
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }

                # Atomic write (write to temp, then rename)
                temp_file = self.cache_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)

                temp_file.replace(self.cache_file)

            logger.info(f"Saved flood intelligence cache ({len(data.get('priorities', []))} colonies)")
            return True

        except Exception as e:
            logger.error(f"Error saving flood cache: {e}")
            return False

    def needs_refresh(self) -> bool:
        """
        Check if cache needs refresh (older than TTL).

        Returns:
            True if cache is missing or older than TTL
        """
        cached = self.get_cached_data()
        if not cached:
            return True

        return not cached['is_fresh']

    def is_stale(self) -> bool:
        """
        Check if cache is critically stale (force user to wait).

        Returns:
            True if cache is older than stale threshold
        """
        cached = self.get_cached_data()
        if not cached:
            return True

        return cached['is_stale']

    def clear_cache(self):
        """Delete the cache file"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("Cleared flood intelligence cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


# Singleton instance
_cache = None

def get_flood_cache() -> FloodIntelligenceCache:
    """Get singleton cache instance"""
    global _cache
    if _cache is None:
        _cache = FloodIntelligenceCache()
    return _cache
