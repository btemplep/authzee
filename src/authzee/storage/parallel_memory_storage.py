
import copy
import datetime
from typing import Dict, List, Optional, Set, Type, Union
import uuid

from pydantic import BaseModel

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.page_refs_page import PageRefsPage
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend
from authzee.storage_flag import StorageFlag


class ParallelMemoryStorage(StorageBackend):
    """Test parallel storage backend for memory. 

    Stores grants in python native data structures. 

    Offers parallel pagination for testing. 
    """


    def __init__(self):
        super().__init__(
            backend_locality=BackendLocality.PROCESS,
            default_page_size=10,
            parallel_pagination=True
        )
        self._grants: Dict[GrantEffect, Dict[str, Grant]] = {}
        self._grants_rtype: Dict[GrantEffect, Dict[Type[BaseModel], List[str]]] = {}
        self._grants_action: Dict[GrantEffect, Dict[ResourceAction, List[str]]] = {}
        self._flags_lookup: Dict[str, StorageFlag] = {}


    async def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        await super().initialize(identity_types, resource_authzs)
        self._grants[GrantEffect.ALLOW] = {}
        self._grants[GrantEffect.DENY] = {}
        self._grants_rtype[GrantEffect.ALLOW] = {}
        self._grants_rtype[GrantEffect.DENY] = {}
        self._grants_action[GrantEffect.ALLOW] = {}
        self._grants_action[GrantEffect.DENY] = {}
        for ra in resource_authzs:
            self._grants_rtype[GrantEffect.ALLOW][ra.resource_type] = []
            self._grants_rtype[GrantEffect.DENY][ra.resource_type] = []
            for action in ra.resource_action_type:
                self._grants_action[GrantEffect.ALLOW][action] = []
                self._grants_action[GrantEffect.DENY][action] = []


    async def shutdown(self) -> None:
        pass
    
    
    async def teardown(self) -> None:
        pass

    
    async def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        new_grant = self._check_uuid(grant=grant, generate_uuid=True)
        self._grants[effect][new_grant.uuid] = new_grant
        self._grants_rtype[effect][grant.resource_type].append(new_grant.uuid)
        for action in new_grant.actions:
            self._grants_action[effect][action].append(grant.uuid)

        return copy.deepcopy(new_grant)


    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        ga = self._grants_action[effect].pop(uuid, None)
        gr = self._grants_rtype[effect].pop(uuid, None)
        g = self._grants[effect].pop(uuid, None)
        if ga is None or gr is None or g is None: 
            raise exceptions.GrantDoesNotExistError(
                f"{effect.value} Grant with UUID '{uuid}' does not exist.")


    async def get_raw_grants_page(
        self, 
        effect: GrantEffect, 
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> RawGrantsPage:
        if page_size is None:
            page_size = self.default_page_size

        grant_keys = list(self._grants[effect].keys())
        if page_ref is None:
            start_index = 0
        else:
            start_index = int(page_ref)
        
        if resource_action is not None:
            grant_keys = self._grants_action[effect][resource_action]
        elif resource_type is not None:
            grant_keys = self._grants_rtype[effect][resource_type]
        
        end_index = start_index + page_size
        next_start_index = end_index + 1
        if next_start_index < len(grant_keys) - 1:
            page_ref = str(next_start_index)
        else:
            page_ref = None
        
        return RawGrantsPage(
            raw_grants={
                "effect": effect,
                "uuids": grant_keys
            },
            next_page_ref=page_ref
        )
    

    async def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        effect = raw_grants_page.raw_grants['effect']
        grants = []
        for uuid in raw_grants_page.raw_grants:
            try:
                grants.append(self._grants[effect][uuid])
            except KeyError:
                pass
    
        return GrantsPage(
            grants=copy.deepcopy(grants),
            next_page_ref=raw_grants_page.next_page_ref
        )
    

    async def get_page_ref_page(
        self, 
        effect: GrantEffect, 
        resource_type: Union[BaseModel, None] = None, 
        resource_action: Union[ResourceAction, None] = None, 
        page_size: Union[int, None] = None, 
        refs_page_size: Union[int, None] = None,
        page_ref: Union[str, None] = None
    ) -> PageRefsPage:
        if page_size is None:
            page_size = self.default_page_size
        
        if refs_page_size is None:
            refs_page_size = self.default_page_size

        if page_ref is None:
            start_index = 0
        else:
            start_index = int(page_ref) 
        
        if resource_action is not None:
            grant_keys = self._grants_action[effect][resource_action]
        elif resource_type is not None:
            grant_keys = self._grants_rtype[effect][resource_type]
        else:
            grant_keys = list(self._grants[effect].keys())

        page_refs = []
        next_page_ref = None
        for page_start in range(start_index, len(grant_keys), page_size):
            if len(page_refs) < refs_page_size:
                page_refs.append(str(page_start))
            else:
                next_page_ref = str(page_start)
                break
        
        return PageRefsPage(
            page_refs=page_refs,
            next_page_ref=next_page_ref
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