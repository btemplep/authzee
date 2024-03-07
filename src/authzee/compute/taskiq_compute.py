
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
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend


class TaskiqCompute(ComputeBackend):
    """Distributed compute with Taskiq. 

    Uses `Taskiq <https://taskiq-python.github.io/>`_ to distribute compute tasks.

    Example of how to use and the workers file. 


    **NOTES** 

    - In the workers file you will need to create and initialize the authzee app 
    to make sure that all tasks and event handlers are added to the broker.

    - Must call broker.startup after authzee.initialize

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
            parallel_pagination=False
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
            print("start worker startup")
            state.jmespath_options = self._jmespath_options
            if self._storage_backend.backend_locality is BackendLocality.PROCESS:
                state.storage_backend = self._storage_backend
            else:
                state.storage_backend = type(self._storage_backend)(**self._storage_backend.kwargs)
                await state.storage_backend.initialize(**self._storage_backend.initialize_kwargs)

            print("end worker startup")

        self._broker.add_event_handler(taskiq.TaskiqEvents.WORKER_STARTUP, worker_startup)


    async def shutdown(self) -> None:
        """Early clean up of compute backend resources.
        """
        await self._broker.shutdown() 


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
        """
        kwargs = {
            "resource_type": resource_type,
            "resource_action": resource_action,
            "jmespath_data": jmespath_data,
            "page_size": page_size
        }
        task = await self._authorize_task.kiq(
            base64.b64encode(
                pickle.dumps(kwargs)
            ).decode("ascii")
        )
        result = await task.wait_result(
            check_interval=self._check_interval, 
            timeout=self._task_timeout
        )

        return result.return_value
    

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


async def _authorize_task(
    kwp: str,
    context: Annotated[taskiq.Context, taskiq.TaskiqDepends()]
) -> bool:
    jmespath_options: Union[jmespath.Options, None] = context.state.jmespath_options
    storage_backend: StorageBackend = context.state.storage_backend
    print("Got to authorize task")
    print(jmespath_options)
    print(storage_backend)
    kwargs = pickle.loads(
        base64.b64decode(kwp.encode("ascii"))
    )
    resource_type: BaseModel = kwargs['resource_type']
    resource_action: ResourceAction = kwargs['resource_action']
    jmespath_data: Dict[str, Any] = kwargs['jmespath_data']
    page_size: Union[int, None] = kwargs['page_size']
    
    
    return False


async def _authorize_many_task(kwp: bytes) -> List[bool]:
    print(f"authorize many task got: {pickle.loads(kwp)}")


async def _get_matching_grants_page_task(kwp: bytes) -> bytes: # GrantsPage:
    print(f"get matching grants page task got: {pickle.loads(kwp)}")

