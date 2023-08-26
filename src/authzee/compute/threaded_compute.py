
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import threading
from typing import Any, Dict, List, Optional, Type

import jmespath
from loguru import logger
from pydantic import BaseModel

from authzee.compute.compute_backend import ComputeBackend
from authzee.compute import general as gc
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend 


class ThreadedCompute(ComputeBackend):

    async_enabled: bool = True
    multi_process_enabled: bool = False


    def __init__(self, max_workers: Optional[int] = None):
        self._max_workers = max_workers
        if self._max_workers is None:
            self._max_workers = os.cpu_count()

        if self._max_workers < 2:
            raise


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
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self._max_workers,
            initializer=_executor_init,
            initargs=(self._jmespath_options,)
        )
        

    def shutdown(self) -> None:
        """Early clean up of compute backend resources.

        Will shutdown the thread pool without waiting for current tasks to finish.
        """
        self._thread_pool.shutdown(wait=False)


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
        cancel_event = threading.Event()
        done_pagination = False
        next_page_ref = None
        deny_match_event = threading.Event()
        deny_futures: List[asyncio.Future] = []
        next_page_task = None
        raw_grants_page = await self._storage_backend.get_raw_grants_page_async(
            effect=GrantEffect.DENY,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_ref
        )
        grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
        while (
            done_pagination is False
            and deny_match_event.is_set() is False
        ):
            next_page_ref = grants_page.next_page_reference
            if next_page_ref is None:
                done_pagination = True
            else:
                next_page_task = asyncio.Task(
                    self._storage_backend.get_raw_grants_page_async(
                        effect=GrantEffect.DENY,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref
                    )
                )

            deny_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    _executor_authorize,
                    grants_page, 
                    jmespath_data,
                    deny_match_event,
                    cancel_event
                )
            )
            if next_page_ref is not None:
                raw_grants_page = await next_page_task
                grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)

        done_pagination = False
        next_page_ref = None
        allow_futures = []
        allow_match_event = threading.Event()
        next_page_task = None
        raw_grants_page = await self._storage_backend.get_raw_grants_page_async(
            effect=GrantEffect.ALLOW,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_ref
        )
        grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
        while (
            done_pagination is False
            and allow_match_event.is_set() is False
            and deny_match_event.is_set() is False
        ):
            next_page_ref = grants_page.next_page_reference
            if next_page_ref is None:
                done_pagination = True
            else:
                next_page_task = asyncio.Task(
                    self._storage_backend.get_raw_grants_page_async(
                        effect=GrantEffect.ALLOW,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref
                    )
                )

            allow_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    _executor_authorize,
                    grants_page, 
                    jmespath_data,
                    allow_match_event,
                    cancel_event
                )
            )
            if next_page_ref is not None:
                raw_grants_page = await next_page_task
                grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
        
        if deny_match_event.is_set() is True:
            cancel_event.set()
            await self._cleanup_futures(futures=deny_futures + allow_futures)

            return False
        
        if len(deny_futures) > 0:
            await asyncio.gather(*deny_futures)
            if deny_match_event.is_set() is True:
                cancel_event.set()
                await self._cleanup_futures(futures=allow_futures)

                return False
        
        if allow_match_event.is_set() is True:
            cancel_event.set()
            await self._cleanup_futures(allow_futures)
            return True

        if len(allow_futures) > 0:
            await asyncio.gather(*allow_futures)
            if allow_match_event.is_set() is True:
                return True
        
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
        loop = asyncio.get_running_loop()
        done_pagination = False
        next_page_ref = None
        deny_futures: List[asyncio.Future] = []
        next_page_task = None
        results = {i: None for i in range(len(jmespath_data_entries))}
        grants_page = await self._storage_backend.get_grants_page_async(
            effect=GrantEffect.DENY,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_ref
        )
        while done_pagination is False:
            next_page_ref = grants_page.next_page_reference
            if next_page_ref is None:
                done_pagination = True
            else:
                next_page_task = asyncio.Task(
                    self._storage_backend.get_grants_page_async(
                        effect=GrantEffect.DENY,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref
                    )
                )

            deny_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    _executor_authorize_many,
                    grants_page, 
                    jmespath_data_entries
                )
            )
            if next_page_ref is not None:
                grants_page = await next_page_task

        done_pagination = False
        next_page_ref = None
        allow_futures = []
        next_page_task = None
        grants_page = await self._storage_backend.get_grants_page_async(
            effect=GrantEffect.ALLOW,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_ref
        )
        while done_pagination is False:
            next_page_ref = grants_page.next_page_reference
            if next_page_ref is None:
                done_pagination = True
            else:
                next_page_task = asyncio.Task(
                    self._storage_backend.get_grants_page_async(
                        effect=GrantEffect.ALLOW,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_ref
                    )
                )

            allow_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    _executor_authorize_many,
                    grants_page, 
                    jmespath_data_entries
                )
            )
            if next_page_ref is not None:
                grants_page = await next_page_task

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

        This will send a page of grants to each worker and return the results.
        
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

        This will send a page of grants to each worker and return the results.

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
        next_page_task = None
        pagination_done = False
        worker_num = 0
        grants_page =  await self._storage_backend.get_grants_page_async(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            next_page_reference=next_page_reference
        )
        while (
            worker_num < self._max_workers
            and pagination_done is False
        ):
            next_page_reference = grants_page.next_page_reference
            if next_page_reference is None:
                pagination_done = True

            if (
                next_page_reference is not None
                and worker_num + 1 < self._max_workers
            ):
                next_page_task = asyncio.Task(
                    self._storage_backend.get_grants_page_async(
                        effect=effect,
                        resource_type=resource_type,
                        resource_action=resource_action,
                        page_size=page_size,
                        next_page_reference=next_page_reference
                    )
                )

            futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    _executor_matching_grants,
                    grants_page, 
                    jmespath_data
                )
            )
            worker_num += 1
            if (
                next_page_reference is not None
                and worker_num + 1 < self._max_workers
            ):
                grants_page = await next_page_task
        
        results = await asyncio.gather(*futures)
        
        return GrantsPage(
            grants=[grant for result in results for grant in result],
            next_page_reference=next_page_reference
        )
        

    async def _cleanup_futures(self, futures: List[asyncio.Future]) -> None:
        gather_futures: List[asyncio.Future] = []
        for future in futures:
            if future.cancel() is False:
                gather_futures.append(future)
        
        await asyncio.gather(*gather_futures)


 
