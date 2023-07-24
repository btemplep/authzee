
from typing import Set, Type

from pydantic import BaseModel, PrivateAttr

from authzee.resource_action import ResourceAction


class ResourceAuthz(BaseModel): 
    """Resource authorization definitions.

        - actions are the actions that can be performed on the resource.
            - action names must be unique among all resource actions
        - resource is the model for authorization of the resource
            - in many cases this can just be some sort of unique identifier
            - you can also have multiple fields though, but all fields are necessary in a resource model
        - parent_resource_authzs - list of resource authz types for parent resources
            - used in grants to authorize resources with specific parent resources
        - child_resources_authzs - list of resource authz types for child resources
            - used in grants to authorize resources with specific child resources
        

    """

    resource_type: Type[BaseModel]
    resource_action_type: Type[ResourceAction]
    parent_authz_names: Set[str]
    child_authz_names: Set[str]
    _parent_authz_types: Set[Type["ResourceAuthz"]] = PrivateAttr(default_factory=set)
    _child_authz_types: Set[Type["ResourceAuthz"]] = PrivateAttr(default_factory=set)
    _parent_resource_types: Set[Type[BaseModel]] = PrivateAttr(default_factory=set)
    _child_resource_types: Set[Type[BaseModel]] = PrivateAttr(default_factory=set)

