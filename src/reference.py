"""A reference implementation for the Authzee specification.

Core workflow:

1. Context, identity, and resource definitions are created to limit inputs.
2. Definitions are validated with their respective function: ``validate_context_defs``, ``validate_identity_defs``, and ``validate_resource_defs``
3. Grants are created to allow or deny actions on resources.
4. Grants are validated with the ``validate_grants`` function.
5. Requests or batch requests are created to perform Authzee operations.
6. Request are individually validated with the ``validate_request`` and batch requests with the ``validate_batch_request`` functions.
7. An operation is ran on the request or batch request.
    - audit - List grants that evaluate to a match for the request
    - authorize - Evaluate grants to determine if a request is authorized
    - batch_audit - audit but on a batch with the same resource_action
    - batch_authorize - authorize but on a batch with the same resource_action
"""

__all__ = [
    "audit",
    "audit_result_schema",
    "audit_workflow",
    "authorize",
    "authorize_result_schema",
    "authorize_workflow",
    "batch_audit",
    "batch_audit_result_schema",
    "batch_audit_workflow",
    "batch_authorize",
    "batch_authorize_result_schema",
    "batch_authorize_workflow",
    "batch_request_schema",
    "context_definition_schema",
    "evaluate_one",
    "evaluate_one_result_schema",
    "general_result_schema",
    "generic_error_schema",
    "grant_schema",
    "identity_definition_schema",
    "query_execute_result_schema",
    "request_schema",
    "resource_definition_schema",
    "validate_batch_request",
    "validate_batch_request_result_schema",
    "validate_context_defs",
    "validate_grants",
    "validate_identity_defs",
    "validate_request",
    "validate_request_result_schema",
    "validate_resource_defs"
]
from typing import Callable, Dict, List, Union

import jsonschema
import jsonschema.exceptions


AnyJSON = Union[
    bool,
    str,
    int,
    float,
    None,
    list,
    dict
]

_type_regex = "^[A-Za-z0-9_]*$"
_type_schema = {
    "title": "Authzee Type",
    "description": "A unique name to identity this type.",
    "type": "string",
    "pattern": _type_regex,
    "minLength": 1,
    "maxLength": 256
}
_action_schema = {
    "title": "Resource Action",
    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
    "type": "string",
    "pattern": "^[A-Za-z0-9_.:-]*$",
    "minLength": 1,
    "maxLength": 512
}
_schema_schema = jsonschema.Draft202012Validator.META_SCHEMA

_context_type_schema = (
    _type_schema
    | {
        "title": "Authzee Context Type",
        "description": "A unique name to identity this context type."
    }
)
_identity_type_schema = (
    _type_schema
    | {
        "title": "Authzee Identity Type",
        "description": "A unique name to identity this identity type."
    }
)
_resource_type_schema = (
    _type_schema
    | {
        "title": "Authzee Resource Type",
        "description": "A unique name to identity this resource type."
    }
)

context_definition_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Context Definition",
    "description": "A request context definition.  Defines a type of context that can be passed with Authzee requests.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "context_type",
        "schema"
    ],
    "properties": {
        "context_type": _context_type_schema,
        "schema": _schema_schema
    }
}
identity_definition_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Identity Definition",
    "description": "An identity definition.  Defines a type of identity to use with Authzee.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "identity_type",
        "schema"
    ],
    "properties": {
        "identity_type": _identity_type_schema,
        "schema": _schema_schema
    }
}
resource_definition_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Resource Definition",
    "description": "A resource definition.  Defines a type of resource to use with Authzee.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "resource_type",
        "actions",
        "schema"
    ],
    "properties": {
        "resource_type": _resource_type_schema,
        "actions": {
            "type": "array",
            "uniqueItems": True,
            "items": _action_schema
        },
        "schema": _schema_schema
    }
}

