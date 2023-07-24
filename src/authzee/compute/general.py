
import multiprocessing
import threading
from typing import Any, Dict, List, Union

import jmespath
from loguru import logger

from authzee.grant import Grant
from authzee.grants_page import GrantsPage


def grant_matches(
    grant: Grant,
    jmespath_data: Dict[str, Any],
    jmespath_options: jmespath.Options
) -> bool:
    import json
    logger.debug("JMESPath Data: {}".format(json.dumps(jmespath_data, indent=4)))
    logger.debug("JMESPath Expression: {}".format(grant.jmespath_expression))
    try:
        result = jmespath.search(
            grant.jmespath_expression, 
            jmespath_data, 
            options=jmespath_options
        )
        logger.debug("JMESPath Expression Value: {}".format(result))
    except jmespath.exceptions.JMESPathError as error:
        logger.debug("JMESPath Search error: {}".format(error))
        return False

    logger.debug("JMESPath result == result_match: {}".format(result == grant.result_match))

    return result == grant.result_match


def authorize_grants(
    grants_page: GrantsPage, 
    jmespath_data: Dict[str, Any], 
    jmespath_options: jmespath.Options,
    match_event: Union[
        threading.Event,
        multiprocessing.Event
    ],
    cancel_event: Union[
        threading.Event,
        multiprocessing.Event
    ]
) -> bool:
    for grant in grants_page.grants:
        if (
            match_event.is_set() is True
            or cancel_event.is_set() is True
        ):
            return False

        grant_match = grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=jmespath_options
        )
        if grant_match is True:
            match_event.set()

            return True

    return False


def authorize_many_grants(
    grants_page: GrantsPage, 
    jmespath_data_entries: List[Dict[str, Any]], 
    jmespath_options: jmespath.Options
) -> List[Union[bool, None]]:
    results = {i: None for i in range(len(jmespath_data_entries))}
    for grant in grants_page.grants:        
        for i, jmespath_data in zip(results, jmespath_data_entries):
            grant_match = grant_matches(
                grant=grant,
                jmespath_data=jmespath_data,
                jmespath_options=jmespath_options
            )
            if grant_match is True:
                results[i] = True

    return list(results.values())


def compute_matching_grants(
    grants_page: GrantsPage, 
    jmespath_data: Dict[str, Any], 
    jmespath_options: jmespath.Options
) -> List[Grant]:
    matching_grants: List[Grant] = []
    for grant in grants_page.grants:
        grant_match = grant_matches(
            grant=grant,
            jmespath_data=jmespath_data,
            jmespath_options=jmespath_options
        )
        if grant_match is True:
            matching_grants.append(grant)

    return matching_grants
 
