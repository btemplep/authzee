
from typing import Any, Optional, Set, Type, Union

from pydantic import BaseModel, validator

from authzee.resource_action import ResourceAction


class Grant(BaseModel):
    """Model for creating a grant.
    
    fill in the model
    """

    name: str
    description: str
    resource_type: Type[BaseModel] 
    resource_actions: Set[Any] 
    jmespath_expression: str
    result_match: Union[bool, dict, float, int, list, None, str] # store as json string
    page_id: Optional[int] = None
    uuid: Optional[str] = None


    @validator("resource_actions")
    def validate_actions(cls, v):
        for value in v:
            if isinstance(value, ResourceAction) != True:
                raise ValueError("'resource_actions' must come from a child class of ResourceAction")

        return v
    

