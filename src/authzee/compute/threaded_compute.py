
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from functools import partial
import os
import threading
from typing import Any, Dict, List, Optional, Type, Union

import jmespath
from loguru import logger
from pydantic import BaseModel

from authzee.backend_locality import BackendLocality
from authzee.compute import general as gc
from authzee.compute.compute_backend import ComputeBackend
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.loop import get_event_loop, get_running_loop
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend 


class ThreadedCompute(ComputeBackend):
    """Multithreaded compute backend.

    Uses a pool of threads for compute.
    
    Threaded Compute may actually be slower than ``MainProcessCompute`` because of the overhead of threads,
    and the GIL stopping multiple threads from executing python code at once. 
    But it does offer async, and doesn't require extra processes.


    Parameters
    ----------
    max_workers : Optional[int], optional
        The max number of worker processes.
        By default it will be the number of processor cores on the system.

    Examples
    --------
    .. code-block:: python

        from authzee import Authzee

    """


    def __init__(
            self, 
            max_workers: Optional[int] = None,
            use_parallel_paging: bool = True
        ):
        super().__init__(
            backend_locality=BackendLocality.PROCESS,
            supports_parallel_paging=True,
            use_parallel_paging=use_parallel_paging
        )
        self._max_workers = max_workers
        if self._max_workers is None:
            self._max_workers = os.cpu_count()

        if self._max_workers < 2:
            raise


    async def initialize(
        self, 
        identity_types: List[Type[BaseModel]],
        jmespath_options: Union[jmespath.Options, None],
        resource_authzs: List[ResourceAuthz],
        storage_backend: StorageBackend,
    ) -> None:
        """Initialize multiprocess backend.

        Should only be called by the ``Authzee`` app.

        Parameters
        ----------
        identity_types : List[Type[BaseModel]]
            Identity types registered with the ``Authzee`` app.
        jmespath_options : Union[jmespath.Options, None]
            Custom ``jmespath.Options`` registered with the ``Authzee`` app.
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
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self._max_workers,
            initializer=_executor_init,
            initargs=(self._jmespath_options,)
        )
        if self.supports_parallel_paging is True and self.use_parallel_paging is True:
            self.authorize = self._authorize_parallel_paging
            self.authorize_many = self._authorize_many_parallel_paging
            self.get_matching_grants_page = self._get_matching_grants_page_parallel_paging
        

    async def shutdown(self) -> None:
        """Early clean up of compute backend resources.

        Will shutdown the thread pool without waiting for current tasks to finish.
        """
        self._thread_pool.shutdown(wait=False)


    async def authorize(
        self, 
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        if self._storage_backend.supports_parallel_paging is True:
            return await self._authorize_parallel_paging(
                resource_type=resource_type,
                action=action,
                jmespath_data=jmespath_data,
                page_size=page_size
            )

        loop = get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        cancel_event = {"set": False}
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event['set'] is False
        ):
            did_once = True
            raw_grants_page = await self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            deny_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    partial(
                        _executor_authorize_deny,
                        storage_backend=self._storage_backend,
                        raw_grants_page=raw_grants_page,
                        jmespath_data=jmespath_data,
                        cancel_event=cancel_event
                    )
                )
            )
        

        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        allow_match_event = {"set": False}
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event['set'] is False
            and allow_match_event['set'] is False
        ):
            did_once = True
            raw_grants_page = await self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            allow_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    partial(
                        _executor_authorize_allow,
                        storage_backend=self._storage_backend,
                        raw_grants_page=raw_grants_page,
                        jmespath_data=jmespath_data,
                        cancel_event=cancel_event,
                        allow_match_event=allow_match_event
                    )
                )
            )

        if cancel_event['set'] is True:
            await self._cleanup_futures(futures=deny_futures + allow_futures)

            return False
        
        elif len(deny_futures) > 0:
            await asyncio.gather(*deny_futures)
            if cancel_event['set'] is True:
                await self._cleanup_futures(futures=allow_futures)

                return False
        
        if allow_match_event['set'] is True:
            await self._cleanup_futures(allow_futures)

            return True

        elif len(allow_futures) > 0:
            await asyncio.gather(*allow_futures)
            if allow_match_event['set'] is True:
                return True
        
        return False


    async def _authorize_parallel_paging(
        self, 
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        loop = get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        cancel_event = {"set": False}
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event['set'] is False
        ):
            did_once = True
            raw_grants_pages_page = await self._storage_backend.get_page_ref_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            next_page_ref = raw_grants_pages_page.next_page_ref
            for ref in raw_grants_pages_page.page_refs:
                deny_futures.append(
                    loop.run_in_executor(
                        self._thread_pool,
                        partial(
                            _executor_authorize_deny_ref,
                            storage_backend=self._storage_backend,
                            raw_grants_kwargs={
                                "effect": GrantEffect.DENY,
                                "resource_type": resource_type,
                                "action": action,
                                "page_size": page_size,
                                "page_ref": ref
                            },
                            jmespath_data=jmespath_data,
                            cancel_event=cancel_event
                        )
                    )
                )

        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        allow_match_event = {"set": False}
        while (
            (
                did_once is not True
                or next_page_ref is not None
            )
            and cancel_event['set'] is False
            and allow_match_event['set'] is False
        ):
            did_once = True
            raw_grants_pages_page = await self._storage_backend.get_page_ref_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            next_page_ref = raw_grants_pages_page.next_page_ref
            for ref in raw_grants_pages_page.page_refs:
                allow_futures.append(
                    loop.run_in_executor(
                        self._thread_pool,
                        partial(
                            _executor_authorize_allow_ref,
                            storage_backend=self._storage_backend,
                            raw_grants_kwargs={
                                "effect": GrantEffect.ALLOW,
                                "resource_type": resource_type,
                                "action": action,
                                "page_size": page_size,
                                "page_ref": ref
                            },
                            jmespath_data=jmespath_data,
                            cancel_event=cancel_event,
                            allow_match_event=allow_match_event
                        )
                    )
                )

        if cancel_event['set'] is True:
            await self._cleanup_futures(futures=deny_futures + allow_futures)

            return False
        
        elif len(deny_futures) > 0:
            await asyncio.gather(*deny_futures)
            if cancel_event['set'] is True:
                await self._cleanup_futures(futures=allow_futures)

                return False
        
        if allow_match_event['set'] is True:
            await self._cleanup_futures(allow_futures)

            return True

        elif len(allow_futures) > 0:
            await asyncio.gather(*allow_futures)
            if allow_match_event['set'] is True:
                return True
        
        return False


    async def authorize_many(
        self, 
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        """ 
        results = {i: None for i in range(len(jmespath_data_entries))}
        loop = get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            raw_grants_page = await self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            deny_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    partial(
                        _executor_authorize_many,
                        storage_backend=self._storage_backend,
                        raw_grants_page=raw_grants_page,
                        jmespath_data_entries=jmespath_data_entries
                    )
                )
            )
        
        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            raw_grants_page = await self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            allow_futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    partial(
                        _executor_authorize_many,
                        storage_backend=self._storage_backend,
                        raw_grants_page=raw_grants_page,
                        jmespath_data_entries=jmespath_data_entries
                    )
                )
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
    

    async def _authorize_many_parallel_paging(
        self, 
        resource_type: Type[BaseModel],
        action: ResourceAction,
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
        """ 
        results = {i: None for i in range(len(jmespath_data_entries))}
        loop = get_running_loop()
        deny_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            page_refs = await self._storage_backend.get_page_ref_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            for ref in page_refs.page_refs:
                deny_futures.append(
                    loop.run_in_executor(
                        self._thread_pool,
                        partial(
                            _executor_authorize_many_ref,
                            storage_backend=self._storage_backend,
                            raw_grants_kwargs = {
                                "effect": GrantEffect.DENY,
                                "resource_type": resource_type,
                                "action": action,
                                "page_size": page_size,
                                "page_ref": ref
                            },
                            jmespath_data_entries=jmespath_data_entries
                        )
                    )
                )
        
        allow_futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        while (
            did_once is not True
            or next_page_ref is not None
        ):
            did_once = True
            page_refs = await self._storage_backend.get_page_ref_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            for ref in page_refs.page_refs:
                allow_futures.append(
                    loop.run_in_executor(
                        self._thread_pool,
                        partial(
                            _executor_authorize_many_ref,
                            storage_backend=self._storage_backend,
                            raw_grants_kwargs = {
                                "effect": GrantEffect.ALLOW,
                                "resource_type": resource_type,
                                "action": action,
                                "page_size": page_size,
                                "page_ref": ref
                            },
                            jmespath_data_entries=jmespath_data_entries
                        )
                    )
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

        This will send a page of grants to each worker and return the results.

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
        """
        loop = get_running_loop()
        futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        worker_num = 0
        while (
            (
                worker_num < self._max_workers
                and next_page_ref is not None
            )
            or did_once is not True
        ):
            worker_num += 1
            did_once = True
            raw_grants_page = await self._storage_backend.get_raw_grants_page(
                effect=effect,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                page_ref=next_page_ref
            )
            futures.append(
                loop.run_in_executor(
                    self._thread_pool,
                    partial(
                        _executor_matching_grants,
                        storage_backend=self._storage_backend,
                        raw_grants_page=raw_grants_page,
                        jmespath_data=jmespath_data
                    )
                )
            )

        results = await asyncio.gather(*futures)
        
        return GrantsPage(
            grants=[grant for grants_list in results for grant in grants_list],
            next_page_ref=page_ref
        )
    

    async def _get_matching_grants_page_parallel_paging(
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

        This will send a page of grants to each worker and return the results.

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
        """
        loop = get_running_loop()
        futures: List[asyncio.Future] = []
        next_page_ref = None
        did_once = False
        worker_num = 0
        while (
            (
                worker_num < self._max_workers
                and next_page_ref is not None
            )
            or did_once is not True
        ):
            worker_num += 1
            did_once = True
            page_refs_page = await self._storage_backend.get_page_ref_page(
                effect=effect,
                resource_type=resource_type,
                action=action,
                page_size=page_size,
                refs_page_size=self._max_workers, # try to get the number of worker refs
                page_ref=page_ref
            )
            for ref in page_refs_page.page_refs:
                worker_num += 1
                futures.append(
                    loop.run_in_executor(
                        self._thread_pool,
                        partial(
                            _executor_matching_grants_ref,
                            storage_backend=self._storage_backend,
                            raw_grants_kwargs={
                                "effect": effect,
                                "resource_type": resource_type,
                                "action": action,
                                "page_size": page_size,
                                "page_ref": ref
                            },
                            jmespath_data=jmespath_data
                        )
                    )
                )

        results = await asyncio.gather(*futures)
        
        return GrantsPage(
            grants=[grant for grants_list in results for grant in grants_list],
            next_page_ref=page_ref
        )
        

    async def _cleanup_futures(self, futures: List[asyncio.Future]) -> None:
        gather_futures: List[asyncio.Future] = []
        for future in futures:
            if future.cancel() is False:
                gather_futures.append(future)
        
        await asyncio.gather(*gather_futures)


def _executor_init(jmespath_options: jmespath.Options) -> None:
    # each thread must get it's own copy of jmespath options and be able to retrieve it
    thread_var_name = f"authzee_jmespath_options_t_{threading.get_ident()}"
    globals()[thread_var_name] = deepcopy(jmespath_options)


def _executor_authorize_deny(
    storage_backend: StorageBackend,
    raw_grants_page: RawGrantsPage,
    jmespath_data: Dict[str, Any],
    cancel_event: Dict[str, bool]
) -> bool:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )
    # Make  deep copy since this a pointer and shared among threads, to avoid race conditions around context
    j_data = deepcopy(jmespath_data)
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=j_data,
            jmespath_options=jmespath_options
        ) is True:
            cancel_event['set'] = True

            return True
        
        if cancel_event['set'] is True:
            return False
    
    return False


def _executor_authorize_deny_ref(
    storage_backend: StorageBackend,
    raw_grants_kwargs: Dict[str, Any],
    jmespath_data: Dict[str, Any],
    cancel_event: Dict[str, bool]
) -> bool:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    raw_grants_page = asyncio.run(
        storage_backend.get_raw_grants_page(**raw_grants_kwargs)
    )
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )   
    j_data = deepcopy(jmespath_data)
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=j_data,
            jmespath_options=jmespath_options
        ) is True:
            cancel_event['set'] = True

            return True
        
        if cancel_event['set'] is True:
            return False
    
    return False


def _executor_authorize_allow(
    storage_backend: StorageBackend,
    raw_grants_page: RawGrantsPage,
    jmespath_data: Dict[str, Any],
    cancel_event: Dict[str, bool],
    allow_match_event: Dict[str, bool]
) -> bool:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )
    j_data = deepcopy(jmespath_data)
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=j_data,
            jmespath_options=jmespath_options
        ) is True:
            allow_match_event['set'] = True

            return True
        
        if (
            cancel_event['set'] is True
            or allow_match_event['set'] is True
        ):
            return False
    
    return False


def _executor_authorize_allow_ref(
    storage_backend: StorageBackend,
    raw_grants_kwargs: Dict[str, Any],
    jmespath_data: Dict[str, Any],
    cancel_event: Dict[str, bool],
    allow_match_event: Dict[str, bool]
) -> bool:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    raw_grants_page = asyncio.run(
        storage_backend.get_raw_grants_page(**raw_grants_kwargs)
    )
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )  
    j_data = deepcopy(jmespath_data)
    for grant in grants_page.grants:
        if gc.grant_matches(
            grant=grant,
            jmespath_data=j_data,
            jmespath_options=jmespath_options
        ) is True:
            allow_match_event['set'] = True

            return True
        
        if (
            cancel_event['set'] is True
            or allow_match_event['set'] is True
        ):
            return False
    
    return False


def _executor_authorize_many(
    storage_backend: StorageBackend,
    raw_grants_page: RawGrantsPage,
    jmespath_data_entries: List[Dict[str, Any]]
) -> List[bool]:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )

    return gc.authorize_many_grants(
        grants_page=grants_page,
        jmespath_data_entries=deepcopy(jmespath_data_entries),
        jmespath_options=jmespath_options
    )


def _executor_authorize_many_ref(
    storage_backend: StorageBackend,
    raw_grants_kwargs: Dict[str, Any],
    jmespath_data_entries: List[Dict[str, Any]]
) -> List[bool]:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    raw_grants_page = asyncio.run(
        storage_backend.get_raw_grants_page(**raw_grants_kwargs)
    )
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )

    return gc.authorize_many_grants(
        grants_page=grants_page,
        jmespath_data_entries=deepcopy(jmespath_data_entries),
        jmespath_options=jmespath_options
    )


def _executor_matching_grants(
    storage_backend: StorageBackend,
    raw_grants_page: RawGrantsPage,
    jmespath_data: Dict[str, Any]
) -> List[Grant]:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )

    return gc.compute_matching_grants(
        grants_page=grants_page,
        jmespath_data=deepcopy(jmespath_data),
        jmespath_options=jmespath_options
    )


def _executor_matching_grants_ref(
    storage_backend: StorageBackend,
    raw_grants_kwargs: Dict[str, Any],
    jmespath_data: Dict[str, Any]
) -> List[Grant]:
    options_var = f"authzee_jmespath_options_t_{threading.get_ident()}"
    jmespath_options = globals()[options_var]
    raw_grants_page = asyncio.run(
        storage_backend.get_raw_grants_page(**raw_grants_kwargs)
    )
    grants_page = asyncio.run(
        storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
    )

    return gc.compute_matching_grants(
        grants_page=grants_page,
        jmespath_data=deepcopy(jmespath_data),
        jmespath_options=jmespath_options
    )
