
import copy
import json
from typing import Any, AsyncIterable, Dict, Iterable, List, Optional, Set, Type, Union

import jmespath
import jmespath.exceptions
from pydantic import BaseModel

from authzee.compute.compute_backend import ComputeBackend
from authzee.jmespath_custom_functions import CustomFunctions
from authzee import exceptions
from authzee.compute import general as gc
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grant_iter import GrantIter
from authzee.grants_page import GrantsPage
from authzee.resource_authz import ResourceAuthz
from authzee.resource_action import ResourceAction
from authzee.storage.storage_backend import StorageBackend


class Authzee:
    """Authzee app for managing grants and verifying authorization.

    Example:

    .. code-block:: python

        from authzee import Authzee


    Parameters
    ----------
    compute_backend : ComputeBackend
        The compute backend instance.
    storage_backend : StorageBackend
        The storage backend instance.
    identity_types : Optional[Set[Type[BaseModel]]], optional
        List of identity model types to register with ``Authzee``.
        By default, none are registered.
    resource_authz_types : Optional[Set[Type[ResourceAuthz]]], optional
        List of ``ResourceAuthz`` types to register with ``Authzee``.
        By default, none are registered.
    jmespath_options : Optional[jmespath.Options], optional
        Custom JMESPath options to use for grant computations.
        See `python jmespath Options <https://github.com/jmespath/jmespath.py#options>`_ for more information.
        By default, custom functions are used from ``authzee.jmespath_custom_functions.CustomFunctions``.
    """


    def __init__(
        self, 
        compute_backend: ComputeBackend,
        storage_backend: StorageBackend,
        identity_types: Optional[Set[Type[BaseModel]]] = None,
        resource_authz_types: Optional[Set[Type[ResourceAuthz]]] = None,
        jmespath_options: Optional[jmespath.Options] = None
    ):
        self._compute_backend = compute_backend
        self._storage_backend = storage_backend
        self._both_async_enabled = (
            self._compute_backend.async_enabled 
            and self._storage_backend.async_enabled
        )
        self._identity_types: Set[Type[BaseModel]] = set()
        self._identity_type_names: Set[str] = set()
        self._resource_types: Set[Type[BaseModel]] = set()
        self._resource_type_names: Set[str] = set()
        self._authz_types: Set[Type[ResourceAuthz]] = set()
        self._authz_type_names: Set[str] = set()
        self._authzs: List[ResourceAuthz] = []
        self._resource_action_types: Set[Type[ResourceAction]] = set()
        self._resource_to_authz_lookup: Dict[Type[BaseModel], ResourceAuthz] = {}
        self._authz_name_to_authz_type_lookup: Dict[str, Type[ResourceAuthz]] = {}
        self._authz_type_to_authz_lookup: Dict[Type[ResourceAuthz], ResourceAuthz] = {}

        if identity_types is not None:
            for identity_type in identity_types:
                self.register_identity_type(identity_type=identity_type)
                
        if resource_authz_types is not None:
            for authz_type in resource_authz_types:
                self.register_resource_authz(authz_type)
        
        if jmespath_options is not None:
            self._jmespath_options = jmespath_options
        else:
            self._jmespath_options = jmespath.Options(
                custom_functions=CustomFunctions()
            )


    def initialize(self) -> None:
        """Initialize the ``Authzee`` app.

        Raises
        ------
        exceptions.InitializationError
            An error occurred while initializing the app.
        """
        for authz in self._authzs:
            for p_authz_name in authz.parent_authz_names:
                if p_authz_name not in self._authz_type_names:
                    raise exceptions.InitializationError(
                        "The parent resource '{}' in ResourceAuthz '{}' is not registered.".format(
                            p_authz_name,
                            authz.__class__.__name__
                        )
                    )

                p_authz_type = self._authz_name_to_authz_type_lookup[p_authz_name]
                authz._parent_authz_types.add(p_authz_type)
                authz._parent_resource_types.add(
                    self._authz_type_to_authz_lookup[p_authz_type].resource_type
                )

            for c_authz_name in authz.child_authz_names:
                if c_authz_name not in self._authz_type_names:
                    raise exceptions.InitializationError(
                        "The child resource '{}' in ResourceAuthz '{}' is not registered.".format(
                            c_authz_name,
                            authz.__class__.__name__
                        )
                    )

                c_authz_type = self._authz_name_to_authz_type_lookup[c_authz_name]
                authz._child_authz_types.add(c_authz_type)
                authz._child_resource_types.add(
                    self._authz_type_to_authz_lookup[c_authz_type].resource_type
                )

        # check that storage and compute are process compatible (and async?)

        self._storage_backend.initialize(
            identity_types=self._identity_types,
            resource_authzs=self._authzs
        )
        self._compute_backend.initialize(
            identity_types=self._identity_types,
            jmespath_options=self._jmespath_options,
            resource_authzs=self._authzs,
            storage_backend=self._storage_backend
        )
    
    def shutdown(self) -> None:
        """Early clean up of resources for authzee.

        If for some reason you don't want the authzee app to last the life of the program,
        you can clean up the heavier resources with this function. 
        """
        self._storage_backend.shutdown()
        self._compute_backend.shutdown()
    

    def setup(self) -> None:
        """One time setup for authzee app with the current configuration. 

        This method only has to be run once.
        """
        self._storage_backend.setup()
        self._compute_backend.setup()
    

    def teardown(self) -> None:
        """Tear down resources create for one time setup by ``setup()``.

        This may delete all storage for grants etc. 
        """
        self._storage_backend.teardown()
        self._compute_backend.teardown()



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
        """
        if identity_type in self._identity_types:
            raise exceptions.IdentityRegistrationError(
                "Identity type '{}' is already registered with Authzee".format(identity_type)
            )
        
        if identity_type.__name__ in self._identity_type_names:
            raise exceptions.IdentityRegistrationError(
                "Identity with name '{}' is already registered with Authzee".format(identity_type.__name__)
            )
        
        self._identity_types.add(identity_type)
        self._identity_type_names.add(identity_type.__name__)
    

    def register_resource_authz(self, resource_authz_type: Type[ResourceAuthz]) -> None:
        """Register a ``ResourceAuthz`` type.

        Parameters
        ----------
        resource_authz_type : Type[ResourceAuthz]
            ``ResourceAuthz`` type to register.

        Raises
        ------
        authzee.exceptions.ResourceAuthzRegistrationError
            Error when registering a ``ResourceAuthz``.
        """
        resource_authz_inst = resource_authz_type()
        if resource_authz_type in self._authz_types:
            raise exceptions.ResourceAuthzRegistrationError(
                "ResourceAuthz type '{}' is already registered with Authzee".format(resource_authz_type)
            )

        if resource_authz_type.__name__ in self._authz_type_names:
            raise exceptions.ResourceAuthzRegistrationError(
                "ResourceAuthz with name '{}' is already registered with Authzee".format(resource_authz_type.__name__)
            )

        if resource_authz_inst.resource_action_type in self._resource_action_types:
            # check the other Authz it is registered with
            registered_resource_authz = None
            for raz_inst in self._authzs:
                if raz_inst.resource_action_type == resource_authz_inst.resource_action_type:
                    registered_resource_authz = raz_inst
                    break
            
            raise exceptions.ResourceAuthzRegistrationError(
                "ResourceAction '{}' is already registered with the '{}' ResourceAuthz".format(
                    resource_authz_inst.resource_actions.__name__,
                    registered_resource_authz.__name__
                )
            )

        if resource_authz_inst.resource_type in self._resource_types:
            raise exceptions.ResourceAuthzRegistrationError(
                "Resource Model '{}' is already registered with Authzee".format(
                    resource_authz_inst.resource
                )
            )

        if resource_authz_inst.resource_type.__name__ in self._resource_type_names:
            raise exceptions.ResourceAuthzRegistrationError(
                "Resource Model with name '{}' is already registered with Authzee".format(
                    resource_authz_inst.resource
                )
            )
        
        self._resource_types.add(resource_authz_inst.resource_type)
        self._resource_type_names.add(resource_authz_inst.resource_type.__name__)
        self._resource_action_types.add(resource_authz_inst.resource_action_type)
        self._authz_types.add(resource_authz_type)
        self._authz_type_names.add(resource_authz_type.__name__)
        self._authzs.append(resource_authz_inst)
        self._resource_to_authz_lookup[resource_authz_inst.resource_type] = resource_authz_inst
        self._authz_name_to_authz_type_lookup[resource_authz_type.__name__] = resource_authz_type
        self._authz_type_to_authz_lookup[resource_authz_type] = resource_authz_inst

    
    def authorize(
        self,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> bool:
        """Authorize an entity with the given ``identities`` to perform the
        ``resource_action`` on the ``resource`` that has ``parent_resources``
        and ``child_resources``.

        Parameters
        ----------
        resource : BaseModel
            The resource model to authorize against.
        resource_action : ResourceAction
            The resource action to authorize against.
        parent_resources : List[BaseModel]
            The resource's parent resource models to authorize against.
        child_resources : List[BaseModel]
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
        """
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return self._compute_backend.authorize(
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size
        )
    

    async def authorize_async(
        self,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> bool:
        """Authorize an entity with the given ``identities`` to perform the
        ``resource_action`` on the ``resource`` that has ``parent_resources``
        and ``child_resources``.

        Parameters
        ----------
        resource : BaseModel
            The resource model to authorize against.
        resource_action : ResourceAction
            The resource action to authorize against.
        parent_resources : List[BaseModel]
            The resource's parent resource models to authorize against.
        child_resources : List[BaseModel]
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
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'authorize' because the compute backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )

        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return await self._compute_backend.authorize_async(
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size
        )
    


    def authorize_many(
        self,
        resources: List[BaseModel],
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> List[bool]:
        """Authorize an entity with the given ``identities`` to perform the
        ``resource_action`` on the ``resource`` s that have ``parent_resources``
        and ``child_resources``.

        Parameters
        ----------
        resources : List[BaseModel]
            The resource models to authorize against.
        resource_action : ResourceAction
            The resource action to authorize against.
        parent_resources : List[BaseModel]
            The resource's parent resource models to authorize against.
        child_resources : List[BaseModel]
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
        """
        self._verify_auth_many_args(
            resources=resources,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_many_jmespath_data(
            resources=resources,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return self._compute_backend.authorize_many(
            resource_type=type(resources[0]),
            resource_action=resource_action,
            jmespath_data_entries=jmespath_data,
            page_size=page_size
        )


    async def authorize_many_async(
        self,
        resources: List[BaseModel],
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> List[bool]:
        """Authorize an entity with the given ``identities`` to perform the
        ``resource_action`` on the ``resource`` that has ``parent_resources``
        and ``child_resources``.

        Parameters
        ----------
        resources : List[BaseModel]
            The resource models to authorize against.
        resource_action : ResourceAction
            The resource action to authorize against.
        parent_resources : List[BaseModel]
            The resource's parent resource models to authorize against.
        child_resources : List[BaseModel]
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
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'authorize_many' because the compute backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )

        self._verify_auth_many_args(
            resources=resources,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_many_jmespath_data(
            resources=resources,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return await self._compute_backend.authorize_many_async(
            resource_type=type(resources[0]),
            resource_action=resource_action,
            jmespath_data_entries=jmespath_data,
            page_size=page_size
        )
  

    def list_grants(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None
    ) -> Iterable[Grant]:
        """List Grants.

        Example:

        .. code-block:: python

            for grant in authzee_app.list_grants():
                print(grant.name)

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grants.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        resource_action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The page size recommendation for the storage backend.
            The default is set on the storage backend. 

        Returns
        -------
        Iterable[Grant]
            An iterable for grants.
        
        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )

        return GrantIter(
            next_page_callable=self._storage_backend.get_grants_page,
            page_size=page_size,
            next_page_reference=None,
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action
        )


    def list_grants_async(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None
    ) -> AsyncIterable[Grant]:
        """List Grants.

        **NOTE** - This is not a coroutine but returns an async iterator.

        Example:

        .. code-block:: python

            async for grant in authzee_app.list_grants_async():
                print(grant.name)

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grants.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        resource_action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The page size recommendation for the storage backend.
            The default is set on the storage backend. 

        Returns
        -------
        AsyncIterable[Grant]
            Async iterable for grants.

        Raises
        ------
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._storage_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'list_grants' because the storage backend '{}' does not support it.".format(
                    self._storage_backend.__class__.__name__
                )
            )
        
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )

        return GrantIter(
            next_page_callable=self._storage_backend.get_grants_page_async,
            page_size=page_size,
            next_page_reference=None,
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action
        )


    def get_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        next_page_reference: Optional[BaseModel] = None
    ) -> GrantsPage:
        """Retrieve a page of grants matching the filters.

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

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
        next_page_reference : Optional[BaseModel], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the 1st page.

        Returns
        -------
        GrantsPage
            The page of grants.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )

        return self._storage_backend.get_grants_page(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_reference
        )


    async def get_grants_page_async(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        next_page_reference: Optional[BaseModel] = None
    ) -> GrantsPage:
        """Retrieve a page of grants matching the filters.

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

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
        next_page_reference : Optional[BaseModel], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the 1st page.

        Returns
        -------
        GrantsPage
            The page of grants.
        
        Raises
        ------
        exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )

        return await self._storage_backend.get_grants_page_async(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_reference
        )


    def list_matching_grants(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> Iterable[Grant]:
        """List matching grants.

        Parameters
        ----------
        effect : GrantEffect
            Grant effect.
        resource : BaseModel
            Resource model.
        resource_action : ResourceAction
            Resource action.
        parent_resources : List[BaseModel]
            Parent resource models.
        child_resources : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.

        Returns
        -------
        Iterable[Grant]
            Iterable for matching Grants.
        
        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return GrantIter(
            next_page_callable=self._compute_backend.get_matching_grants_page,
            page_size=page_size,
            next_page_reference=None,
            effect=effect,
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data
        )


    def list_matching_grants_async(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> AsyncIterable[Grant]:
        """List matching grants.

        **NOTE** - This is not a coroutine but returns an async iterator.

        Parameters
        ----------
        effect : GrantEffect
            Grant effect.
        resource : BaseModel
            Resource model.
        resource_action : ResourceAction
            Resource action.
        parent_resources : List[BaseModel]
            Parent resource models.
        child_resources : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            The default is set on the storage backend.


        Returns
        -------
        AsyncIterable[Grant]
            Async Iterable for matching Grants.
        
        Raises
        ------
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'list_matching_grants' because the compute backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )

        self._verify_grant_effect(effect=effect)
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return GrantIter(
            next_page_callable=self._compute_backend.get_matching_grants_page_async,
            page_size=page_size,
            next_page_reference=None,
            effect=effect,
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data
        )


    def get_matching_grants_page(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None,
        next_page_reference: Optional[BaseModel] = None
    ) -> GrantsPage:
        """Retrieve a page of matching grants. 

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

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
        jmespath_data : Dict[str, Any]
            JMESPath data that the grants will be computed with.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            This is not directly related to the returned number of grants, and can vary by compute backend.
            The default is set on the storage backend.
        next_page_reference : Optional[BaseModel], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the 1st page.

        Returns
        -------
        GrantsPage
            The page of matching grants.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return self._compute_backend.get_matching_grants_page(
            effect=effect,
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size,
            next_page_reference=next_page_reference
        )


    async def get_matching_grants_page_async(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None,
        next_page_reference: Optional[BaseModel] = None
    ) -> GrantsPage:
        """Retrieve a page of matching grants. 

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

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
        jmespath_data : Dict[str, Any]
            JMESPath data that the grants will be computed with.
        page_size : Optional[int], optional
            The page size to use for the storage backend.
            This is not directly related to the returned number of grants, and can vary by compute backend.
            The default is set on the storage backend.
        next_page_reference : Optional[BaseModel], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the 1st page.

        Returns
        -------
        GrantsPage
            The page of matching grants.

        Raises
        ------
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'get_matching_grants_page' because the compute backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )
        
        self._verify_grant_effect(effect=effect)
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return await self._compute_backend.get_matching_grants_page_async(
            effect=effect,
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size,
            next_page_reference=next_page_reference
        )
    

    def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
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
        """
        self._verify_grant_effect(effect=effect)
        self._verify_grant(grant=grant)
        
        return self._storage_backend.add_grant(effect=effect, grant=grant)
    

    async def add_grant_async(self, effect: GrantEffect, grant: Grant) -> Grant:
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
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.GrantUUIDError
            Grants that are being added should not have a UUID.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'add_grant' because the compute backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )

        self._verify_grant_effect(effect=effect)
        self._verify_grant(grant=grant)

        return await self._storage_backend.add_grant_async(effect=effect, grant=grant)


    def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            Effect of the grant to delete.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.GrantDoesNotExistError
            The given grant does not exist.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant_effect(effect=effect)
        self._storage_backend.delete_grant(effect=effect, uuid=uuid)

    
    async def delete_grant_async(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            Effect of the grant to delete.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.AsyncNotAvailableError
            Async is not available for the storage backend.
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if self._compute_backend.async_enabled != True:
            raise exceptions.AsyncNotAvailableError(
                "Async is not available for 'delete_grant' because the storage backend '{}' does not support it.".format(
                    self._compute_backend.__class__.__name__
                )
            )
        
        self._verify_grant_effect(effect=effect)
        await self._storage_backend.delete_grant_async(effect=effect, uuid=uuid)


    def grant_matches( 
        self,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel],
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        grant: Grant
    ) -> bool:
        """Verifies a grant, the resources, and identities. Then computes if they match.

        Parameters
        ----------
        resource : BaseModel
            Resource model.
        resource_action : ResourceAction
            Resource Action.
        parent_resources : List[BaseModel]
            Parent resource models.
        child_resources : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.
        grant : Grant
            Grant to match against.

        Returns
        -------
        bool
            ``True`` if the grant matches, or else ``False``.
        
        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        self._verify_grant(grant=grant)
        self._verify_auth_args(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )
        if ( 
            type(resource) != grant.resource_type
            or resource_action not in grant.resource_actions
        ):
            return False

        jmespath_data = self._generate_jmespath_data(
            resource=resource,
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )

        return gc.grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=self._jmespath_options
        )

    
    def _generate_jmespath_data(
        self,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel],
        child_resources: List[BaseModel],
        identities: List[BaseModel],
    ) -> Dict[str, Any]:
        """Generate JMESPath data.

        Parameters
        ----------
        resource : BaseModel
            Resource model.
        resource_action : ResourceAction
            Resource Action.
        parent_resources : List[BaseModel]
            Parent resource models.
        child_resources : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.

        Returns
        -------
        Dict[str, Any]
            The JMESPath data. 
        """
        resource_type = type(resource)
        parent_resources_by_type = {parent_type.__name__: [] for parent_type in self._resource_to_authz_lookup[resource_type]._parent_resource_types}
        for parent_resource in parent_resources:
            parent_type = type(parent_resource)
            parent_resources_by_type[parent_type.__name__].append(json.loads(parent_resource.json()))
        
        child_resources_by_type = {child_type.__name__: [] for child_type in self._resource_to_authz_lookup[resource_type]._child_resource_types}
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type.__name__ not in child_resources_by_type:
                child_resources_by_type[child_type.__name__] = []
            
            child_resources_by_type[child_type.__name__].append(json.loads(child_resource.json()))

        identities_by_type = {identity_name: [] for identity_name in self._identity_type_names}
        for identity in identities:
            identity_type = type(identity)
            identities_by_type[identity_type.__name__].append(json.loads(identity.json()))
        
        jmespath_data = {
            "identities": identities_by_type,
            "resource": json.loads(resource.json()),
            "resource_type": type(resource).__name__,
            "resource_action": str(resource_action),
            "parent_resources": parent_resources_by_type,
            "child_resources": child_resources_by_type
        }

        return jmespath_data
    

    def _generate_many_jmespath_data(
        self,
        resources: List[BaseModel],
        resource_action: ResourceAction,
        parent_resources: List[BaseModel],
        child_resources: List[BaseModel],
        identities: List[BaseModel],
    ) -> List[Dict[str, Any]]:
        """Generate JMESPath data.

        Parameters
        ----------
        resources : List[BaseModel]
            Resource models.
        resource_action : ResourceAction
            Resource Action.
        parent_resources : List[BaseModel]
            Parent resource models.
        child_resources : List[BaseModel]
            Child resource models.
        identities : List[BaseModel]
            Identity models.

        Returns
        -------
        List[Dict[str, Any]]
            List of JMESPath data for the request. 
        """
        resource_type = type(resources[0])
        parent_resources_by_type = {parent_type.__name__: [] for parent_type in self._resource_to_authz_lookup[resource_type]._parent_resource_types}
        for parent_resource in parent_resources:
            parent_type = type(parent_resource)
            parent_resources_by_type[parent_type.__name__].append(json.loads(parent_resource.json()))
        
        child_resources_by_type = {child_type.__name__: [] for child_type in self._resource_to_authz_lookup[resource_type]._child_resource_types}
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type.__name__ not in child_resources_by_type:
                child_resources_by_type[child_type.__name__] = []
            
            child_resources_by_type[child_type.__name__].append(json.loads(child_resource.json()))

        identities_by_type = {identity_name: [] for identity_name in self._identity_type_names}
        for identity in identities:
            identity_type = type(identity)
            identities_by_type[identity_type.__name__].append(json.loads(identity.json()))
        
        jmespath_data = {
            "identities": identities_by_type,
            "resource_type": type(resources[0]).__name__,
            "resource_action": str(resource_action),
            "parent_resources": parent_resources_by_type,
            "child_resources": child_resources_by_type
        }
        data_entries = []
        for resource in resources:
            new_jmespath_data = copy.deepcopy(jmespath_data)
            new_jmespath_data['resource'] = json.loads(resource.json())
            data_entries.append(new_jmespath_data)

        return data_entries


    def _verify_auth_args(
        self,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel]
    ) -> None:
        """Verify the authorization args.

        Parameters
        ----------
        resource : BaseModel
            Resource model to verify.
        resource_action : ResourceAction
            Resource Action to verify.
        parent_resources : List[BaseModel]
            Parent resource models to verify.
        child_resources : List[BaseModel]
            Child resource models to verify.
        identities : List[BaseModel]
            Identity models to verify.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        resource_type = type(resource)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )
        resource_authz_inst = self._resource_to_authz_lookup[resource_type]
        for parent_resource in parent_resources:
            parent_type = type(parent_resource)
            if parent_type not in self._resource_types:
                raise exceptions.InputVerificationError(
                    "Parent resource type '{}' is not a registered resource.".format(
                        parent_type.__name__
                    )
                )
            
            if type(self._resource_to_authz_lookup[parent_type]) not in resource_authz_inst._parent_authz_types:
                raise exceptions.InputVerificationError(
                    "Resource type '{}' is not a registered parent resource type of '{}'".format(
                        parent_type.__name__,
                        resource_type.__name__
                    )
                )
        
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type not in self._resource_types:
                raise exceptions.InputVerificationError(
                    "Parent resource type '{}' is not a registered resource.".format(
                        child_type.__name__
                    )
                )
            
            if type(self._resource_to_authz_lookup[child_type]) not in resource_authz_inst._child_authz_types:
                raise exceptions.InputVerificationError(
                    "Resource type '{}' is not a registered child resource type of '{}'".format(
                        child_type.__name__,
                        resource_type.__name__
                    )
                )

        for identity in identities:
            identity_type = type(identity)
            if identity_type not in self._identity_types:
                raise exceptions.InputVerificationError(
                    "Identity type '{}' is not registered".format(
                        identity_type.__name__
                    )
                )


    def _verify_auth_many_args(
        self,
        resources: List[BaseModel],
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel]
    ) -> None:
        """Verify the authorization args for many resource calls.

        Parameters
        ----------
        resources : List[BaseModel]
            Resource models to verify.
        resource_action : ResourceAction
            Resource Action to verify.
        parent_resources : List[BaseModel]
            Parent resource models to verify.
        child_resources : List[BaseModel]
            Child resource models to verify.
        identities : List[BaseModel]
            Identity models to verify.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        resource_type = type(resources[0])
        for resource in resources:
            if isinstance(resource, resource_type) is False:
                raise exceptions.InputVerificationError(
                    "All resources must be of the same type: {} is not of type {}".format(
                        resource, resource_type
                    )
                )
        
        self._verify_auth_args(
            resource=resources[0],
            resource_action=resource_action,
            parent_resources=parent_resources,
            child_resources=child_resources,
            identities=identities
        )


    def _verify_grant(self, grant: Grant) -> None:
        """Verify a grant with the ``Authzee`` configuration.

        Parameters
        ----------
        grant : Grant
            Grant to verify.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        resource_type = grant.resource_type
        if resource_type not in self._resource_types:
            raise exceptions.InputVerificationError(
                "Resource type '{}' is not a part of any registered ResourceAuthzs.".format(
                    resource_type.__name__
                )
            )
        
        if len(grant.resource_actions) < 1:
            raise exceptions.InputVerificationError("A set of at least one resource action must be given in a grant.")
        
        resource_authz_inst = self._resource_to_authz_lookup[resource_type]
        for resource_action in grant.resource_actions:
            resource_action_type = type(resource_action)
            if resource_action_type not in self._resource_action_types:
                raise exceptions.InputVerificationError(
                    "ResourceAction type '{}' is not registered.".format(
                        resource_action_type.__name__
                    )
                )

            if resource_action_type != resource_authz_inst.resource_action_type:
                raise exceptions.InputVerificationError(
                    "The '{}' resource action does not apply to the '{}' resource type.".format(
                        resource_action,
                        resource_type.__name__
                    )
                )


    def _verify_resource_type_and_action_filter(
        self, 
        resource_type: Union[Type[BaseModel], None], 
        resource_action: Union[ResourceAction, None]
    ) -> None:
        """Verify resource type and resource action filters

        Parameters
        ----------
        resource_type : Union[Type[BaseModel], None]
            Resource type model to verify, or None
        resource_action : Union[ResourceAction, None]
            Resource Action type model to verify, or None

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        """
        if resource_type is not None:
            if resource_type not in self._resource_types:
                raise exceptions.InputVerificationError(
                    "Resource type '{}' is not a part of any registered ResourceAuthzs.".format(
                        resource_type.__name__
                    )
                )

        if resource_action is not None:
            resource_action_type = type(resource_action)
            if resource_action_type not in self._resource_action_types:
                raise exceptions.InputVerificationError(
                    "ResourceAction type '{}' is not registered.".format(
                        resource_action_type.__name__
                    )
                )

            resource_authz_inst = self._resource_to_authz_lookup[resource_type]
            if resource_action_type != resource_authz_inst.resource_action_type:
                raise exceptions.InputVerificationError(
                    "The '{}' resource action type does not apply to the '{}' resource type.".format(
                        resource_action_type,
                        resource_type.__name__
                    )
                )



    def _verify_grant_effect(self, effect: GrantEffect) -> None:
        """Verify Grant effect type.

        Parameters
        ----------
        effect : GrantEffect
            effect to verify.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            Error with grant effect type.
        """
        if type(effect) != GrantEffect:
            raise exceptions.InputVerificationError("Must use a GrantEffect, but '{}' was given.".format(effect)) 
    