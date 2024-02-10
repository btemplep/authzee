
from typing import Any, Dict, List, Union

from pydantic import BaseModel

from authzee.grant import Grant


class GrantsPage(BaseModel):

    grants: List[Grant]
    next_page_ref: Union[str, None]

