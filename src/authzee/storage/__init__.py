
__all__ = [
    "StorageBackend",
    "MemoryStorage",
    "ParallelMemoryStorage"
]

from authzee.storage.storage_backend import StorageBackend

from authzee.storage.memory_storage import MemoryStorage
from authzee.storage.parallel_memory_storage import ParallelMemoryStorage
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
