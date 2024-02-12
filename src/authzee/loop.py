
import asyncio


def get_running_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_running_loop()


def get_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_event_loop()

