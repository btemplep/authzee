
from typing import List, Union

from pydantic import BaseModel


class PageRefsPage(BaseModel):
    page_refs: List[str]
    next_page_ref: Union[str, None]