grant_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Grant",
    "description": "A grant is an object representing enacted authorization rules.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "effect",
        "actions",
        "data",
        "query",
        "equality",
        "applicable_on_failure"
    ],
    "properties": {
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": (
                "Any applicable deny grant will always cause the request to be unauthorized. "
                "If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. "
                "If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
            )
        },
        "actions": {
            "type": "array",
            "uniqueItems": True,
            "items": _action_schema,
            "description": "List of actions this grant applies to or null to match any resource action."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "query": {
            "type": "string",
            "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
        },
        "equality": {
            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
        },
        "applicable_on_failure": {
            "type": "boolean",
            "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
        }
    }
}
generic_error_schema = {
    "title": "Operation Error",
    "description": "Error from an Authzee operation, or null if no error.",
    "type": [
        "object",
        "null"
    ],
    "required": [
        "error_type",
        "message"
    ],
    "properties": {
        "error_type": {
            "type": "string",
            "description": "The type of error."
        },
        "message": {
            "type": "string",
            "description": "Message describing the error."
        }
    }
}
general_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "General Result",
    "description": "General result, where no distinct return value is needed.  Only passes on if there was an error or not. ",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "error"
    ],
    "properties": {
        "error": generic_error_schema
    }
}

_request_identities_schema = {
    "description": "Object whose keys are the identity types, and values are an array of instances of that identity type.",
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "patternProperties": {
        _type_regex: {
            "type": "array",
            "items": {
                "type": "object"
            }
        }
    }
}
_request_resource_schema = {
    "type": "object",
    "description": "Resource for the request that is an instance of the given resource_type."
}
_request_context_schema = {
    "type": "object",
    "description": "Context for the request that is an instance of the given context_type."
}
request_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authzee Operation Request",
    "description": "Request for an Authzee Operation.",
    "additionalProperties": False,
    "required": [
        "identities",
        "action",
        "resource_type",
        "resource",
        "context_type",
        "context"
    ],
    "properties": {
        "identities": _request_identities_schema,
        "action": _action_schema,
        "resource_type": _resource_type_schema,
        "resource": _request_resource_schema,
        "context_type": _context_type_schema,
        "context": _request_context_schema
    }
}
_query_result_schema = {
    "description": "Result from running the JSON query in the grant."
}
query_execute_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Result for a JSON query execute function",
    "description": "Result from evaluating a JSON query against the given input data.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "result",
        "failure"
    ],
    "properties": {
        "result": _query_result_schema,
        "failure": {
            "type": [
                "string",
                "null"
            ],
            "description": "A message describing why the query execution failed, or null if no failure occurred."
        }
    }
}
_is_applicable_schema = {
    "type": "boolean",
    "description": "If the grant is applicable to the request or not."
}
evaluate_one_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Evaluate One Result",
    "description": "Result from evaluating one grant against a request.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_applicable",
        "query_result",
        "failure"
    ],
    "properties": {
        "is_applicable": _is_applicable_schema,
        "query_result": _query_result_schema,
        "failure": {
            "type": [
                "string",
                "null"
            ],
            "description": "A message describing why the evaluation failed, or null if no failure occurred. Evaluation failures do not cause the operation to fail."
        }
    }
}
audit_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Audit Result",
    "description": "Result for the audit operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "results",
        "error"
    ],
    "properties": {
        "results": {
            "type": "array",
            "description": "List of grant evaluation results.",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "required": [
                    "grant",
                    "is_applicable",
                    "query_result",
                    "failure"
                ],
                "properties": {
                    "grant": grant_schema,
                    "is_applicable": _is_applicable_schema,
                    "query_result": _query_result_schema,
                    "failure": {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": "A message describing why the evaluation failed, or null if no failure occurred."
                    }
                }
            }
        },
        "error": generic_error_schema
    }
}
authorize_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authorize Result",
    "description": "Result for the authorize operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "is_authorized",
        "grant",
        "message",
        "error"
    ],
    "properties": {
        "is_authorized": {
            "type": "boolean",
            "description": "true if the request is authorized.  false if it is not authorized."
        },
        "grant": {
            "description": "Grant that was responsible for the authorization decision, if applicable.",
            "anyOf": [
                {
                    "type": "null",
                    "description": "No grant was involved in the authorization decision."
                },
                grant_schema
            ]
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not.",
            "enum": [
                "An error has occurred. Therefore, the request is not authorized.",
                "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized."
            ]
        },
        "error": generic_error_schema
    }
}

