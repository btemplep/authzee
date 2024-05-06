
from typing import Set, Type

from pydantic import BaseModel

from authzee.resource_action import ResourceAction


class ResourceAuthz(BaseModel): 
    """Resource authorization definitions.

    Parameters
    ----------
    resource_type : Type[BaseModel]
        Resource type for authorization.
    action_type : Type[ResourceAction]
        Resource actions to associate with the resource authorization.
    parent_types : Set[Type[BaseModel]]
        Parent resource types to associate with the resource authorization.
        Used to validate requests for correct parent resource types.
    child_types : Set[Type[BaseModel]]
        Child resource types to associate with the resource authorization.
        Used to validate requests for correct child resource types.
    """
    resource_type: Type[BaseModel]
    action_type: Type[ResourceAction]
    parent_types: Set[Type[BaseModel]]
    child_types: Set[Type[BaseModel]]

