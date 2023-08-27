

from multiprocessing.managers import SharedMemoryManager


class SharedMemEvent:


    def __init__(self, smm: SharedMemoryManager):
        self._sm = smm.SharedMemory(size=1)
    

    def is_set(self) -> bool:
        return self._sm.buf[0] == 1
    

    def set(self) -> None:
        self._sm.buf[0] = 1
    
    
    def clear(self) -> None:
        self._sm.buf[0] = 0


    def unlink(self) -> None:
        self._sm.unlink()