_request_level_description = " Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value."
_batch_item_level_description = " Overrides the batch request level if the field exists and is not null."
batch_request_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Operation Request",
    "description": "Request for an Authzee Batch Operation.",
    "additionalProperties": True,
    "required": [
        "identities",
        "action",
        "resource_type",
        "resource",
        "context_type",
        "context",
        "batch"
    ],
    "properties": {
        "identities": _request_identities_schema | {
            "description": _request_identities_schema['description'] + _request_level_description
        },
        "action": _action_schema,
        "resource_type": _resource_type_schema | {
            "description": _resource_type_schema['description'] + _request_level_description
        },
        "resource": _request_resource_schema | {
            "description": _request_resource_schema['description'] + _request_level_description
        },
        "context_type": _context_type_schema,
        "context": _request_context_schema | {
            "description": _request_context_schema['description'] + _request_level_description
        },
        "batch": {
            "type": "array",
            "description": "Batch of items to process with shared resource types. When evaluated, each item is merged with the root request, where the batch item fields take precedence.",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [],
                "properties": {
                    "identities": _request_identities_schema | {
                        "type": [
                            "object",
                            "null"
                        ],
                        "description": _request_identities_schema['description'] + _batch_item_level_description
                    },
                    "resource_type": _resource_type_schema | {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": _resource_type_schema['description'] + _batch_item_level_description
                    },
                    "resource": _request_resource_schema | {
                        "description": "Resource for this batch item, that is an instance of the given resource_type. Overrides the batch request level if the field exists and is not null."
                    },
                    "context_type": _context_type_schema | {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": _context_type_schema['description'] + _batch_item_level_description
                    },
                    "context": {
                        "type": [
                            "object",
                            "null"
                        ],
                        "description": "Context for the request that is an instance of context_type." + _batch_item_level_description
                    }
                }
            }
        }
    }
}
validate_request_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Request Validation Result",
    "description": "Request Validation Result schema.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "error"
    ],
    "properties": {
        "error": generic_error_schema
    }
}
validate_batch_request_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch request Validation Result",
    "description": "Batch request Validation Result schema.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "error",
        "batch"
    ],
    "properties": {
        "error": generic_error_schema,
        "batch": {
            "type": "array",
            "description": "Each result corresponds to the batch request item of the same index.",
            "items": generic_error_schema
        }
    }
}
batch_audit_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Audit Result",
    "description": "Result for the Batch Audit Operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "grants",
        "batch",
        "error"
    ],
    "properties": {
        "grants": {
            "type": "array",
            "description": "List of grants that have been processed for the request.",
            "items": grant_schema
        },
        "batch": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "description": "Audit batch item result.",
                "additionalProperties": True,
                "required": [
                    "results",
                    "error"
                ],
                "properties": {
                    "results": {
                        "type": "array",
                        "description": "List of grant evaluation results for each respective grant index.",
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                            "required": [
                                "is_applicable",
                                "query_result",
                                "failure"
                            ],
                            "properties": {
                                "is_applicable": _is_applicable_schema,
                                "query_result": _query_result_schema,
                                "failure": {
                                    "type": [
                                        "string",
                                        "null"
                                    ],
                                    "description": "A message describing why the evaluation failed, or null if no failure occurred."
                                }
                            }
                        }
                    },
                    "error": generic_error_schema
                }
            }
        },
        "error": generic_error_schema
    }
}
batch_authorize_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Authorize Result",
    "description": "Result for the Batch Authorize Operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "batch",
        "error"
    ],
    "properties": {
        "batch": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": authorize_result_schema
        },
        "error": generic_error_schema
    }
}


def validate_context_defs(
    context_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    context_types = set()
    for c_def in context_defs:
        try:
            jsonschema.validate(c_def, context_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Context def is not valid. Schema Error: {exc}'"
                }
            }

        if c_def['context_type'] not in context_types:
            context_types.add(c_def['context_type'])
        else:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Context types must be unique. '{c_def['context_type']}' is present more than once."
                }
            }

        if (
            "type" not in c_def['schema']
            or c_def['schema']['type'] != "object"
        ):
            return {
                "error": {
                    "error_type": "definition",
                    "message": "Context schemas must declare the root type to be an object."
                }
            }

    return {
        "error": None
    }


