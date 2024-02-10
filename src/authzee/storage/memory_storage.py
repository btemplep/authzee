
import copy
from typing import Dict, List, Optional, Set, Type

from pydantic import BaseModel

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend


class MemoryStorage(StorageBackend):
    """Storage backend for memory. 

    Stores grants in python native data structures.
    """


    def __init__(self):
        super().__init__(
            async_enabled=True,
            backend_locality=BackendLocality.MAIN_PROCESS,
            compatible_localities={
                BackendLocality.MAIN_PROCESS,
                BackendLocality.NETWORK,
                BackendLocality.SYSTEM
            },
            default_page_size=10,
        )
        self._allow_grants: List[Grant] = []
        self._allow_grants_lookup: Dict[str, Grant] = {}
        self._deny_grants: List[Grant] = []
        self._deny_grants_lookup: Dict[str, Grant] = {}



    def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        super().initialize(identity_types, resource_authzs)
        

    
    def shutdown(self) -> None:
        pass
    
    
    def teardown(self) -> None:
        self._allow_grants = []
        self._allow_grants_lookup = {}
        self._deny_grants = []
        self._deny_grants_lookup = {}

    
    def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        new_grant = self._check_uuid(grant=grant, generate_uuid=True)
        if effect is GrantEffect.ALLOW:
            self._allow_grants.append(new_grant)
            self._allow_grants_lookup[new_grant.uuid] = new_grant
        elif effect is GrantEffect.DENY:
            self._deny_grants.append(new_grant)
            self._deny_grants_lookup[new_grant.uuid] = new_grant

        return copy.deepcopy(new_grant)


    async def add_grant_async(self, effect: GrantEffect, grant: Grant) -> Grant:
        return self.add_grant(effect=effect, grant=grant)


    def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        if effect is GrantEffect.ALLOW:
            if uuid in self._allow_grants_lookup:
                self._allow_grants_lookup.pop(uuid)
                return
        
        if effect is GrantEffect.DENY:
            if uuid in self._deny_grants_lookup:
                self._deny_grants_lookup.pop(uuid)
                return 

        raise exceptions.GrantDoesNotExistError("{} Grant with UUID '{}' does not exist.".format(effect.value, uuid))


    async def delete_grant_async(self, effect: GrantEffect, uuid: str) -> None:
        return self.delete_grant(effect=effect, uuid=uuid)


    def get_raw_grants_page(
        self, 
        effect: GrantEffect, 
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> RawGrantsPage:
        if page_size is None:
            page_size = self.default_page_size
        if effect == GrantEffect.ALLOW:
            grants = self._allow_grants
        elif effect == GrantEffect.DENY:
            grants = self._deny_grants
        
        if page_ref is None:
            start_index = 0
        else:
            start_index = page_ref + 1
        
        end_index = start_index + page_size
        page_ref = str(end_index)
        if end_index >= len(grants) - 1:
            end_index = None
            page_ref = None

        grants = copy.deepcopy(grants[start_index:end_index])
        
        if resource_type is not None:
            grants = [grant for grant in grants if grant.resource_type == resource_type]
        
        if resource_action is not None:
            grants = [grant for grant in grants if resource_action in grant.resource_actions]
        
        return RawGrantsPage(
            raw_grants=grants,
            next_page_ref=None
        )


    async def get_raw_grants_page_async(
        self, effect: GrantEffect, 
        resource_type: Optional[type[BaseModel]] = None, 
        resource_action: Optional[ResourceAction]= None, 
        page_size: Optional[int] = None, 
        page_ref: Optional[str] = None
    ) -> RawGrantsPage:
        return self.get_raw_grants_page(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            page_ref=page_ref
        )
    

    def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        return GrantsPage(
            grants=raw_grants_page.raw_grants,
            next_page_ref=raw_grants_page.next_page_ref
        )


    async def normalize_raw_grants_page_async(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        return self.normalize_raw_grants_page(
            raw_grants_page=raw_grants_page
        )
