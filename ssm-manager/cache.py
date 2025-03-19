"""
Application cache module
"""
from cachelib.file import FileSystemCache

class Cache:
    def __init__(self):
        self.cache = FileSystemCache(cache_dir='cache', threshold=500, default_timeout=3600)
        if self.cache.get('active_connections') is None:
            self.cache.set('active_connections', [])

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache.set(key, value)

    def delete(self, key):
        self.cache.delete(key)

    def remove(self, key, value):
        items = self.cache.get(key)
        if items is not None:
            items.remove(value)
        self.cache.set(key, items)

    def append(self, key, value):
        items = self.cache.get(key)
        if items is None:
            items = []
        items.append(value)
        self.cache.set(key, items)
