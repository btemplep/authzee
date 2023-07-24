
import asyncio
from typing import Any, AsyncIterator, Callable, Coroutine, Iterator, Optional, Union

from pydantic import BaseModel

from authzee.grant import Grant
from authzee.grants_page import GrantsPage


class GrantIter: 

    def __init__(
        self, 
        next_page_callable: Callable[..., GrantsPage],
        page_size: Optional[int] = None,
        next_page_reference: Optional[BaseModel] = None,
        **next_page_kwargs: Any
    ):
        self._next_page_callable = next_page_callable
        self._page_size = page_size
        self._start_page_reference = next_page_reference
        self._next_page_reference = next_page_reference
        self._next_page_kwargs = next_page_kwargs

        self._grants_page: GrantsPage = None
        self._grants_iter: Iterator[Grant] = None


    def __iter__(self) -> Iterator:
        self._next_page_reference = self._start_page_reference
        self._grants_page = None

        return self


    def __next__(self) -> Grant:
        return self._get_next_item()
    

    def _get_next_item(self) -> Grant:
        if self._grants_page is None:
            self._grants_page = self._next_page_callable(
                page_size=self._page_size,
                next_page_reference=self._next_page_reference,
                **self._next_page_kwargs
            )
            self._grants_iter = iter(self._grants_page.grants)
            self._next_page_reference = self._grants_page.next_page_reference

        try:
            return next(self._grants_iter)
        except StopIteration:
            if self._next_page_reference is None:
                raise

            self._grants_page = None
            
            return self._get_next_item()
    

    def __aiter__(self) -> AsyncIterator:
        self._next_page_reference = self._start_page_reference
        self._grants_page = None

        return self


    async def __anext__(self) -> Grant:
        return await self._get_next_item_async()
    

    async def _get_next_item_async(self) -> Grant:
        if self._grants_page is None:
            self._grants_page = await self._next_page_callable(
                page_size=self._page_size,
                next_page_reference=self._next_page_reference,
                **self._next_page_kwargs
            )
            self._grants_iter = iter(self._grants_page.grants)
            self._next_page_reference = self._grants_page.next_page_reference

        try:
            return next(self._grants_iter)
        except StopIteration:
            if self._next_page_reference is None:
                raise StopAsyncIteration

            self._grants_page = None

            return await self._get_next_item_async()

