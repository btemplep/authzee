
import copy
from typing import List, Optional, Set, Type, Union
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


class StorageBackend:
    """Base class for ``Authzee`` storage. 

    Base classes must at least implement:

        - ``initialize`` - Initialize the storage backend. External connections should be created here
        - ``shutdown`` - Preemptively cleanup storage backend resources.
        - ``setup`` - One time setup for compute backend.
        - ``teardown`` - Remove resources created from ``setup()``.
        - ``add_grant`` - Add a grant to storage.
        - ``delete_grant`` - Delete a grant from storage.
        - ``get_raw_grants_page`` - Retrieve a page of raw grants from storage. 
        - ``normalize_raw_grants_page`` - Convert the raw storage grants to a list of ``Grant`` models.
    
    Optionally ``async`` methods may also be created for calls to storage. 

        - ``add_grant_async``
        - ``delete_grant_async``
        - ``get_grants_page_async``
        - ``normalize_raw_grants_page_async`` - Convert the raw storage grants to a list of ``Grant`` models.

    The sub-class must also set the class vars:

        - ``async_enabled`` - The class has all ``async`` methods available.
        - ``process_safe`` - The storage is safe between processes ie. external to the running program.

    No error checking should be needed for validation of resources, resource_types etc. That should all be handled by ``Authzee``.

    Storage backends should store all arguments to the ``__init__`` method in ``self.kwargs``, 
    and all arguments to the ``initialize`` method in ``self.initialize_kwargs``.  
    These should be available if the compute backend needs to instantiate more instances of the storage backend.

    Parameters
    ----------
    async_enabled : bool
        This instance of the storage backend is async enabled.
        It has all async methods.
        This parameter should not be exposed on the child class.
    backend_locality : BackendLocality
        The backend locality this instance of the storage backend supports.
        See ``authzee.backend_locality.BackendLocality`` for more info on what the localites mean.
        This parameter should not be exposed on the child class.
    compatible_localities : Set[BackendLocality]
        Set of compatible compute backend localities.
        This parameter should not be exposed on the child class.
    default_page_size : int
        For methods that accept ``page_size``, this will be used as the default.
    """


    def __init__(
        self, 
        *, 
        async_enabled: bool,
        backend_locality: BackendLocality,
        compatible_localities: Set[BackendLocality],
        default_page_size: int, 
        **kwargs
    ):
        self.async_enabled = async_enabled
        self.backend_locality = backend_locality
        self.compatible_localities = compatible_localities
        # Reassign all to a method with a better error
        if async_enabled is False:
            self.add_grant_async = self._async_not_supported
            self.delete_grant_async = self._async_not_supported
            self.get_raw_grants_page_async = self._async_not_supported
            self.normalize_raw_grants_page_async = self._async_not_supported

        self.default_page_size = default_page_size
        self.kwargs = kwargs
        self.kwargs['default_page_size'] = default_page_size
        self.initialize_kwargs = {}


    def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        """Initialize the storage backend. 

        All creation of connections to external storage should take place here,
        but not creation of resources in the storage.  ie don't create tables.

        Parameters
        ----------
        identity_types : Set[Type[BaseModel]]
            Identity types that have been registered with ``Authzee``.
        resource_authzs : List[ResourceAuthz]
            ``ResourceAuthz`` instances that have been registered with ``Authzee``.
        """
        self.initialize_kwargs = {
            "identity_types": identity_types,
            "resource_authzs": resource_authzs
        }
        self._identity_types = identity_types
        self._resource_authzs = resource_authzs
    

    def shutdown(self) -> None:
        """Early clean up of storage backend resources.
        """
        pass


    def setup(self) -> None:
        """One time setup for storage backend resources.
        """
        pass

    
    def teardown(self) -> None:
        """Teardown and delete the results of ``setup()`` .
        """
        pass

    
    def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        """Add a grant. 

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        grant : Grant
            The grant.

        Returns
        -------
        Grant
            The grant that has been added with additional information for the specific backend.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
    

    async def add_grant_async(self, effect: GrantEffect, grant: Grant) -> Grant:
        """Add a grant. 

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        grant : Grant
            The grant.

        Returns
        -------
        Grant
            The grant that has been added with additional information for the specific backend.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes *may* implement this method if ``async`` is supported.
        """
        raise exceptions.MethodNotImplementedError()


    def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()


    async def delete_grant_async(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes *may* implement this method if ``async`` is supported.
        """
        raise exceptions.MethodNotImplementedError()
        

    def get_raw_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        next_page_reference: Optional[str] = None
    ) -> RawGrantsPage:
        """Retrieve a page of raw grants matching the filters.

        If ``RawGrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=RawGrantsPage.next_page_reference`` .

        Use ``normalize_raw_grants_page`` to convert the ``RawGrantsPage`` to a ``GrantsPage`` model.

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        resource_action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The suggested page size to return. 
            There is no guarantee of how much data will be returned if any.
            The default is set on the storage backend. 
        next_page_reference : Optional[str], optional
            The reference to the next page that is returned in ``RawGrantsPage``.
            By default this will return the first page.

        Returns
        -------
        RawGrantsPage
            The page of raw grants.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
    

    async def get_raw_grants_page_async(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        next_page_reference: Optional[str] = None
    ) -> RawGrantsPage:
        """Retrieve a page of raw grants matching the filters.

        If ``RawGrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=RawGrantsPage.next_page_reference`` .

        Use ``normalize_raw_grants_page`` to convert the ``RawGrantsPage`` to a ``GrantsPage`` model.

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        resource_action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The suggested page size to return. 
            There is no guarantee of how much data will be returned if any.
            The default is set on the storage backend. 
        next_page_reference : Optional[str], optional
            The reference to the next page that is returned in ``RawGrantsPage``.
            By default this will return the first page.

        Returns
        -------
        RawGrantsPage
            The page of raw grants.


        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes *may* implement this method if ``async`` is supported.
        """
        raise exceptions.MethodNotImplementedError()
    

    def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        """Convert a ``RawGrantsPage`` to a ``GrantsPage``.

        Parameters
        ----------
        raw_grants_page : RawGrantsPage
            Raw grants page to convert.

        Returns
        -------
        GrantsPage
            Normalized grants page.
        
        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()


    async def normalize_raw_grants_page_async(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        """Convert a ``RawGrantsPage`` to a ``GrantsPage``.

        Parameters
        ----------
        raw_grants_page : RawGrantsPage
            Raw grants page to convert.

        Returns
        -------
        GrantsPage
            Normalized grants page.
        
        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()


    def _check_uuid(self, grant: Grant, generate_uuid: bool) -> Grant:
        """Check if a UUID is on a grant to add, optionally generate a UUID with UUID 4.


        Parameters
        ----------
        grant : Grant
            The grant to check.
        generate_uuid : bool
            Optionally generate a UUID and add it to the grant. 

        Returns
        -------
        Grant
            A deep copy of the passed in grant, optionally with a UUID 4 added.

        Raises
        ------
        authzee.exceptions.GrantUUIDError
            Grants that are being added should not have a UUID.
        """
        if grant.uuid is not None:
            raise exceptions.GrantUUIDError("Cannot create a grant that has a UUID.")

        grant = copy.deepcopy(grant)
        if generate_uuid == True:
            grant.uuid = str(uuid.uuid4())
        
        return grant
    

    def _real_page_size(self, page_size: Union[int, None]) -> int:
        if page_size is None:
            return self.default_page_size
    
        return page_size


    async def _async_not_supported(self, *args, **kwargs) -> None:
        raise exceptions.MethodNotImplementedError(
            "Async is not supported by this storage backend instance."
        )


