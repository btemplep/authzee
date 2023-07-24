
__all__ = [
    "StorageBackend",
    "MemoryStorage"
]

from authzee.storage.storage_backend import StorageBackend

from authzee.storage.memory_storage import MemoryStorage
try:
    from authzee.storage.sql_storage import SQLNextPageRef
    from authzee.storage.sql_storage import SQLStorage
    __all__.append("SQLNextPageRef")
    __all__.append("SQLStorage")
except ModuleNotFoundError: # pragma: no cover
    pass
