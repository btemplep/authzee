
from typing import Any, Union

from pydantic import BaseModel


class RawGrantsPage(BaseModel):

    raw_grants: Any
    next_page_ref: Union[str, None]

