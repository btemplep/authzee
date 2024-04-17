
import copy
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Type, Union

import jmespath
import jmespath.exceptions
from pydantic import BaseModel

from authzee.backend_locality import compute_compatibility
from authzee.compute.compute_backend import ComputeBackend
from authzee import exceptions
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.page_refs_page import PageRefsPage
from authzee.resource_authz import ResourceAuthz
from authzee.resource_action import ResourceAction
from authzee.storage.storage_backend import StorageBackend


class Authzee:
    """Authzee app for managing grants and verifying authorization.

    Parameters
    ----------
    compute_backend : ComputeBackend
        The compute backend instance.
    storage_backend : StorageBackend
        The storage backend instance.
    identity_types : Optional[Set[Type[BaseModel]]], optional
        List of identity model types to register with ``Authzee``.
        By default, none are registered.
    resource_authzs : Optional[List[ResourceAuthz]], optional
        List of ``ResourceAuthz`` types to register with ``Authzee``.
        By default, none are registered.
    jmespath_options : Optional[jmespath.Options], optional
        Custom JMESPath options to use for grant computations.
        See `python jmespath Options <https://github.com/jmespath/jmespath.py#options>`_ for more information.
        By default, no custom functions or options are used.
    check_backend_localities : bool, default: True
        Check if compute and storage backend localities are compatible. 
        This is best guess but if you are sure it should work then you can turn this off. 
    
    Examples
    --------
    .. code-block:: python

        from authzee import Authzee

    """

    def __init__(
        self, 
        compute_backend: ComputeBackend,
        storage_backend: StorageBackend,
        identity_types: Optional[Set[Type[BaseModel]]] = None,
        resource_authzs: Optional[List[ResourceAuthz]] = None,
        jmespath_options: Optional[jmespath.Options] = None,
        check_backend_localities: bool = True
    ):
        self._compute_backend = compute_backend
        self._storage_backend = storage_backend
        self._identity_types: Set[Type[BaseModel]] = set()
        self._identity_type_names: Set[str] = set()
        self._resource_types: Set[Type[BaseModel]] = set()
        self._resource_type_names: Set[str] = set()
        self._authzs: List[ResourceAuthz] = []
        self._resource_action_types: Set[Type[ResourceAction]] = set()
        self._resource_to_authz_lookup: Dict[Type[BaseModel], ResourceAuthz] = {}
        self._jmespath_options = jmespath_options
        self._check_backend_localities = check_backend_localities

        if identity_types is not None:
            for identity_type in identity_types:
                self.register_identity_type(identity_type=identity_type)
                
        if resource_authzs is not None:
            for authz in resource_authzs:
                self.register_resource_authz(authz)


    async def initialize(self) -> None:
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
        for authz in self._authzs:
            for p_resource in authz.parent_resource_types:
                if p_resource not in self._resource_types:
                    raise exceptions.InitializationError(
                        f"The parent resource '{p_resource}' in ResourceAuthz '{authz.__class__.__name__}' is not registered."
                    )

            for c_resource in authz.child_resource_types:
                if c_resource not in self._resource_types:
                    raise exceptions.InitializationError(
                        f"The child resource '{c_resource}' in ResourceAuthz '{authz.__class__.__name__}' is not registered."
                    )

        await self._storage_backend.initialize(
            identity_types=self._identity_types,
            resource_authzs=self._authzs
        )
        await self._compute_backend.initialize(
            identity_types=self._identity_types,
            jmespath_options=self._jmespath_options,
            resource_authzs=self._authzs,
            storage_backend=self._storage_backend
        )

        if (
            self._check_backend_localities is True
            and self._storage_backend.backend_locality not in compute_compatibility[self._compute_backend.backend_locality]
        ):
            raise exceptions.BackendLocalityIncompatibility()

    
    async def shutdown(self) -> None:
        """Clean up of resources for the authzee app.

        Should be called on program shutdown to clean up async connections etc.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        await self._storage_backend.shutdown()
        await self._compute_backend.shutdown()
    

    async def setup(self) -> None:
        """One time setup for authzee app with the current configuration. 

        This method only has to be run once.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        await self._storage_backend.setup()
        await self._compute_backend.setup()
    

    async def teardown(self) -> None:
        """Tear down resources create for one time setup by ``setup()``.

        This may delete all storage for grants etc. 

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

        """
        await self._storage_backend.teardown()
        await self._compute_backend.teardown()



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
        if identity_type in self._identity_types:
            raise exceptions.IdentityRegistrationError(
                f"Identity type '{identity_type}' is already registered with Authzee"
            )
        
        if identity_type.__name__ in self._identity_type_names:
            raise exceptions.IdentityRegistrationError(
                f"Identity with name '{identity_type.__name__}' is already registered with Authzee"
            )
        
        self._identity_types.add(identity_type)
        self._identity_type_names.add(identity_type.__name__)
    

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
        if resource_authz.resource_action_type in self._resource_action_types:
            # check the other Authz it is registered with
            registered_resource_authz = None
            for raz_inst in self._authzs:
                if raz_inst.resource_action_type == resource_authz.resource_action_type:
                    registered_resource_authz = raz_inst
                    break
            
            raise exceptions.ResourceAuthzRegistrationError(
                (
                    f"ResourceAction '{resource_authz.resource_action_type.__name__}' is already registered "
                    f"with the '{registered_resource_authz.__name__}' ResourceAuthz"
                )
            )

        if resource_authz.resource_type in self._resource_types:
            raise exceptions.ResourceAuthzRegistrationError(
                f"Resource Model '{resource_authz.resource_type}' is already registered with Authzee"
            )

        if resource_authz.resource_type.__name__ in self._resource_type_names:
            raise exceptions.ResourceAuthzRegistrationError(
                f"Resource Model with name '{resource_authz.resource_type}' is already registered with Authzee"
            )
        
        self._resource_types.add(resource_authz.resource_type)
        self._resource_type_names.add(resource_authz.resource_type.__name__)
        self._resource_action_types.add(resource_authz.resource_action_type)
        self._authzs.append(resource_authz)
        self._resource_to_authz_lookup[resource_authz.resource_type] = resource_authz
    

    async def authorize(
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

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

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

        return await self._compute_backend.authorize(
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size
        )


    async def authorize_many(
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
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

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

        return await self._compute_backend.authorize_many(
            resource_type=type(resources[0]),
            resource_action=resource_action,
            jmespath_data_entries=jmespath_data,
            page_size=page_size
        )


    async def list_grants(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None
    ) -> AsyncIterator[Grant]:
        """List Grants.

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
        AsyncIterator[Grant]
            Async generator for grants that automatically handles pagination.

        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.
        
        Examples
        --------
        .. code-block:: python

            async for grant in authzee_app.list_grants():
                print(grant.name)
        """
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )
        did_once = False
        next_page_ref = None
        grants_page = None
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            raw_grants = await self._storage_backend.get_raw_grants_page(
                effect=effect,
                resource_type=resource_type,
                resource_action=resource_action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            grants_page = await self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants)
            next_page_ref = grants_page.next_page_ref
            
            for grant in grants_page.grants:
                yield grant


    async def get_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
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
        resource_action : Optional[ResourceAction], optional
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
        self._verify_grant_effect(effect=effect)
        self._verify_resource_type_and_action_filter(
            resource_type=resource_type,
            resource_action=resource_action
        )
        raw_grants_page = await self._storage_backend.get_raw_grants_page(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            page_ref=page_ref
        )

        return await self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    

    async def get_page_ref_page(self, page_ref: str) -> PageRefsPage:
        """Get a page of page references for parallel pagination. 

        **NOTE** - Not all storage backends or storage backend configurations support parallel pagination.
        You cannot be certain until the ``initialization`` method is called and complete. 
        Then you can check the ``parallel_pagination`` flag on the storage backend to see if it is supported. 

        .. code-block:: python

            storage_backend = MyStorageBackend()
            compute_backend = MyComputeBackend()
            authzee_app = Authzee(compute_backend=compute_backend, storage_backend=storage_backend)

            async def init():
                await authzee_app.initialize()
                if storage_backend.parallel_pagination is True:
                    print("This storage backend supports parallel pagination!")
                else:
                    print("This storage backend doesn't support parallel pagination :(")

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
        authzee.exceptions.MethodNotImplementedError
            Sub-classes should implement this method if this storage backend supports parallel pagination. 
            They must also set the ``parallel_pagination`` flag. 
        """
        return await self._storage_backend.get_page_ref_page(page_ref=page_ref)


    async def list_matching_grants(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
        identities: List[BaseModel],
        page_size: Optional[int] = None
    ) -> AsyncIterator[Grant]:
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
        AsyncIterator[Grant]
            Async generator for matching grants that automatically handles pagination.
        
        Raises
        ------
        authzee.exceptions.InputVerificationError
            The inputs were not verified with the ``Authzee`` configuration.

        Examples
        --------
        .. code-block:: python

            from authzee import Authzee

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
        did_once = False
        next_page_ref = None
        grants_page = None
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            grants_page = await self._compute_backend.get_matching_grants_page(
                effect=effect,
                resource_type=type(resource),
                resource_action=resource_action,
                jmespath_data=jmespath_data,
                page_size=page_size,
                page_ref=next_page_ref
            )
            next_page_ref = grants_page.next_page_ref
            
            for grant in grants_page.grants:
                yield grant


    async def get_matching_grants_page(
        self,
        effect: GrantEffect,
        resource: BaseModel,
        resource_action: ResourceAction,
        parent_resources: List[BaseModel], 
        child_resources: List[BaseModel],
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
        resource_action : Optional[ResourceAction], optional
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

        return await self._compute_backend.get_matching_grants_page(
            effect=effect,
            resource_type=type(resource),
            resource_action=resource_action,
            jmespath_data=jmespath_data,
            page_size=page_size,
            page_ref=page_ref
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
        self._verify_grant_effect(effect=effect)
        self._verify_grant(grant=grant)

        return await self._storage_backend.add_grant(effect=effect, grant=grant)

    
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
        self._verify_grant_effect(effect=effect)
        await self._storage_backend.delete_grant(effect=effect, uuid=uuid)

    
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
        parent_resources_by_type = {parent_type.__name__: [] for parent_type in self._resource_to_authz_lookup[resource_type].parent_resource_types}
        for parent_resource in parent_resources:
            parent_type = type(parent_resource)
            parent_resources_by_type[parent_type.__name__].append(parent_resource.model_dump(mode="json"))
        
        child_resources_by_type = {child_type.__name__: [] for child_type in self._resource_to_authz_lookup[resource_type].child_resource_types}
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type.__name__ not in child_resources_by_type:
                child_resources_by_type[child_type.__name__] = []
            
            child_resources_by_type[child_type.__name__].append(child_resource.model_dump(mode="json"))

        identities_by_type = {identity_name: [] for identity_name in self._identity_type_names}
        for identity in identities:
            identity_type = type(identity)
            identities_by_type[identity_type.__name__].append(identity.model_dump(mode="json"))
        
        jmespath_data = {
            "identities": identities_by_type,
            "resource": resource.model_dump(mode="json"),
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
        parent_resources_by_type = {parent_type.__name__: [] for parent_type in self._resource_to_authz_lookup[resource_type].parent_resource_types}
        for parent_resource in parent_resources:
            parent_type = type(parent_resource)
            parent_resources_by_type[parent_type.__name__].append(parent_resource.model_dump(mode="json"))
        
        child_resources_by_type = {child_type.__name__: [] for child_type in self._resource_to_authz_lookup[resource_type].child_resource_types}
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type.__name__ not in child_resources_by_type:
                child_resources_by_type[child_type.__name__] = []
            
            child_resources_by_type[child_type.__name__].append(child_resource.model_dump(mode="json"))

        identities_by_type = {identity_name: [] for identity_name in self._identity_type_names}
        for identity in identities:
            identity_type = type(identity)
            identities_by_type[identity_type.__name__].append(identity.model_dump(mode="json"))
        
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
            new_jmespath_data['resource'] = resource.model_dump(mode="json")
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
                    f"Parent resource type '{parent_type.__name__}' is not a registered resource."
                )
            
            if parent_type not in resource_authz_inst.parent_resource_types:
                raise exceptions.InputVerificationError(
                    f"Resource type '{parent_type.__name__}' is not a registered parent resource type of '{resource_type.__name__}'"
                )
        
        for child_resource in child_resources:
            child_type = type(child_resource)
            if child_type not in self._resource_types:
                raise exceptions.InputVerificationError(
                    f"Parent resource type '{child_type.__name__}' is not a registered resource."
                )
            
            if child_type not in resource_authz_inst.child_resource_types:
                raise exceptions.InputVerificationError(
                    f"Resource type '{child_type.__name__}' is not a registered child resource type of '{resource_type.__name__}'" 
                )

        for identity in identities:
            identity_type = type(identity)
            if identity_type not in self._identity_types:
                raise exceptions.InputVerificationError(
                    f"Identity type '{identity_type.__name__}' is not registered"
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
                    f"All resources must be of the same type: '{resource}' is not of type '{resource_type}'."
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
                f"Resource type '{resource_type.__name__}' is not a part of any registered ResourceAuthzs."
            )
        
        if len(grant.actions) < 1:
            raise exceptions.InputVerificationError("A set of at least one resource action must be given in a grant.")
        
        resource_authz_inst = self._resource_to_authz_lookup[resource_type]
        for resource_action in grant.actions:
            resource_action_type = type(resource_action)
            if resource_action_type not in self._resource_action_types:
                raise exceptions.InputVerificationError(
                    f"ResourceAction type '{resource_action_type.__name__}' is not registered."
                )

            if resource_action_type != resource_authz_inst.resource_action_type:
                raise exceptions.InputVerificationError(
                    "The '{resource_action}' resource action does not apply to the '{resource_type.__name__}' resource type."
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
                    f"Resource type '{resource_type.__name__}' is not a part of any registered ResourceAuthzs."
                )

        if resource_action is not None:
            resource_action_type = type(resource_action)
            if resource_action_type not in self._resource_action_types:
                raise exceptions.InputVerificationError(
                    f"ResourceAction type '{resource_action_type.__name__}' is not registered."
                )

        if resource_type is not None and resource_action is not None:
            resource_authz_inst = self._resource_to_authz_lookup[resource_type]
            if resource_action_type != resource_authz_inst.resource_action_type:
                raise exceptions.InputVerificationError(
                    f"The '{resource_action_type}' resource action type does not apply to the '{resource_type.__name__}' resource type."
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
            raise exceptions.InputVerificationError(
                f"Must use a GrantEffect, but '{effect}' was given."
            )