def validate_identity_defs(
    identity_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    id_types = []
    for id_def in identity_defs:
        try:
            jsonschema.validate(id_def, identity_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Identity definition is not valid. Schema Error: {exc}'"
                }
            }

        if id_def['identity_type'] not in id_types:
            id_types.append(id_def['identity_type'])
        else:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Identity types must be unique. '{id_def['identity_type']}' is present more than once."
                }
            }

        if (
            "type" not in id_def['schema']
            or id_def['schema']['type'] != "object"
        ):
            return {
                "error": {
                    "error_type": "definition",
                    "message": "Identity schemas must declare the root type to be an object."
                }
            }

    return {
        "error": None
    }


def validate_resource_defs(
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    r_types = set()
    for r_def in resource_defs:
        try:
            jsonschema.validate(r_def, resource_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Resource definition is not valid. Schema Error: {exc}"
                }
            }

        if r_def['resource_type'] not in r_types:
            r_types.add(r_def['resource_type'])
        else:
            return {
                "error": {
                    "error_type": "definition",
                    "message": f"Resource types must be unique. '{r_def['resource_type']}' is present more than once."
                }
            }

        if (
            "type" not in r_def['schema']
            or r_def['schema']['type'] != "object"
        ):
            return {
                "error": {
                    "error_type": "definition",
                    "message": "Resource schemas must declare the root type to be an object."
                }
            }

    return {
        "error": None
    }


def validate_grants(grants: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    for g in grants:
        try:
            jsonschema.validate(g, grant_schema)
        except jsonschema.exceptions.ValidationError as exc:
            return {
                "error": {
                    "error_type": "grant",
                    "message": f"The grant is not valid. Schema Error: {exc}"
                }
            }

    return {
        "error": None
    }


def _validate_request_identities(
    identities: Dict[str, AnyJSON],
    identity_lut: dict
) -> str | None:
    for i_type in identities:
        if i_type not in identity_lut:
            return f"Identity Type '{i_type}' is not valid."

        else:
            for identity, i_num in zip(identities[i_type], range(len(identities[i_type]))):
                try:
                    jsonschema.validate(
                        identity,
                        identity_lut[i_type]['schema']
                    )
                except jsonschema.exceptions.ValidationError as exc:
                    return f"Identity '{i_type}[{i_num}]' is not valid. Schema Error: {exc}"

    return None


def _validate_request_resource(
    resource_type: str,
    resource: dict,
    action: str,
    resource_lut: dict
) -> str | None:
    if resource_type not in resource_lut:
        return f"Resource type '{resource_type}' is not valid."

    try:
        jsonschema.validate(
            resource,
            resource_lut[resource_type]['schema']
        )
    except jsonschema.exceptions.ValidationError as exc:
        return f"The request resource is not valid for the '{resource_type}' resource type. Schema Error: {exc}"

    if action not in resource_lut[resource_type]['actions']:
        return f"'{action}' is not a valid action for the '{resource_type}' resource type."

    return None


def _validate_request_context(
    context_type: str,
    context: dict,
    context_lut: dict
) -> str | None:
    if context_type not in context_lut:
        return f"Context type '{context_type}' is not valid."

    try:
        jsonschema.validate(
            context,
            context_lut[context_type]['schema']
        )
    except jsonschema.exceptions.ValidationError as exc:
        return f"The request context is not valid for the '{context_type}' context type. Schema Error: {exc}"

    return None


def validate_request(
    request: Dict[str, AnyJSON],
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    try:
        jsonschema.validate(request, request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "error": {
                "error_type": "request",
                "message": f"The request is not valid. Schema Error: {exc}"
            }
        }

    err = _validate_request_identities(
        identities=request['identities'],
        identity_lut={i['identity_type']: i for i in identity_defs}
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            }
        }

    err = _validate_request_resource(
        resource_type=request['resource_type'],
        resource=request['resource'],
        action=request['action'],
        resource_lut={r['resource_type']: r for r in resource_defs}
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            }
        }

    err = _validate_request_context(
        context_type=request['context_type'],
        context=request['context'],
        context_lut={c['context_type']: c for c in context_defs}
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            }
        }

    return {
        "error": None
    }


