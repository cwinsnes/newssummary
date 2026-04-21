import pickle
import hashlib
import functools
import logging
import threading
import datetime
import os
from pathlib import Path
from typing import Any, Callable, Dict

CACHE_DIR = Path(".news_cache")

class DailyCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._current_date: datetime.date | None = None
        self._cache_dir_ready = False

    def _get_cache_file(self, date: datetime.date) -> Path:
        return self.cache_dir / f"cache_{date.isoformat()}.pkl"

    def _ensure_loaded(self):
        """Ensure the cache for today is loaded into memory."""
        today = datetime.date.today()
        
        if not self._cache_dir_ready:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_dir_ready = True

        if self._current_date != today:
            self._current_date = today
            cache_file = self._get_cache_file(today)
            if cache_file.exists():
                try:
                    with open(cache_file, "rb") as f:
                        self._data = pickle.load(f)
                except Exception as e:
                    logging.warning(f"Failed to load daily cache: {e}")
                    self._data = {}
            else:
                self._data = {}

    def get(self, key: str) -> Any:
        with self.lock:
            self._ensure_loaded()
            return self._data.get(key)

    def set(self, key: str, value: Any):
        with self.lock:
            self._ensure_loaded()
            self._data[key] = value
            
            # Persist to disk atomically
            cache_file = self._get_cache_file(self._current_date)
            try:
                temp_file = cache_file.with_suffix(".tmp")
                with open(temp_file, "wb") as f:
                    pickle.dump(self._data, f)
                # Atomic replace
                os.replace(temp_file, cache_file)
            except Exception as e:
                logging.warning(f"Failed to save daily cache: {e}")

# Global cache instance
_MANAGER = DailyCache(CACHE_DIR)

def disk_cache(func: Callable) -> Callable:
    """
    An optimized persistent cache that stores all results for a given day
    in a single pickle file.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # Generate a unique key for this function and its arguments
            key_data = pickle.dumps((func.__name__, args, kwargs))
            key_hash = hashlib.sha256(key_data).hexdigest()
            
            # Check the daily manager
            cached_result = _MANAGER.get(key_hash)
            if cached_result is not None:
                return cached_result

            # Not in cache, execute
            result = func(*args, **kwargs)
            
            # Store in cache
            _MANAGER.set(key_hash, result)
                
            return result
        except Exception as e:
            logging.warning(f"Cache subsystem error in {func.__name__}: {e}")
            return func(*args, **kwargs)
            
    return wrapper

def cleanup_legacy_cache():
    """Remove individual .pkl files from previous implementation."""
    if not CACHE_DIR.exists():
        return
    for p in CACHE_DIR.glob("*.pkl"):
        # Legacy files were hex-named (64 chars), new ones start with 'cache_'
        if not p.name.startswith("cache_") and len(p.stem) == 64:
            try:
                p.unlink()
            except Exception:
                pass

# Run cleanup on import
cleanup_legacy_cache()
