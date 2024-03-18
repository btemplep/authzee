

from typing import Any, Dict, List, Optional, Type, Union

import jmespath
from pydantic import BaseModel

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend


class ComputeBackend:
    """Base class for ``Authzee`` compute backend.

    Base classes must at least implement these async methods:

        - ``initialize`` - Initialize the compute backend.
        - ``shutdown`` - Preemptively cleanup compute backend resources.
        - ``setup`` - One time setup for compute backend.
        - ``teardown`` - Remove resources created from ``setup()``.
        - ``authorize`` - Figure out if the given given identities are authorized to perform the given action on the given resource.
        - ``authorize_many`` - Figure out if the given given identities are authorized to perform the given action on the given resources.
        - ``get_matching_grants_page`` - Get a page of matching grants. 
    

    No error checking should be needed for validation of resources, resource_types etc. That should all be handled by ``Authzee``.

    Parameters
    ----------
    backend_locality : BackendLocality
        The backend locality this instance of the compute backend supports.
        See ``authzee.backend_locality.BackendLocality`` for more info on what the localites mean.
        This parameter should not be exposed on the child class.
    parallel_pagination : bool
        Flag for if this compute backend supports parallel pagination if the storage backend does. 
        If ``True``, the compute backend must support getting pages in parallel from the storage backend, 
        and effectively using that functionality in the ``authorize``, ``authorize_many``, and ``get_matching_grants_page`` methods.
        This parameter should not be exposed as a parameter on the child class.
    """


    def __init__(
        self,
        backend_locality: BackendLocality,
        parallel_pagination: bool
    ):
        self.backend_locality = backend_locality
        self.parallel_pagination = parallel_pagination


    async def initialize(
        self, 
        identity_types: List[Type[BaseModel]],
        jmespath_options: Union[jmespath.Options, None],
        resource_authzs: List[ResourceAuthz],
        storage_backend: StorageBackend,
    ) -> None:
        """Initialize the compute backend.

        Should only be called by the ``Authzee`` app.

        Parameters
        ----------
        identity_types : List[Type[BaseModel]]
            Identity types registered with the ``Authzee`` app.
        jmespath_options : Union[jmespath.Options, None]
            Custom ``jmespath.Options`` registered with the ``Authzee`` app.
            **This object should not be considered thread safe**. 
            Threads should get their own copy of this object.
            This is because custom versions of JMESPath functions are not restricted.
        resource_authzs : List[ResourceAuthz]
            ``ResourceAuthz`` s registered with the ``Authzee`` app.
        storage_backend : StorageBackend
            Storage backend registered with the ``Authzee`` app.
        """
        self._identity_types = identity_types
        self._jmespath_options = jmespath_options
        self._resource_authzs = resource_authzs
        self._storage_backend = storage_backend


    async def shutdown(self) -> None:
        """Early clean up of compute backend resources.
        """
        pass 


    async def setup(self) -> None:
        """One time setup for compute backend resources.
        """
        pass

    
    async def teardown(self) -> None:
        """Teardown and delete the results of ``setup()`` .
        """
        pass


    async def authorize(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None,
    ) -> bool:
        """Authorize a given resource and action, with the JMESPath data against stored grants.

        First ``GrantEffect.DENY`` grants should be checked.
        If any match, then it is denied.

        Then ``GrantEffect.ALLOW`` grants are checked.
        If any match, it is allowed. If there are no matches, it is denied.

        Parameters
        ----------
        resource_type : BaseModel
            The resource type to compare grants to.
        resource_action : ResourceAction
            The resource action to compare grants to.
        jmespath_data : Dict[str, Any]
            JMESPath data that the grants will be computed with.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        bool
            ``True`` if allowed, ``False`` if denied.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
    

    async def authorize_many(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data_entries: List[Dict[str, Any]],
        page_size: Optional[int] = None,
    ) -> List[bool]:
        """Authorize a given resource and action, with the JMESPath data against stored grants.

        First ``GrantEffect.DENY`` grants should be checked.
        If any match, then it is denied.

        Then ``GrantEffect.ALLOW`` grants are checked.
        If any match, it is allowed. If there are no matches, it is denied.

        Parameters
        ----------
        resource_type : BaseModel
            The resource type to compare grants to.
        resource_action : ResourceAction
            The resource action to compare grants to.
        jmespath_data_entries : List[Dict[str, Any]]
            List of JMESPath data that the grants will be computed with.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        List[bool]
            List of bools directory corresponding to ``jmespath_data_entries``.  
            ``True`` if authorized, ``False`` if denied.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()


    async def get_matching_grants_page(
        self, 
        effect: GrantEffect,
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> GrantsPage:
        """Retrieve a page of matching grants. 

        If ``GrantsPage.next_page_ref`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``page_ref=GrantsPage.next_page_ref`` .

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        resource_type : BaseModel
            The resource type to compare grants to.
        resource_action : ResourceAction
            The resource action to compare grants to. 
        jmespath_data : Dict[str, Any]
            JMESPath data that the grants will be computed with.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            This is not directly related to the returned number of grants, and can vary by compute backend.
            The default is set on the storage backend.
        page_ref : Optional[str], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the first page.

        Returns
        -------
        GrantsPage
            The page of matching grants.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            Sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