def validate_batch_request(
    batch_request: Dict[str, AnyJSON],
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    try:
        jsonschema.validate(batch_request, batch_request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "error": {
                "error_type": "request",
                "message": f"The batch request is not valid. Schema Error: {exc}"
            },
            "batch": []
        }

    identity_lut = {i['identity_type']: i for i in identity_defs}
    resource_lut = {r['resource_type']: r for r in resource_defs}
    context_lut = {c['context_type']: c for c in context_defs}

    err = _validate_request_identities(
        identities=batch_request['identities'],
        identity_lut=identity_lut
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            },
            "batch": []
        }

    err = _validate_request_resource(
        resource_type=batch_request['resource_type'],
        resource=batch_request['resource'],
        action=batch_request['action'],
        resource_lut=resource_lut
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            },
            "batch": []
        }

    err = _validate_request_context(
        context_type=batch_request['context_type'],
        context=batch_request['context'],
        context_lut=context_lut
    )
    if err is not None:
        return {
            "error": {
                "error_type": "request",
                "message": err
            },
            "batch": []
        }

    batch = []
    for item in batch_request['batch']:
        item_err = None
        if (
            item_err is None
            and item.get("identities", None) is not None
        ):
            item_err = _validate_request_identities(
                identities=item['identities'],
                identity_lut=identity_lut
            )

        if item_err is None and (
            item.get("resource_type", None) is not None
            or item.get("resource", None) is not None
        ):
            item_err = _validate_request_resource(
                resource_type=item.get("resource_type", batch_request['resource_type']),
                resource=item.get("resource", batch_request['resource']),
                action=batch_request['action'],
                resource_lut=resource_lut
            )

        if item_err is None and (
            item.get("context_type", None) is not None
            or item.get("context", None) is not None
        ):
            item_err = _validate_request_context(
                context_type=item.get("context_type", batch_request['context_type']),
                context=item.get("context", batch_request['context']),
                context_lut=context_lut
            )

        if item_err is not None:
            batch.append(
                {
                    "error_type": "request",
                    "message": item_err
                }
            )
        else:
            batch.append(None)

    return {
        "error": None,
        "batch": batch
    }


def evaluate_one(
    request: Dict[str, AnyJSON],
    grant: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    result = {
        "is_applicable": False,
        "query_result": None,
        "failure": None
    }
    if (
        len(grant['actions']) > 0
        and request['action'] not in grant['actions']
    ):
        return result

    query_result = execute(
        grant['query'],
        {
            "request": request,
            "grant": grant
        }
    )
    if query_result['failure'] is None:
        result['query_result'] = query_result['result']
        if query_result['result'] == grant['equality']:
            result['is_applicable'] = True

    else:
        result['failure'] = query_result['failure']
        if grant['applicable_on_failure'] is True:
            result['is_applicable'] = True

    return result


def audit(
    request: Dict[str, AnyJSON],
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]:
    result = {
        "results": [],
        "error": None
    }
    for g in grants:
        g_eval = evaluate_one(request, g, execute)
        result['results'].append(
            {
                "grant": g,
                "is_applicable": g_eval['is_applicable'],
                "query_result": g_eval['query_result'],
                "failure": g_eval['failure']
            }
        )

    return result


def authorize(
    request: Dict[str, AnyJSON],
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    allow_grants = []
    deny_grants = []
    for g in grants:
        if g['effect'] == "allow":
            allow_grants.append(g)
        else:
            deny_grants.append(g)

    for g in deny_grants:
        g_eval = evaluate_one(request, g, execute)
        if g_eval['is_applicable'] is True:
            return {
                "is_authorized": False,
                "grant": g,
                "message": "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "error": None
            }

    for g in allow_grants:
        g_eval = evaluate_one(request, g, execute)
        if g_eval['is_applicable'] is True:
            return {
                "is_authorized": True,
                "grant": g,
                "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "error": None
            }

    return {
        "is_authorized": False,
        "grant": None,
        "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
        "error": None
    }


def _validate(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    is_batch: bool
) -> Dict[str, AnyJSON]:
    c_val = validate_context_defs(context_defs)
    if c_val['error'] is not None:
        return c_val

    i_val = validate_identity_defs(identity_defs)
    if i_val['error'] is not None:
        return i_val

    r_val = validate_resource_defs(resource_defs)
    if r_val['error'] is not None:
        return r_val

    g_val = validate_grants(grants)
    if g_val['error'] is not None:
        return g_val

    if is_batch is True:
        req_val = validate_batch_request(
            request,
            context_defs,
            identity_defs,
            resource_defs
        )
        if req_val['error'] is not None:
            return req_val

        return {
            "error": None,
            "batch": req_val['batch']
        }

    req_val = validate_request(
        request,
        context_defs,
        identity_defs,
        resource_defs
    )
    if req_val['error'] is not None:
        return req_val

    return {
        "error": None
    }


def audit_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_defs,
        identity_defs,
        resource_defs,
        grants,
        request,
        False
    )
    if val['error'] is not None:
        return {
            "results": [],
            "error": val['error']
        }

    return audit(request, grants, execute)


def authorize_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_defs,
        identity_defs,
        resource_defs,
        grants,
        request,
        False
    )
    if val['error'] is not None:
        return {
            "is_authorized": False,
            "grant": None,
            "message": "An error has occurred. Therefore, the request is not authorized.",
            "error": val['error']
        }

    return authorize(request, grants, execute)


