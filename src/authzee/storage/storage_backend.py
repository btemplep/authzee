
import copy
from typing import List, Optional, Set, Type, Union
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


class StorageBackend:
    """Base class for ``Authzee`` storage. 

    Base classes must at least implement these async methods:

        - ``initialize`` - Initialize the storage backend. External connections should be created here
        - ``shutdown`` - Preemptively cleanup storage backend resources.
        - ``setup`` - One time setup for compute backend.
        - ``teardown`` - Remove resources created from ``setup()``.
        - ``add_grant`` - Add a grant to storage.
        - ``delete_grant`` - Delete a grant from storage.
        - ``get_raw_grants_page`` - Retrieve a page of raw grants from storage. 
        - ``normalize_raw_grants_page`` - Convert the raw storage grants to a list of ``Grant`` models.
    
    Optional async methods:
        - ``get_page_ref_page`` - For parallel pagination.  Retrieve a page of page references. 
            Set ``parallel_pagination`` flag if this is implemented.

    No error checking should be needed for validation of resources, resource_types etc. That should all be handled by ``Authzee``.

    Storage backends should store all arguments to the ``__init__`` method in ``self.kwargs``, 
    and all arguments to the ``initialize`` method in ``self.initialize_kwargs``.  
    These should be available if the compute backend needs to instantiate more instances of the storage backend.

    Parameters
    ----------
    backend_locality : BackendLocality
        The backend locality this instance of the storage backend supports.
        See ``authzee.backend_locality.BackendLocality`` for more info on what the localites mean.
        This parameter should not be exposed on the child class.
    default_page_size : int
        For methods that accept ``page_size``, this will be used as the default.
    parallel_pagination : bool
        Flag for if this storage backend support parallel pagination. 
        If it does then it must implement the ``get_page_ref_page`` async method.
    """


    def __init__(
        self, 
        *, 
        backend_locality: BackendLocality,
        default_page_size: int, 
        parallel_pagination: bool,
        **kwargs
    ):
        self.backend_locality = backend_locality
        self.default_page_size = default_page_size
        self.parallel_pagination = parallel_pagination
        self.kwargs = kwargs
        self.initialize_kwargs = {}


    async def initialize(
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
    

    async def shutdown(self) -> None:
        """Early clean up of storage backend resources.
        """
        pass


    async def setup(self) -> None:
        """One time setup for storage backend resources.
        """
        pass

    
    async def teardown(self) -> None:
        """Teardown and delete the results of ``setup()`` .
        """
        pass

    
    async def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
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


    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
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
        

    async def get_raw_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> RawGrantsPage:
        """Retrieve a page of raw grants matching the filters.

        If ``RawGrantsPage.next_page_ref`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``page_ref=RawGrantsPage.next_page_ref`` .

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
        page_ref : Optional[str], optional
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
    

    async def normalize_raw_grants_page(
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
    

    async def get_page_ref_page(self, page_ref: str) -> PageRefsPage:
        """Get a page of page references for parallel pagination. 

        Parameters
        ----------
        page_ref : str
            Page reference for the next page of page references.

        Returns
        -------
        PageRefsPage
            Page of page references.

        Raises
        ------
        exceptions.MethodNotImplementedError
            Sub-classes must implement this method if this storage backend supports parallel pagination. 
            They must also set the ``parallel_pagination`` flag. 
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

