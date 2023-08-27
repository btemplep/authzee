
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
import multiprocessing as mp
from multiprocessing.connection import Connection
from multiprocessing.context import BaseContext
from multiprocessing.managers import SharedMemoryManager
import os
from typing import Any, Dict, List, Optional, Type, Union

import jmespath
from loguru import logger
from pydantic import BaseModel

from authzee.compute.compute_backend import ComputeBackend
from authzee import exceptions
from authzee.compute import general as gc
from authzee.compute.shared_mem_event import SharedMemEvent
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend 


class MultiprocessCompute(ComputeBackend):

    async_enabled: bool = True
    multi_process_enabled: bool = True


    def __init__(
            self,
            max_workers: Optional[int] = None,
            mp_context: Optional[BaseContext] = None
        ):
        self._max_workers = max_workers
        if self._max_workers is None:
            self._max_workers = len(os.sched_getaffinity(0))
        self._mp_context = mp_context


    def initialize(
        self, 
        identity_types: List[Type[BaseModel]],
        jmespath_options: jmespath.Options,
        resource_authzs: List[ResourceAuthz],
        storage_backend: StorageBackend,
    ) -> None:
        """Initialize multiprocess backend.

        Should only be called by the ``Authzee`` app.

        Parameters
        ----------
        identity_types : List[Type[BaseModel]]
            Identity types registered with the ``Authzee`` app.
        jmespath_options : jmespath.Options
            Custom ``jmespath.Options`` registered with the ``Authzee`` app.
        resource_authzs : List[ResourceAuthz]
            ``ResourceAuthz`` s registered with the ``Authzee`` app.
        storage_backend : StorageBackend
            Storage backend registered with the ``Authzee`` app.
        """
        super().initialize(
            identity_types=identity_types,
            jmespath_options=jmespath_options,
            resource_authzs=resource_authzs,
            storage_backend=storage_backend
        )
        self._process_pool = ProcessPoolExecutor(
            max_workers=self._max_workers, 
            mp_context=self._mp_context,
            initializer=partial(
                _executor_init,
                storage_type=type(self._storage_backend),
                storage_kwargs=self._storage_backend.kwargs,
                initialize_kwargs=self._storage_backend.initialize_kwargs,
                jmespath_options=jmespath_options
            )
        )
        # Thread pool for converting pipe actions to async
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        self._shared_mem_manager = SharedMemoryManager()
        self._shared_mem_manager.start()


    def shutdown(self) -> None:
        """Early clean up of compute backend resources.

        Will shutdown the process pool without waiting for current tasks to finish.
        """
        self._process_pool.shutdown(wait=False)
        self._thread_pool.shutdown(wait=False)
        self._shared_mem_manager.shutdown()
        

    def authorize(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None
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
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.authorize_async(
                resource_type=resource_type,
                resource_action=resource_action,
                jmespath_data=jmespath_data,
                page_size=page_size
            )
        )


    async def authorize_async(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None
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
        loop = asyncio.get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        cancel_event = SharedMemEvent(smm=self._shared_mem_manager)
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event.is_set() is False
        ):
            did_once = True
            recv_conn, send_conn = mp.Pipe(duplex=False)
            deny_futures.append(
                loop.run_in_executor(
                    self._process_pool,
                    partial(
                        _executor_grant_page_matches_deny,
                        effect=GrantEffect.DENY,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref,
                        jmespath_data=jmespath_data,
                        pipe_conn=send_conn,
                        cancel_event=cancel_event
                    )
                )
            )
            # wait for next page ref from child
            next_page_ref = await loop.run_in_executor(
                self._thread_pool,
                recv_conn.recv
            )

        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        allow_match_event = SharedMemEvent(smm=self._shared_mem_manager)
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event.is_set() is False
            and allow_match_event.is_set() is False
        ):
            did_once = True
            recv_conn, send_conn = mp.Pipe(duplex=False)
            allow_futures.append(
                loop.run_in_executor(
                    self._process_pool,
                    partial(
                        _executor_grant_page_matches_allow,
                        effect=GrantEffect.ALLOW,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref,
                        jmespath_data=jmespath_data,
                        pipe_conn=send_conn,
                        cancel_event=cancel_event,
                        allow_match_event=allow_match_event
                    )
                )
            )
            # wait for next page ref from child
            next_page_ref = await loop.run_in_executor(
                self._thread_pool,
                recv_conn.recv
            )
        
        # If we found a deny then cleanup tasks and return False
        if cancel_event.is_set() is True:
            await self._cleanup_futures(futures=deny_futures + allow_futures)
            cancel_event.unlink()
            allow_match_event.unlink()

            return False
        # Then check if we ran any deny tasks and recheck cancel status
        elif len(deny_futures) > 0:
            await asyncio.gather(*deny_futures)
            if cancel_event.is_set() is True:
                await self._cleanup_futures(futures=allow_futures)
                cancel_event.unlink()
                allow_match_event.unlink()

                return False
        
        # Check for allow match
        if allow_match_event.is_set() is True:
            cancel_event.set()
            await self._cleanup_futures(allow_futures)
            cancel_event.unlink()
            allow_match_event.unlink()

            return True
        # Then check if we ran any allow tasks and recheck allow match status
        elif len(allow_futures) > 0:
            await asyncio.gather(*allow_futures)
            if allow_match_event.is_set() is True:
                cancel_event.unlink()
                allow_match_event.unlink()
                
                return True
        
        cancel_event.unlink()
        allow_match_event.unlink()

        return False


    def authorize_many(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data_entries: List[Dict[str, Any]],
        page_size: Optional[int] = None
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
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.authorize_many_async(
                resource_type=resource_type,
                resource_action=resource_action,
                jmespath_data_entries=jmespath_data_entries,
                page_size=page_size
            )
        ) 


    async def authorize_many_async(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data_entries: List[Dict[str, Any]],
        page_size: Optional[int] = None
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
        """
        results = {i: None for i in range(len(jmespath_data_entries))}
        loop = asyncio.get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            recv_conn, send_conn = mp.Pipe(duplex=False)
            deny_futures.append(
                loop.run_in_executor(
                    self._process_pool,
                    partial(
                        _executor_authorize_many,
                        effect=GrantEffect.DENY,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref,
                        jmespath_data_entries=jmespath_data_entries,
                        pipe_conn=send_conn
                    )
                )
            )
            # wait for next page ref from child
            next_page_ref = await loop.run_in_executor(
                self._thread_pool,
                recv_conn.recv
            )

        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            recv_conn, send_conn = mp.Pipe(duplex=False)
            allow_futures.append(
                loop.run_in_executor(
                    self._process_pool,
                    partial(
                        _executor_authorize_many,
                        effect=GrantEffect.ALLOW,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref,
                        jmespath_data_entries=jmespath_data_entries,
                        pipe_conn=send_conn
                    )
                )
            )
            # wait for next page ref from child
            next_page_ref = await loop.run_in_executor(
                self._thread_pool,
                recv_conn.recv
            )

        if len(deny_futures) > 0:
            deny_results: List[List[bool]] = await asyncio.gather(*deny_futures)
            for result_set in deny_results:
                for i, result in zip(results, result_set):
                    if result is True:
                        results[i] = False

        if len(allow_futures) > 0:
            allow_results: List[List[bool]] = await asyncio.gather(*allow_futures)
            for result_set in allow_results:
                for i, result in zip(results, result_set):
                    if result is True:
                        results[i] = True
        
        return [val is True for val in list(results.values())]


    def get_matching_grants_page(
        self, 
        effect: GrantEffect,
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None,
        next_page_reference: Optional[str] = None
    ) -> GrantsPage:
        """Retrieve a page of matching grants. 

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        ``max_worker`` pages of grants (using ``page_size`` ) will be pulled and checked for matches. 
        
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
        next_page_reference : Optional[str], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the first page.

        Returns
        -------
        GrantsPage
            The page of matching grants.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.get_matching_grants_page_async(
                effect=effect,
                resource_type=resource_type,
                resource_action=resource_action,
                jmespath_data=jmespath_data,
                page_size=page_size,
                next_page_reference=next_page_reference
            )
        )


    async def get_matching_grants_page_async(
        self, 
        effect: GrantEffect,
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None,
        next_page_reference: Optional[str] = None
    ) -> GrantsPage:
        """Retrieve a page of matching grants. 

        If ``GrantsPage.next_page_reference`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``next_page_reference=GrantsPage.next_page_reference`` .

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        ``max_worker`` pages of grants (using ``page_size`` ) will be pulled and checked for matches. 

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
        next_page_reference : Optional[str], optional
            The reference to the next page that is returned in ``GrantsPage``.
            By default this will return the first page.

        Returns
        -------
        GrantsPage
            The page of matching grants.
        """
        loop = asyncio.get_running_loop()
        futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        worker_num = 0
        while (
            worker_num < self._max_workers
            and did_once is not True
            or next_page_ref is not None
        ):
            worker_num += 1
            did_once = True
            recv_conn, send_conn = mp.Pipe(duplex=False)
            futures.append(
                loop.run_in_executor(
                    self._process_pool,
                    partial(
                        _executor_matching_grants,
                        effect=effect,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref,
                        jmespath_data=jmespath_data,
                        pipe_conn=send_conn
                    )
                )
            )
            # wait for next page ref from child
            next_page_ref = await loop.run_in_executor(
                self._thread_pool,
                recv_conn.recv
            )
        
        results = await asyncio.gather(*futures)
        
        return GrantsPage(
            grants=[grant for grants_list in results for grant in grants_list],
            next_page_reference=next_page_reference
        )
        

    async def _cleanup_futures(self, futures: List[asyncio.Future]) -> None:
        gather_futures: List[asyncio.Future] = []
        for future in futures:
            if future.cancel() is False:
                gather_futures.append(future)
        
        await asyncio.gather(*gather_futures)

 