def batch_audit(
    batch_request: Dict[str, AnyJSON],
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]:
    batch_results = []
    for item in batch_request['batch']:
        request = {
            "identities": item.get("identities") or batch_request['identities'],
            "action": batch_request['action'],
            "resource_type": item.get("resource_type") or batch_request['resource_type'],
            "resource": item.get("resource") or batch_request['resource'],
            "context_type": item.get("context_type") or batch_request['context_type'],
            "context": item.get("context") if item.get("context") is not None else batch_request['context']
        }
        results = []
        for g in grants:
            g_eval = evaluate_one(request, g, execute)
            results.append(
                {
                    "is_applicable": g_eval['is_applicable'],
                    "query_result": g_eval['query_result'],
                    "failure": g_eval['failure']
                }
            )

        batch_results.append(
            {
                "results": results,
                "error": None
            }
        )

    return {
        "grants": grants,
        "batch": batch_results,
        "error": None
    }


def batch_authorize(
    batch_request: Dict[str, AnyJSON],
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]:
    results = []
    for item in batch_request['batch']:
        results.append(
            authorize(
                {
                    "identities": item.get("identities") or batch_request['identities'],
                    "action": batch_request['action'],
                    "resource_type": item.get("resource_type") or batch_request['resource_type'],
                    "resource": item.get("resource") or batch_request['resource'],
                    "context_type": item.get("context_type") or batch_request['context_type'],
                    "context": item.get("context") if item.get("context") is not None else batch_request['context']
                },
                grants,
                execute
            )
        )

    return {
        "batch": results,
        "error": None
    }


def batch_audit_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_defs,
        identity_defs,
        resource_defs,
        grants,
        batch_request,
        True
    )
    if val['error'] is not None:
        return {
            "grants": [],
            "batch": [],
            "error": val['error']
        }

    batch_results = []
    batch = []
    batch_results_indexes = []
    for error, request, i in zip(
        val['batch'],
        batch_request['batch'],
        range(len(val['batch']))
    ):
        if error is None:
            batch_results.append(None)
            batch.append(request)
            batch_results_indexes.append(i)
        else:
            batch_results.append(
                {
                    "results": [],
                    "error": error
                }
            )

    result = batch_audit(batch_request, grants, execute)
    for request, i in zip(result['batch'], batch_results_indexes):
        batch_results[i] = request

    result['batch'] = batch_results

    return result


def batch_authorize_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_defs,
        identity_defs,
        resource_defs,
        grants,
        batch_request,
        True
    )
    if val['error'] is not None:
        return {
            "batch": [],
            "error": val['error']
        }

    batch_results = []
    batch = []
    batch_results_indexes = []
    for error, request, i in zip(
        val['batch'],
        batch_request['batch'],
        range(len(val['batch']))
    ):
        if error is None:
            batch_results.append(None)
            batch.append(request)
            batch_results_indexes.append(i)
        else:
            batch_results.append(
                {
                    "is_authorized": False,
                    "grant": None,
                    "message": "An error has occurred. Therefore, the request is not authorized.",
                    "error": error
                }
            )

    result = batch_authorize(batch_request, grants, execute)
    for request, i in zip(result['batch'], batch_results_indexes):
        batch_results[i] = request

    result['batch'] = batch_results

    return result