def _executor_init(jmespath_options: jmespath.Options) -> None:
    # each thread must get it's own copy of jmespath options and be able to retrieve it
    thread_var_name = "authzee_jmespath_options_t_{}".format(
        threading.get_ident()
    )
    globals()[thread_var_name] = deepcopy(jmespath_options)


def _executor_authorize(
    grants_page: GrantsPage, 
    jmespath_data: Dict[str, Any], 
    match_event: threading.Event,
    cancel_event: threading.Event
) -> bool:
    thread_var_name = "authzee_jmespath_options_t_{}".format(
        threading.get_ident()
    )
    return _authorize_grants(
        grants_page=grants_page,
        jmespath_data=jmespath_data,
        jmespath_options=globals()[thread_var_name],
        match_event=match_event,
        cancel_event=cancel_event
    )


def _authorize_grants(
    grants_page: GrantsPage, 
    jmespath_data: Dict[str, Any], 
    jmespath_options: jmespath.Options,
    match_event: threading.Event,
    cancel_event: threading.Event
) -> bool:
    for grant in grants_page.grants:
        if (
            match_event.is_set() is True
            or cancel_event.is_set() is True
        ):
            return False

        grant_match = gc.grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=jmespath_options
        )
        if grant_match is True:
            match_event.set()

            return True

    return False


def _executor_authorize_many(
    grants_page: GrantsPage, 
    jmespath_data_entries: List[Dict[str, Any]]
) -> bool:
    thread_var_name = "authzee_jmespath_options_t_{}".format(
        threading.get_ident()
    )
    return gc.authorize_many_grants(
        grants_page=grants_page,
        jmespath_data_entries=jmespath_data_entries,
        jmespath_options=globals()[thread_var_name]
    )


def _executor_matching_grants(
    grants_page: GrantsPage, 
    jmespath_data: Dict[str, Any]
) -> List[Grant]:
    thread_var_name = "authzee_jmespath_options_t_{}".format(
        threading.get_ident()
    )
    return gc.compute_matching_grants(
        grants_page=grants_page,
        jmespath_data=jmespath_data,
        jmespath_options=globals()[thread_var_name]
    )
