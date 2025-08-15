"""
Application cache module
"""
from cachelib.file import FileSystemCache

class Cache:
    """
    Cache class to manage application cache using FileSystemCache.
    """
    def __init__(self, cache_dir='cache'):
        self._cache = FileSystemCache(cache_dir, threshold=500, default_timeout=3600)
        if self._cache.get('active_connections') is None:
            self._cache.set('active_connections', [])

    def get(self, key):
        """
        Get the value associated with the key from the cache.
        :param key: The key to retrieve the value for.
        :return: The value associated with the key, or None if not found.
        """
        return self._cache.get(key)

    def set(self, key, value):
        """
        Set the value for the key in the cache.
        :param key: The key to set the value for.
        :param value: The value to set for the key.
        """
        self._cache.set(key, value)

    def delete(self, key):
        """
        Delete the key from the cache.
        :param key: The key to delete from the cache.
        """
        self._cache.delete(key)

    def remove(self, key, value):
        """
        Remove a value from a list associated with the key in the cache.
        :param key: The key to remove the value from.
        :param value: The value to remove from the list.
        """
        items = self._cache.get(key)
        if items is not None:
            items.remove(value)
        else:
            items = []
        self._cache.set(key, items)

    def append(self, key, value):
        """
        Append a value to a list associated with the key in the cache.
        :param key: The key to append the value to.
        :param value: The value to append to the list.
        """
        items = self._cache.get(key)
        if items is None:
            items = []
        items.append(value)
        self._cache.set(key, items)
