
from enum import Enum
from typing import Any, Dict, Optional, Set, Type, Union
from typing_extensions import Annotated

from pydantic import BaseModel, Field, validator

from authzee.resource_action import ResourceAction


class Grant(BaseModel):
    """Model for creating a grant.
    
    fill in the model
    """
    name: str
    description: str
    resource_type: Type[BaseModel] 
    actions: Set[Enum] 
    expression: Annotated[str, Field(description="JMESPath expression.")]
    context: Annotated[Dict[str, Any], Field(description="Additional context for the authorization request.")]
    equality: Annotated[
        Union[bool, dict, float, int, list, None, str],
        Field(description="If the JMESPath search matches this, then the grant is a match.")
    ] # store as json string
    storage_id: Optional[str] = None # Leave as a string so storage can decide what it wants
    uuid: Optional[str] = None


    @validator("actions")
    def validate_actions(cls, v):
        for value in v:
            if isinstance(value, ResourceAction) != True:
                raise ValueError("'actions' must come from a child class of ResourceAction")

        return v
    

