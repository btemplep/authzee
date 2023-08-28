
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


    async_enabled: bool = False
    backend_locality: BackendLocality = BackendLocality.MAIN_PROCESS
    compute_locality_compatibility: Set[BackendLocality] = {
        BackendLocality.MAIN_PROCESS,
        BackendLocality.NETWORK,
        BackendLocality.SYSTEM
    }


    def __init__(self):
        super().__init__(
            default_page_size=1000
        )


    def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        super().initialize(identity_types, resource_authzs)
        self._allow_grants_lookup: Dict[str, Grant] = {}
        self._deny_grants_lookup: Dict[str, Grant] = {}

    
    def shutdown(self):
        pass

    
    def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        grant = self._check_uuid(grant=grant, generate_uuid=True)
        if effect is GrantEffect.ALLOW:
            self._allow_grants_lookup[grant.uuid] = grant
        elif effect is GrantEffect.DENY:
            self._deny_grants_lookup[grant.uuid] = grant

        return grant


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


    def get_raw_grants_page(
        self, 
        effect: GrantEffect, 
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        next_page_reference: Optional[str] = None
    ) -> RawGrantsPage:
        if effect == GrantEffect.ALLOW:
            grants: List[Grant] = copy.deepcopy(list(self._allow_grants_lookup.values()))
        elif effect == GrantEffect.DENY:
            grants: List[Grant] = copy.deepcopy(list(self._deny_grants_lookup.values()))
        
        if resource_type is not None:
            grants = [grant for grant in grants if grant.resource_type == resource_type]
        
        if resource_action is not None:
            grants = [grant for grant in grants if resource_action in grant.resource_actions]
        
        return RawGrantsPage(
            raw_grants=grants,
            next_page_reference=None
        )
    

    def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        return GrantsPage(
            grants=raw_grants_page.raw_grants,
            next_page_reference=raw_grants_page.next_page_reference
        )

