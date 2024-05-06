
import copy
import datetime
from typing import Dict, List, Optional, Set, Type
import uuid

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
from authzee.storage_flag import StorageFlag


class MemoryStorage(StorageBackend):
    """Storage backend for memory. 

    Stores grants in python native data structures. 
    """


    def __init__(self):
        super().__init__(
            backend_locality=BackendLocality.PROCESS,
            default_page_size=10,
            supports_parallel_paging=False
        )
        self._allow_grants: List[Grant] = []
        self._allow_grants_lookup: Dict[str, Grant] = {}
        self._deny_grants: List[Grant] = []
        self._deny_grants_lookup: Dict[str, Grant] = {}
        self._flags_lookup: Dict[str, StorageFlag] = {}


    async def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        await super().initialize(identity_types, resource_authzs)

    
    async def shutdown(self) -> None:
        pass
    
    
    async def teardown(self) -> None:
        self._allow_grants = []
        self._allow_grants_lookup = {}
        self._deny_grants = []
        self._deny_grants_lookup = {}
        self._flags_lookup = {}

    
    async def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        new_grant = self._check_uuid(grant=grant, generate_uuid=True)
        if effect is GrantEffect.ALLOW:
            self._allow_grants.append(new_grant)
            self._allow_grants_lookup[new_grant.uuid] = new_grant
        elif effect is GrantEffect.DENY:
            self._deny_grants.append(new_grant)
            self._deny_grants_lookup[new_grant.uuid] = new_grant

        return copy.deepcopy(new_grant)


    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        if effect is GrantEffect.ALLOW:
            if uuid in self._allow_grants_lookup:
                self._allow_grants_lookup.pop(uuid)
                return
        
        if effect is GrantEffect.DENY:
            if uuid in self._deny_grants_lookup:
                self._deny_grants_lookup.pop(uuid)
                return 

        raise exceptions.GrantDoesNotExistError(
            f"{effect.value} Grant with UUID '{uuid}' does not exist.")


    async def get_raw_grants_page(
        self, 
        effect: GrantEffect, 
        resource_type: Optional[Type[BaseModel]] = None,
        action: Optional[ResourceAction] = None,
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
        
        if action is not None:
            grants = [grant for grant in grants if action in grant.actions]
        
        return RawGrantsPage(
            raw_grants=grants,
            next_page_ref=None
        )
    

    async def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        return GrantsPage(
            grants=raw_grants_page.raw_grants,
            next_page_ref=raw_grants_page.next_page_ref
        )
    

    async def create_flag(self) -> StorageFlag:
        """Create a new shared flag in the storage backend.

        Returns
        -------
        StorageFlag
            New storage flag. 
        """
        new_flag = StorageFlag()
        self._flags_lookup[new_flag.uuid] = new_flag

        return copy.deepcopy(new_flag)


    async def get_flag(self, uuid: str) -> StorageFlag:
        """Retrieve flag by UUID.

        Parameters
        ----------
        uuid : str
            Storage flag UUID.

        Returns
        -------
        StorageFlag
            The storage flag with the given UUID.
        
        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        self._check_flag_uuid_exists(uuid=uuid)
        
        return copy.deepcopy(self._flags_lookup[uuid])


    async def set_flag(self, uuid: str) -> StorageFlag:
        """Set a flag for a given UUID. 

        Parameters
        ----------
        uuid : str
            Storage flag UUID.

        Returns
        -------
        StorageFlag
            The storage flag with the given UUID and the flag set.
        
        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        self._check_flag_uuid_exists(uuid=uuid)
        flag = self._flags_lookup[uuid]
        flag.is_set = True

        return copy.deepcopy(flag)


    async def delete_flag(self, uuid: str) -> None:
        """Delete a storage flag by UUID.

        Parameters
        ----------
        uuid : str
            Storage flag UUID.
        
        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        self._check_flag_uuid_exists(uuid=uuid)
        self._flags_lookup.pop(uuid)


    async def cleanup_flags(self, earlier_than: datetime.datetime) -> None:
        """Delete zombie storage flags from before a certain point in time.

        Parameters
        ----------
        earlier_than : datetime.datetime
            Delete flags created earlier than this date. 
            Naive datetimes are assumed to be UTC. 
        """
        if earlier_than.tzinfo is None:
            earlier_than = earlier_than.replace(tzinfo=datetime.timezone.utc)
        elif earlier_than.tzinfo is not None:
            earlier_than = earlier_than.astimezone(datetime.timezone.utc)

        delete_uuids = []
        for uuid in self._flags_lookup:
            if self._flags_lookup[uuid].created_at < earlier_than:
                delete_uuids.append(uuid)

        for uuid in delete_uuids:
            self._flags_lookup.pop(uuid)


    def _check_flag_uuid_exists(self, uuid: str) -> None:
        """Check that a flag with the given UUID exists and return it. 

        Parameters
        ----------
        uuid : str
            Storage flag UUID. 

        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        if uuid not in self._flags_lookup:
            raise exceptions.StorageFlagNotFoundError(
                f"The storage flag with UUID '{uuid}' was not found!"
            )