def _executor_init(
    storage_type: Type[StorageBackend],
    storage_kwargs: Dict[str, Any],
    initialize_kwargs: Dict[str, Any],
    jmespath_options: jmespath.Options
) -> None:
    global authzee_jmespath_options
    authzee_jmespath_options = jmespath_options
    global authzee_storage
    authzee_storage = storage_type(**storage_kwargs)
    authzee_storage.initialize(**initialize_kwargs)


def _executor_grant_page_matches_deny(
    effect: GrantEffect,
    resource_type: Type[BaseModel],
    resource_action: ResourceAction,
    page_size: int,
    next_page_reference: Union[str, None],
    jmespath_data: Dict[str, Any],
    pipe_conn: Connection,
    cancel_event: SharedMemEvent
) -> bool:
    global authzee_jmespath_options
    global authzee_storage
    raw_grants = authzee_storage.get_raw_grants_page(
        effect=effect,
        resource_type=resource_type,
        resource_action=resource_action,
        page_size=page_size,
        next_page_reference=next_page_reference
    )
    # Send back next page ref to parent
    pipe_conn.send(raw_grants.next_page_reference)
    if cancel_event.is_set() is True:
        return False

    grants_page = authzee_storage.normalize_raw_grants_page(
        raw_grants_page=raw_grants
    )
    if cancel_event.is_set() is True:
        return False
    
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=authzee_jmespath_options
        ):
            cancel_event.set()
            return True

        if cancel_event.is_set() is True:
            return False

    return False
 

