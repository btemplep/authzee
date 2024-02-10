
from typing import Any, Dict, List, Optional, Set, Type

from pydantic import BaseModel

from authzee.backend_locality import BackendLocality
from authzee.compute.compute_backend import ComputeBackend
from authzee.compute import general as gc
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.resource_action import ResourceAction


class MainProcessCompute(ComputeBackend):
    """Process grants directly.

    """

    def __init__(self):
        super().__init__(
            async_enabled=False,
            backend_locality=BackendLocality.MAIN_PROCESS,
            compatible_localities={
                BackendLocality.MAIN_PROCESS,
                BackendLocality.NETWORK,
                BackendLocality.SYSTEM
            }
        )


    def shutdown(self) -> None:
        """Early clean up of compute backend resources.

        NOOP
        """
        pass


    def authorize(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None
    ) -> bool:
        done_pagination = False
        next_page_ref = None
        while done_pagination is False:
            raw_grants_page = self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                resource_action=resource_action,
                page_ref=next_page_ref
            )
            grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
            next_page_ref = grants_page.next_page_ref
            if next_page_ref is None:
                done_pagination = True

            for grant in grants_page.grants:
                grant_match = gc.grant_matches(
                    grant=grant,
                    jmespath_data=jmespath_data,
                    jmespath_options=self._jmespath_options
                )
                if grant_match is True:
                    return False

        done_pagination = False
        next_page_ref = None
        while done_pagination is False:
            raw_grants_page = self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                resource_action=resource_action,
                page_ref=next_page_ref
            )
            grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
            next_page_ref = grants_page.next_page_ref
            if next_page_ref is None:
                done_pagination = True

            for grant in grants_page.grants:
                grant_match = gc.grant_matches(
                    grant=grant,
                    jmespath_data=jmespath_data,
                    jmespath_options=self._jmespath_options
                )
                if grant_match is True:
                    return True
        
        return False


    def authorize_many(
        self, 
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data_entries: List[Dict[str, Any]],
        page_size: Optional[int] = None
    ) -> List[bool]:
        results = {i: None for i in range(len(jmespath_data_entries))}
        done_pagination = False
        next_page_ref = None
        while done_pagination is False:
            raw_grants_page = self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.DENY,
                resource_type=resource_type,
                resource_action=resource_action,
                page_ref=next_page_ref
            )
            grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
            next_page_ref = grants_page.next_page_ref
            if next_page_ref is None:
                done_pagination = True

            for grant in grants_page.grants:
                for i, jmespath_data in zip(results, jmespath_data_entries):
                    grant_match = gc.grant_matches(
                        grant=grant,
                        jmespath_data=jmespath_data,
                        jmespath_options=self._jmespath_options
                    )
                    if grant_match is True:
                        results[i] = False
                        values = list(results.values())
                        if None not in values:
                            return values

        done_pagination = False
        next_page_ref = None
        while done_pagination is False:
            raw_grants_page = self._storage_backend.get_raw_grants_page(
                effect=GrantEffect.ALLOW,
                resource_type=resource_type,
                resource_action=resource_action,
                page_ref=next_page_ref
            )
            grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants_page)
            next_page_ref = grants_page.next_page_ref
            if next_page_ref is None:
                done_pagination = True

            for grant in grants_page.grants:
                for i, jmespath_data in zip(results, jmespath_data_entries):
                    grant_match = gc.grant_matches(
                        grant=grant,
                        jmespath_data=jmespath_data,
                        jmespath_options=self._jmespath_options
                    )
                    if grant_match is True:
                        results[i] = True
                        values = list(results.values())
                        if None not in values:
                            return values
        
        return [val is True for val in list(results.values())]


    def get_matching_grants_page(
        self, 
        effect: GrantEffect,
        resource_type: Type[BaseModel],
        resource_action: ResourceAction,
        jmespath_data: Dict[str, Any],
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> GrantsPage:
        matching_grants = []
        raw_grants = self._storage_backend.get_raw_grants_page(
            effect=effect,
            resource_type=resource_type,
            resource_action=resource_action,
            page_size=page_size,
            page_ref=page_ref
        )
        grants_page = self._storage_backend.normalize_raw_grants_page(raw_grants_page=raw_grants)
        for grant in grants_page.grants:
            grant_match = gc.grant_matches(
                grant=grant,
                jmespath_data=jmespath_data,
                jmespath_options=self._jmespath_options
            )
            if grant_match == True:
                matching_grants.append(grant)
        
        return GrantsPage(
            grants=matching_grants,
            next_page_ref=grants_page.next_page_ref
        )



