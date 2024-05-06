"""
"""

import asyncio
from typing import Iterator, List, Optional, Type

import jmespath.exceptions
from pydantic import BaseModel

from authzee.authzee import Authzee
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_authz import ResourceAuthz
from authzee.resource_action import ResourceAction



class AuthzeeSync:

    def __init__(self, authzee_app: Authzee, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._authzee_app = authzee_app
        self._loop = loop
        self._async_run = asyncio.run
        if loop is not None:
            self._async_run = loop.run_until_complete
    

    def initialize(self) -> None:
        """Initialize the ``Authzee`` app.

        Raises
        ------
        authzee.exceptions.InitializationError
            An error occurred while initializing the app.
        
        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.initialize())

    
    def shutdown(self) -> None:
        """Early clean up of resources for authzee.

        If for some reason you don't want the authzee app to last the life of the program,
        you can clean up the heavier resources with this function. 

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.shutdown())
    

    def setup(self) -> None:
        """One time setup for authzee app with the current configuration. 

        This method only has to be run once.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.setup())
    

    def teardown(self) -> None:
        """Tear down resources create for one time setup by ``setup()``.

        This may delete all storage for grants etc. 

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.teardown())



    def register_identity_type(self, identity_type: Type[BaseModel]) -> None:
        """Register an Identity model type.

        Parameters
        ----------
        identity_type : Type[BaseModel]
            Identity model type to register.

        Raises
        ------
        authzee.exceptions.IdentityRegistrationError
            Error when trying to register the Identity model type.
        
        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.register_identity_type(identity_type=identity_type))
    

    def register_resource_authz(self, resource_authz: ResourceAuthz) -> None:
        """Register a ``ResourceAuthz`` type.

        Parameters
        ----------
        resource_authz_type : Type[ResourceAuthz]
            ``ResourceAuthz`` type to register.

        Raises
        ------
        authzee.exceptions.ResourceAuthzRegistrationError
            Error when registering a ``ResourceAuthz``.
        
        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        self._async_run(self._authzee_app.register_resource_authz(resource_authz=resource_authz))
    

    async def authorize(
        self,
        resource: BaseModel,
        action: ResourceAction,
        parents: List[BaseModel], 
        children: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> bool:
        """Authorize an entity with the given ``identities`` to perform the
        ``action`` on the ``resource`` that has ``parents``
        and ``children``.

        Parameters
        ----------
        resource : BaseModel
            The resource model to authorize against.
        action : ResourceAction
            The resource action to authorize against.
        parents : List[BaseModel]
            The resource's parent resource models to authorize against.
        children : List[BaseModel]
            The resource's child resource models to authorize against. 
        identities : List[BaseModel]
            The entities identities to authorize.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        bool
            ``True`` if authorized, ``False`` if denied.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(
            self._authzee_app.authorize(
                resource=resource,
                action=action,
                parents=parents,
                children=children,
                identities=identities,
                page_size=page_size
            )
        )


    async def authorize_many(
        self,
        resources: List[BaseModel],
        action: ResourceAction,
        parents: List[BaseModel], 
        children: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> List[bool]:
        """Authorize an entity with the given ``identities`` to perform the
        ``action`` on the ``resource`` that has ``parents``
        and ``children``.

        Parameters
        ----------
        resources : List[BaseModel]
            The resource models to authorize against.
        action : ResourceAction
            The resource action to authorize against.
        parents : List[BaseModel]
            The resource's parent resource models to authorize against.
        children : List[BaseModel]
            The resource's child resource models to authorize against. 
        identities : List[BaseModel]
            The entities identities to authorize.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        List[bool]
            List of bools directory corresponding to ``resources``.  ``True`` if authorized, ``False`` if denied.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(
            self._authzee_app.authorize_many(
                resources=resources,
                action=action,
                parents=parents,
                children=children,
                identities=identities,
                page_size=page_size
            )
        )


    def list_grants(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None
    ) -> Iterator[Grant]:
        """List Grants.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grants.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The page size recommendation for the storage backend.
            The default is set on the storage backend. 

        Returns
        -------
        Iterator[Grant]
            Generator for grants that automatically handles pagination.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        
        Examples
        --------
        .. code-block:: python

            for grant in authzee_app.list_grants():
                print(grant.name)
        """
        a_iter = self._authzee_app.list_grants(
            effect=effect,
            resource_type=resource_type,
            action=action,
            page_size=page_size
        )
        try:
            while True:
                yield self._async_run(a_iter.__anext__())
        except StopAsyncIteration:
            pass


    def get_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> GrantsPage:
        """Retrieve a page of grants matching the filters.

        If ``GrantsPage.next_page_ref`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``page_ref=GrantsPage.next_page_ref`` .

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The suggested page size to return. 
            There is no guarantee of how much data will be returned if any.
            The default is set on the storage backend. 
        page_ref : Optional[str], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the first page.

        Returns
        -------
        GrantsPage
            The page of grants.
        
        Raises
        ------
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(
            self._authzee_app.get_grants_page(
                effect=effect,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=page_ref
            )
        )


    def list_matching_grants(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        action: ResourceAction,
        parents: List[BaseModel], 
        children: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> Iterator[Grant]:
        """List matching grants.

        Parameters
        ----------
        effect : GrantEffect
            Grant effect.
        resource : BaseModel
            Resource model.
        action : ResourceAction
            Resource action.
        parents : List[BaseModel]
            Parent resource models.
        children : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        Iterator[Grant]
            Generator for matching grants that automatically handles pagination.
        
        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        a_iter = self._authzee_app.list_matching_grants(
            effect=effect,
            resource=resource,
            action=action,
            parents=parents,
            children=children,
            identities=identities,
            page_size=page_size
        )
        try:
            while True:
                yield self._async_run(a_iter.__anext__())
        except StopAsyncIteration:
            pass


    def get_matching_grants_page(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        action: ResourceAction,
        parents: List[BaseModel], 
        children: List[BaseModel],
        identities: List[BaseModel],
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
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
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
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(
            self._authzee_app.get_matching_grants_page(
                effect=effect,
                resource=resource,
                action=action,
                parents=parents,
                children=children,
                identities=identities,
                page_size=page_size,
                page_ref=page_ref
            )
        )
    

    async def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        """Add a grant.

        Parameters
        ----------
        effect : GrantEffect
            Effect of the grant to add.
        grant : Grant
            Grant to add.

        Returns
        -------
        Grant
            The stored grant.

        Raises
        ------
        authzee.exceptions.GrantUUIDError
            Grants that are being added should not have a UUID.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(self._authzee_app.add_grant(effect=effect, grant=grant))

    
    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            Effect of the grant to delete.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        return self._async_run(self._authzee_app.delete_grant(effect=effect, uuid=uuid))
