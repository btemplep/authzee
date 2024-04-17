
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

try:
    from authzee.storage.s3_storage import S3Storage, S3PageRef
    __all__.append("S3PageRef")
    __all__.append("S3Storage")
except ModuleNotFoundError:
    pass
