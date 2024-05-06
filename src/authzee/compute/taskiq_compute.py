
import asyncio
import base64
import pickle
from typing import Any, Dict, List, Optional, Type, Union
from typing_extensions import Annotated

import jmespath
from pydantic import BaseModel
import taskiq

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.compute.compute_backend import ComputeBackend
from authzee.compute import general as gc
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend
from authzee.storage_flag import StorageFlag


class TaskiqCompute(ComputeBackend):
    """Distributed compute with Taskiq. 

    Uses `Taskiq <https://taskiq-python.github.io/>`_ to distribute compute tasks.

    **NOTES** 

    - In the workers file you will need to create and initialize the authzee app 
    to make sure that all tasks and event handlers are added to the broker.

    - Must call broker.startup after authzee.initialize

    Examples
    --------
    
    Initializing Authzee with Taskiq:

        .. code-block:: python

            import asyncio
        
            from authzee import Authzee, TaskiqCompute, SQLStorage
            import taskiq

            broker = taskiq.InMemoryBroker()
            compute = TaskiqCompute(broker=broker)
            storage = SQLStorage(
                sqlalchemy_async_engine_kwargs={
                    "url": "sqlite+aiosqlite:///test.sqlite",
                    "echo": False
                }
            )
            authzee = Authzee(
                compute_backend=compute,
                storage_backend=storage,
                identity_types=[],
                resource_authzs=[]
            )
            # register identities and resource authzs as needed

            async def main():
                await authzee.initialize()
                # Only run setup once
                #await authzee.setup()
                await broker.startup()
                is_authorized = await authzee.authorize(
                    resource=Balloon(
                        color="green",
                        size=1.2
                    ),
                    action=BalloonAction.CreateBalloon,
                    parents=[],
                    children=[],
                    identities=[
                        ADGroup(cn="MYGroup")
                    ]
                )
                print(f"is authorized: {is_authorized}")
            
            
            asyncio.run(main())
    
    Taskiq workers file:
    
        .. code-block:: python

            # my_taskiq_workers.py
            import asyncio
        
            from authzee import Authzee, TaskiqCompute, SQLStorage
            import taskiq

            broker = taskiq.InMemoryBroker()
            compute = TaskiqCompute(broker=broker)
            storage = SQLStorage(
                sqlalchemy_async_engine_kwargs={
                    "url": "sqlite+aiosqlite:///test.sqlite",
                    "echo": False
                }
            )
            authzee = Authzee(
                compute_backend=compute,
                storage_backend=storage,
                identity_types=[],
                resource_authzs=[]
            )
            # register identities and resource authzs as needed

            async def main():
                await authzee.initialize()
                # Only run setup once
                #await authzee.setup()
                await broker.startup()
            
                
            asyncio.run(main())

    The workers for Taskiq will run from the workers file.
    Then start the workers (note that workers are not needed for in memory broker)

        .. code-block:: console
    
            taskiq worker my_taskiq_workers:broker

    Parameters
    ----------
    broker : taskiq.AsyncBroker
        Taskiq broker for compute and results. 
        The ``startup()`` method should not be run on the broker. 
    check_interval : float, default: 0.01
        Interval to poll if worker results are available.
    task_timeout : float, default: 2.0 
        Timeout in seconds for TASKiq tasks to finish. 
    """


    def __init__(
        self,
        broker: taskiq.AsyncBroker,
        check_interval: float = 0.01,
        task_timeout: float = 2.0
    ):
        self._broker = broker
        self._check_interval = check_interval
        self._task_timeout = task_timeout
        locality = BackendLocality.NETWORK
        if type(self._broker) is taskiq.InMemoryBroker:
            locality = BackendLocality.PROCESS
        
        super().__init__(
            backend_locality=locality,
            supports_parallel_paging=False,
            use_parallel_paging=False
        )


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
        await super().initialize(
            identity_types=identity_types,
            jmespath_options=jmespath_options,
            resource_authzs=resource_authzs,
            storage_backend=storage_backend
        )
        self._authorize_task = self._broker.register_task(
            _authorize_task, 
            "authzee.authorize"
        )
        self._authorize_many_task = self._broker.register_task(
            _authorize_many_task, 
            "authzee.authorize_many"
        )
        self._get_matching_grants_page_task = self._broker.register_task(
            _get_matching_grants_page_task, 
            "authzee.get_matching_grants_page"
        )

        async def worker_startup(state: taskiq.TaskiqState) -> None:
            state.az_broker = self._broker
            state.az_jmespath_options = self._jmespath_options
            state.az_check_interval = self._check_interval
            state.az_task_timeout = self._task_timeout
            state.az_authorize_task = self._authorize_task
            state.az_authorize_many_task = self._authorize_many_task
            state.az_get_matching_grants_page_task = self._get_matching_grants_page_task
            if self._storage_backend.backend_locality is BackendLocality.PROCESS:
                state.az_storage_backend = self._storage_backend
            else:
                state.az_storage_backend = type(self._storage_backend)(**self._storage_backend.kwargs)
                await state.az_storage_backend.initialize(**self._storage_backend.initialize_kwargs)

        self._broker.add_event_handler(taskiq.TaskiqEvents.WORKER_STARTUP, worker_startup)


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
        action: ResourceAction,
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
        action : ResourceAction
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
        """
        deny_flag, allow_flag = await asyncio.gather(
            self._storage_backend.create_flag(),
            self._storage_backend.create_flag()
        )
        kwargs = {
            "resource_type": resource_type,
            "action": action,
            "jmespath_data": jmespath_data,
            "page_size": page_size,
            "page_ref": None,
            "deny_flag_uuid": deny_flag.uuid,
            "allow_flag_uuid": allow_flag.uuid,
            "more_deny_grants": True
        }
        task: taskiq.AsyncTaskiqTask = await self._authorize_task.kiq(
            _kwargs_dumps(**kwargs)
        )
        await task.wait_result(
            check_interval=self._check_interval, 
            timeout=self._task_timeout
        )
        # refresh flags
        deny_flag, allow_flag = await asyncio.gather(
            self._storage_backend.get_flag(deny_flag.uuid),
            self._storage_backend.get_flag(allow_flag.uuid)
        )
        if deny_flag.is_set is True:
            return False
        
        if allow_flag.is_set is True:
            return True
        
        return False
    

    async def authorize_many(
        self, 
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        action : ResourceAction
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
        kwargs = {
            "resource_type": resource_type,
            "action": action,
            "jmespath_data_entries": jmespath_data_entries,
            "page_size": page_size,
            "page_ref": None,
            "more_deny_grants": True
        }
        task: taskiq.AsyncTaskiqTask = await self._authorize_many_task.kiq(
            _kwargs_dumps(**kwargs)
        )
        task_result = await task.wait_result(
            check_interval=self._check_interval, 
            timeout=self._task_timeout
        )
        auth_list = []
        for auth in task_result.return_value:
            if auth is None:
                auth_list.append(False)
            else:
                auth_list.append(auth)

        return auth_list


    async def get_matching_grants_page(
        self, 
        effect: GrantEffect,
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        action : ResourceAction
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
        kwargs = {
            "effect": effect,
            "resource_type": resource_type,
            "action": action,
            "jmespath_data": jmespath_data,
            "page_size": page_size,
            "page_ref": page_ref
        }
        task: taskiq.AsyncTaskiqTask = await self._get_matching_grants_page_task.kiq(
            _kwargs_dumps(**kwargs)
        )
        result = await task.wait_result(
            check_interval=self._check_interval, 
            timeout=self._task_timeout
        )
        
        return result.return_value


def _kwargs_dumps(**kwargs) -> str:
    return base64.b64encode(
        pickle.dumps(kwargs)
    ).decode("ascii")


def _kwargs_loads(kwp: str) -> Dict[str, Any]:
    return pickle.loads(
        base64.b64decode(kwp.encode("ascii"))
    )


async def _authorize_task(
    kwp: str,
    context: Annotated[taskiq.Context, taskiq.TaskiqDepends()]
) -> None:
    authorize_task: taskiq.AsyncTaskiqDecoratedTask = context.state.az_authorize_task
    jmespath_options: Union[jmespath.Options, None] = context.state.az_jmespath_options
    storage_backend: StorageBackend = context.state.az_storage_backend
    check_interval: float = context.state.az_check_interval
    task_timeout: float = context.state.az_task_timeout
    kwargs = _kwargs_loads(kwp)
    resource_type: BaseModel = kwargs['resource_type']
    action: ResourceAction = kwargs['action']
    jmespath_data: Dict[str, Any] = kwargs['jmespath_data']
    page_size: Union[int, None] = kwargs['page_size']
    page_ref: Union[str, None] = kwargs['page_ref']
    more_deny_grants: bool = kwargs['more_deny_grants']
    deny_flag_uuid: Union[str, None] = kwargs['deny_flag_uuid']
    allow_flag_uuid: Union[str, None] = kwargs['allow_flag_uuid']
    deny_flag: StorageFlag
    allow_flag: StorageFlag
    deny_flag, allow_flag = await asyncio.gather(
        storage_backend.get_flag(deny_flag_uuid),
        storage_backend.get_flag(allow_flag_uuid)
    )

    if (
        deny_flag.is_set is True
        or allow_flag.is_set is True
    ):
        return 

    if more_deny_grants is True:
        raw_grants = await storage_backend.get_raw_grants_page(
            effect=GrantEffect.DENY,
            resource_type=resource_type,
            action=action,
            page_size=page_size,
            page_ref=page_ref
        )
        if raw_grants.next_page_ref is None:
            more_deny_grants = False

        next_task_kiq = asyncio.create_task(
            authorize_task.kiq(
                _kwargs_dumps(
                    **{
                        "resource_type": resource_type,
                        "action": action,
                        "jmespath_data": jmespath_data,
                        "page_size": page_size,
                        "page_ref": raw_grants.next_page_ref,
                        "deny_flag_uuid": deny_flag.uuid,
                        "allow_flag_uuid": allow_flag.uuid,
                        "more_deny_grants": more_deny_grants,
                    }
                )
            )
        )
        grants_page = await storage_backend.normalize_raw_grants_page(raw_grants)
        for grant in grants_page.grants:
            if gc.grant_matches(
                grant=grant,
                jmespath_data=jmespath_data,
                jmespath_options=jmespath_options
            ) is True:
                deny_flag = await storage_backend.set_flag(deny_flag.uuid)
                break
        
        next_task_iq = await next_task_kiq
        await next_task_iq.wait_result(
            check_interval=check_interval,
            timeout=task_timeout
        )

        return 

    else:
        raw_grants = await storage_backend.get_raw_grants_page(
            effect=GrantEffect.ALLOW,
            resource_type=resource_type,
            action=action,
            page_size=page_size,
            page_ref=page_ref
        )
        if raw_grants.next_page_ref is not None:
            next_task_kiq = asyncio.create_task(
                authorize_task.kiq(
                    _kwargs_dumps(
                        **{
                            "resource_type": resource_type,
                            "action": action,
                            "jmespath_data": jmespath_data,
                            "page_size": page_size,
                            "page_ref": raw_grants.next_page_ref,
                            "deny_flag_uuid": deny_flag.uuid,
                            "allow_flag_uuid": allow_flag.uuid,
                            "more_deny_grants": more_deny_grants,
                        }
                    )
                )
            )
        else:
            next_task_kiq = None

        grants_page = await storage_backend.normalize_raw_grants_page(raw_grants)
        for grant in grants_page.grants:
            if gc.grant_matches(
                grant=grant,
                jmespath_data=jmespath_data,
                jmespath_options=jmespath_options
            ) is True:
                allow_flag = await storage_backend.set_flag(allow_flag.uuid)
                break
        
        if next_task_kiq is not None:
            next_task_iq = await next_task_kiq
            await next_task_iq.wait_result(
                check_interval=check_interval,
                timeout=task_timeout
            )


async def _authorize_many_task(
    kwp: str,
    context: Annotated[taskiq.Context, taskiq.TaskiqDepends()]
) -> List[Union[bool, None]]:
    authorize_many_task: taskiq.AsyncTaskiqDecoratedTask = context.state.az_authorize_many_task
    jmespath_options: Union[jmespath.Options, None] = context.state.az_jmespath_options
    storage_backend: StorageBackend = context.state.az_storage_backend
    check_interval: float = context.state.az_check_interval
    task_timeout: float = context.state.az_task_timeout
    kwargs = _kwargs_loads(kwp)
    resource_type: BaseModel = kwargs['resource_type']
    action: ResourceAction = kwargs['action']
    jmespath_data_entries: List[Dict[str, Any]] = kwargs['jmespath_data_entries']
    page_size: Union[int, None] = kwargs['page_size']
    page_ref: Union[str, None] = kwargs['page_ref']
    more_deny_grants: bool = kwargs['more_deny_grants']

    if more_deny_grants is True:
        raw_grants = await storage_backend.get_raw_grants_page(
            effect=GrantEffect.DENY,
            resource_type=resource_type,
            action=action,
            page_size=page_size,
            page_ref=page_ref
        )
        if raw_grants.next_page_ref is None:
            more_deny_grants = False

        next_task_kiq = asyncio.create_task(
            authorize_many_task.kiq(
                _kwargs_dumps(
                    **{
                        "resource_type": resource_type,
                        "action": action,
                        "jmespath_data_entries": jmespath_data_entries,
                        "page_size": page_size,
                        "page_ref": raw_grants.next_page_ref,
                        "more_deny_grants": more_deny_grants
                    }
                )
            )
        )
        grants_page = await storage_backend.normalize_raw_grants_page(raw_grants)
        results = gc.authorize_many_grants(
            grants_page=grants_page,
            jmespath_data_entries=jmespath_data_entries,
            jmespath_options=jmespath_options
        )
        auth_list = []
        for result in results:
            # if deny match, not authorized
            if result is True:
                auth_list.append(False)
            else:
                auth_list.append(None)

        next_task_iq = await next_task_kiq
        next_results = await next_task_iq.wait_result(
            check_interval=check_interval,
            timeout=task_timeout
        )
        combined_auth_list = []
        for auth, nr in zip(auth_list, next_results.return_value):
            # if it's an explicit deny, always use that
            if auth is False:
                combined_auth_list.append(False)
            # or else just pass on the value from the next task
            else:
                combined_auth_list.append(nr)
        
        return combined_auth_list

    else:
        raw_grants = await storage_backend.get_raw_grants_page(
            effect=GrantEffect.ALLOW,
            resource_type=resource_type,
            action=action,
            page_size=page_size,
            page_ref=page_ref
        )
        if raw_grants.next_page_ref is not None:
            next_task_kiq = asyncio.create_task(
                authorize_many_task.kiq(
                    _kwargs_dumps(
                        **{
                            "resource_type": resource_type,
                            "action": action,
                            "jmespath_data_entries": jmespath_data_entries,
                            "page_size": page_size,
                            "page_ref": raw_grants.next_page_ref,
                            "more_deny_grants": more_deny_grants
                        }
                    )
                )
            )
        else:
            next_task_kiq = None

        grants_page = await storage_backend.normalize_raw_grants_page(raw_grants)
        results = gc.authorize_many_grants(
            grants_page=grants_page,
            jmespath_data_entries=jmespath_data_entries,
            jmespath_options=jmespath_options
        )
        auth_list = []
        for result in results:
            # if allow match, authorized
            if result is True:
                auth_list.append(True)
            else:
                auth_list.append(None)

        if next_task_kiq is not None:
            next_task_iq = await next_task_kiq
            next_results = await next_task_iq.wait_result(
                check_interval=check_interval,
                timeout=task_timeout
            )
            combined_auth_list = []
            for auth, nr in zip(auth_list, next_results.return_value):
                # if it's an explicit allow, always use that
                if auth is True:
                    combined_auth_list.append(True)
                # or else just pass on the next 
                else:
                    combined_auth_list.append(nr)
            
            return combined_auth_list

        else:
            return auth_list


async def _get_matching_grants_page_task(
    kwp: str,
    context: Annotated[taskiq.Context, taskiq.TaskiqDepends()]
) -> GrantsPage:
    jmespath_options: Union[jmespath.Options, None] = context.state.az_jmespath_options
    storage_backend: StorageBackend = context.state.az_storage_backend
    kwargs = _kwargs_loads(kwp)
    effect: GrantEffect = kwargs['effect']
    resource_type: BaseModel = kwargs['resource_type']
    action: ResourceAction = kwargs['action']
    jmespath_data: Dict[str, Any] = kwargs['jmespath_data']
    page_size: Union[int, None] = kwargs['page_size']
    page_ref: Union[str, None] = kwargs['page_ref']
    raw_grants = await storage_backend.get_raw_grants_page(
        effect=effect,
        resource_type=resource_type,
        action=action,
        page_size=page_size,
        page_ref=page_ref
    )
    grants_page = await storage_backend.normalize_raw_grants_page(raw_grants)
    matching_grants = gc.compute_matching_grants(
        grants_page=grants_page,
        jmespath_data=jmespath_data,
        jmespath_options=jmespath_options
    )

    return GrantsPage(
        grants=matching_grants,
        next_page_ref=grants_page.next_page_ref
    )