def _executor_grant_page_matches_allow(
    effect: GrantEffect,
    resource_type: Type[BaseModel],
    resource_action: ResourceAction,
    page_size: int,
    next_page_reference: Union[str, None],
    jmespath_data: Dict[str, Any],
    pipe_conn: Connection,
    cancel_event: SharedMemEvent,
    allow_match_event: SharedMemEvent
) -> bool:
    global authzee_jmespath_options
    global authzee_storage
    raw_grants = authzee_storage.get_raw_grants_page(
        effect=effect,
        resource_type=resource_type,
        resource_action=resource_action,
        page_size=page_size,
        next_page_reference=next_page_reference
    )
    pipe_conn.send(raw_grants.next_page_reference)
    if (
        cancel_event.is_set() is True
        or allow_match_event.is_set() is True
    ):
        return False

    grants_page = authzee_storage.normalize_raw_grants_page(
        raw_grants_page=raw_grants
    )
    if (
        cancel_event.is_set() is True
        or allow_match_event.is_set() is True
    ):
        return False
    
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=authzee_jmespath_options
        ):
            allow_match_event.set()
            return True

        if (
            cancel_event.is_set() is True
            or allow_match_event.is_set() is True
        ):
            return False

    return False


def _executor_authorize_many(
    effect: GrantEffect,
    resource_type: Type[BaseModel],
    resource_action: ResourceAction,
    page_size: int,
    next_page_reference: Union[str, None],
    jmespath_data_entries: List[Dict[str, Any]],
    pipe_conn: Connection
) -> List[bool]:
    global authzee_storage
    global authzee_jmespath_options
    raw_page = authzee_storage.get_raw_grants_page(
        effect=effect,
        resource_type=resource_type,
        resource_action=resource_action,
        page_size=page_size,
        next_page_reference=next_page_reference
    )
    pipe_conn.send(raw_page.next_page_reference)
    grants_page = authzee_storage.normalize_raw_grants_page(raw_grants_page=raw_page)

    return gc.authorize_many_grants(
        grants_page=grants_page,
        jmespath_data_entries=jmespath_data_entries,
        jmespath_options=authzee_jmespath_options
    )


def _executor_matching_grants(
    effect: GrantEffect,
    resource_type: Type[BaseModel],
    resource_action: ResourceAction,
    page_size: int,
    next_page_reference: Union[str, None],
    jmespath_data: Dict[str, Any],
    pipe_conn: Connection
) -> List[Grant]:
    global authzee_storage
    global authzee_jmespath_options
    raw_page = authzee_storage.get_raw_grants_page(
        effect=effect,
        resource_type=resource_type,
        resource_action=resource_action,
        page_size=page_size,
        next_page_reference=next_page_reference
    )
    pipe_conn.send(raw_page.next_page_reference)
    grants_page = authzee_storage.normalize_raw_grants_page(raw_grants_page=raw_page)

    return gc.compute_matching_grants(
        grants_page=grants_page,
        jmespath_data=jmespath_data,
        jmespath_options=authzee_jmespath_options
    )

