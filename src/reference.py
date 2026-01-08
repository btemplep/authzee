"""A reference implementation for the core functionality of Authzee. 

Core workflow:

1. Context, identity, and resource definitions are created to limit inputs.
2. Definitions are validated with their respective function: ``validate_context_definitions``, ``validate_identity_definitions``, and ``validate_resource_definitions``
3. Grants are created to allow or deny actions on resources.
4. Grants are validated with the ``validate_grants`` function.
5. Requests or batch requests are created to perform Authzee operations.
6. Request are individually validated with the ``validate_request`` and batch requests with the ``validate_batch_request`` functions.
7. An operation is ran on the request or batch request.
    - audit - List grants that evaluate to a match for the request
    - authorize - Evaluate grants to determine if a request is authorized
    - batch_audit - audit but on a batch with the same identities, action, resource_type, and context_type
    - batch_authorize - authorize but on a batch with the same identities, action, resource_type, and context_type
"""

__all__ = [
    "context_definition_schema",
    "identity_definition_schema",
    "resource_definition_schema",
    "grant_schema",
    "definition_error_schema",
    "grant_error_schema",
    "query_error_schema",
    "request_error_schema",
    "validate_definitions_result_schema",
    "validate_grants_result_schema",
    "request_schema",
    "validate_request_result_schema",
    "query_execute_result_schema",
    "evaluate_one_result_schema",
    "audit_result_schema",
    "authorize_result_schema",
    "batch_request_schema",
    "validate_batch_request_result_schema",
    "batch_audit_result_schema",
    "batch_authorize_result_schema",
    "validate_context_definitions",
    "validate_identity_definitions",
    "validate_resource_definitions",
    "validate_grants",
    "validate_request",
    "validate_batch_request",
    "evaluate_one",
    "audit",
    "authorize",
    "audit_workflow",
    "authorize_workflow",
    "batch_audit",
    "batch_authorize",
    "batch_audit_workflow",
    "batch_authorize_workflow"
]

from typing import Callable, Dict, List, Union

import jsonschema
import jsonschema.exceptions


AnyJSON = Union[bool, str, int, float, None, list, dict]

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

_context_type_schema = _type_schema | {
    "title": "Authzee Context Type",
    "description": "A unique name to identity this context type."
}
_identity_type_schema = _type_schema | {
    "title": "Authzee Identity Type",
    "description": "A unique name to identity this identity type."
}
_resource_type_schema = _type_schema | {
    "title": "Authzee Resource Type",
    "description": "A unique name to identity this resource type."
}

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
_query_validation_schema = {
    "title": "Grant-Level Query Validation Setting",
    "description": (
        "Grant-level query validation setting. Set how the query errors are treated. "
        "'validate' - Query errors cause the grant to be inapplicable to the request. "
        "'error' - Includes the 'validate' setting checks, and also adds errors to the result. "
        "'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early."
    ),
    "type": "string",
    "enum": [
        "validate",
        "error",
        "critical"
    ]
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
        "query_validation",
        "equality"
    ],
    "properties": {
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": (
                "Any applicable deny grant will always cause the request to be not authorized. "
                "If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. "
                "If there no applicable allow or deny grants, requests are implicitly denied and not authorized."
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
        "query_validation": _query_validation_schema,
        "equality": {
            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
        }
    }
}
_is_critical_schema = {
    "type": "boolean",
    "description": "If this error is critical. Critical errors generally halt further operations."
}
_error_message_schema = {
    "type": "string",
    "description": "Detailed message about what caused the error."
}
definition_error_schema = {
    "title": "Definition Error",
    "description": "Error when an context, identity, or resource definition is not valid.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "is_critical",
        "message",
        "definition_type",
        "definition"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema,
        "definition_type": {
            "type": "string",
            "enum": [
                "context",
                "identity",
                "resource"
            ]
        },
        "definition": {
            "description": "The value that was given as a definition."
        }
    }
}
grant_error_schema = {
    "title": "Grant Error",
    "description": "Error when an grant is not valid.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "is_critical",
        "message",
        "grant"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema,
        "grant": {
            "description": "The value that was given as a grant."
        }
    }
}
query_error_schema = {
    "title": "Query Error",
    "description": "Error when a JSON query fails.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "is_critical",
        "message"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema
    }
}
request_error_schema = {
    "title": "Authzee Operation Request Error",
    "description": "Error when a request is not valid.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "is_critical",
        "message"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema
    }
}
_is_valid_schema = {
    "type": "boolean",
    "description": "If the inputs have been successfully validated or not."
}
validate_definitions_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Definition Validation Result.",
    "description": "Definition validation result.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_valid",
        "errors"
    ],
    "properties": {
        "is_valid": _is_valid_schema,
        "errors": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "definition": {
                    "type": "array",
                    "items": definition_error_schema
                }
            }
        }
    }
}
validate_grants_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Grant Validation Result.",
    "description": "Grant Validation Result.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_valid",
        "errors"
    ],
    "properties": {
         "is_valid": _is_valid_schema,
        "errors": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "grant": {
                    "type": "array",
                    "items": grant_error_schema
                }
            }
        }
    }
}
_request_query_validation_schema = {
    "title": "Request-Level Query Validation Setting",
    "description": "Request-level query validation setting. Overrides " + _query_validation_schema['description'],
    "type": "string",
    "enum": ["grant"] + _query_validation_schema['enum']
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
        "context",
        "query_validation"
    ],
    "properties": {
        "identities": _request_identities_schema,
        "action": _action_schema,
        "resource_type": _resource_type_schema,
        "resource": _request_resource_schema,
        "context_type": _context_type_schema,
        "context": _request_context_schema,
        "query_validation": _request_query_validation_schema
    }
}
validate_request_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Request Validation Result",
    "description": "Request Validation Result schema.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_valid",
        "errors"
    ],
    "properties": {
         "is_valid": _is_valid_schema,
        "errors": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "request": {
                    "type": "array",
                    "items": request_error_schema
                }
            }
        }
    }
}
_operation_errors_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Operation Result Errors",
    "description": "Errors returned from Authzee Operations.",
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {
        "query": {
            "type": "array",
            "items": query_error_schema
        }
    }
}
_has_failed_schema = {
    "type": "boolean",
    "description": "If the request has failed from a critical error or not."
}
_query_result_schema = {
    "description": "Result from running the JSON query."
}
query_execute_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Result for a JSON query execute function",
    "description": "Result from evaluating a JSON query against the given input data.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "result",
        "has_failed",
        "error_message"
    ],
    "properties": {
        "result": _query_result_schema,
        "has_failed": _has_failed_schema,
        "error_message": {
            "type": [
                "string",
                "null"
            ],
            "description": "Details of why the query failed. `null` if there are no errors."
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
        "has_failed",
        "errors"
    ],
    "properties": {
        "is_applicable": _is_applicable_schema,
        "query_result": _query_result_schema,
        "has_failed": _has_failed_schema,
        "errors": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "query": {
                    "type": "array",
                    "items": query_error_schema
                }
            }
        }
    }
}
_audit_grant_list_schema = {
    "type": "array",
    "description": "List of grants that have been processed for the request.",
    "items": grant_schema
}
audit_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Audit Result",
    "description": "Result for the audit operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "grants",
        "results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": _audit_grant_list_schema,
        "results": {
            "type": "array",
            "description": "List of grant evaluation results for each respective grant index.",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "required": [
                    "is_applicable",
                    "query_result",
                    "errors"
                ],
                "properties": {
                    "is_applicable": _is_applicable_schema,
                    "query_result": _query_result_schema,
                    "errors": _operation_errors_schema
                }
            }
        },
        "has_failed": _has_failed_schema,
        "errors": _operation_errors_schema
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
        "has_failed",
        "critical_errors"
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
                "A critical error has occurred. Therefore, the request is not authorized.",
                "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized."
            ]
        },
        "has_failed": _has_failed_schema,
        "critical_errors": _operation_errors_schema
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
        "query_validation",
        "batch"
    ],
    "properties": {
        "identities": _request_identities_schema | {
            "description": _request_identities_schema['description'] + _request_level_description
        },
        "action": _action_schema,
        "resource_type": _resource_type_schema | {
            "description":  _resource_type_schema['description'] + _request_level_description
        },
        "resource": _request_resource_schema | {
            "description":  _request_resource_schema['description'] + _request_level_description
        },
        "context_type": _context_type_schema,
        "context": _request_context_schema | {
            "description": _request_context_schema['description'] + _request_level_description
        },
        "query_validation": _request_query_validation_schema | {
            "description": _request_query_validation_schema['description'] + _request_level_description
        },
        "batch": {
            "type": "array",
            "description": "Batch of resources and contexts to process with shared identities, action, resource type, and context type.",
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
                        "description":  _resource_type_schema['description'] + _batch_item_level_description
                    },
                    "resource": _request_resource_schema | {
                        "description": "Resource for this batch item, that is an instance of the given resource_type"
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
                    },
                    "query_validation": _request_query_validation_schema | {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": _request_query_validation_schema['description'] + _batch_item_level_description
                    }
                }
            }
        }
    }
}
validate_batch_request_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Request Validation Result",
    "description": "Request Validation Result schema.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_valid",
        "errors",
        "batch_errors"
    ],
    "properties": {
        "is_valid": _is_valid_schema,
        "errors": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "request": {
                    "type": "array",
                    "items": request_error_schema
                }
            }
        },
        "batch_errors": {
            "type": "array",
            "description": "Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [],
                "properties": {
                    "request": {
                        "type": "array",
                        "items": request_error_schema
                    }
                }
            }
        }
    }
}
_batch_result_errors_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Result Errors",
    "description": "Errors returned from Authzee Batch requests.",
    "type": "object",
    "additionalProperties": True,
    "required": [],
    "properties": {}
}
_has_failed_batch_schema = {
    "type": "boolean",
    "description": "If the batch request could not be validated and failed or not. "
}
batch_audit_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Audit Result",
    "description": "Result for the Batch Audit Operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "grants",
        "batch_results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": _audit_grant_list_schema,
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "description": "Audit batch item result.",
                "additionalProperties": True,
                "required": [
                    "results",
                    "has_failed",
                    "errors"
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
                                "errors"
                            ],
                            "properties": {
                                "is_applicable": _is_applicable_schema,
                                "query_result": _query_result_schema,
                                "errors": _operation_errors_schema
                            }
                        }
                    },
                    "has_failed": _has_failed_schema,
                    "errors": _operation_errors_schema
                }
            }
        },
        "has_failed": _has_failed_batch_schema,
        "errors": _batch_result_errors_schema
    }
}
batch_authorize_result_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Authorize Result",
    "description": "Result for the Batch Authorize Operation.",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "batch_results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": authorize_result_schema
        },
        "has_failed": _has_failed_batch_schema,
        "errors": _batch_result_errors_schema
    }
}


def validate_context_definitions(context_definitions: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    errors = []
    context_types = set()
    for c_def in context_definitions:
        try:
            jsonschema.validate(c_def, context_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Context definition is not valid. Schema Error: {exc}'",
                    "definition_type": "context",
                    "definition": c_def
                }
            )
            continue

        if c_def['context_type'] not in context_types:
            context_types.add(c_def['context_type'])
        else:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Context types must be unique. '{c_def['context_type']}' is present more than once.",
                    "definition_type": "context",
                    "definition": c_def
                }
            )
        
        if "type" not in c_def['schema'] or c_def['schema']['type'] != "object": 
            errors.append(
                {
                    "is_critical": True,
                    "message": "Context schemas must declare the the root type to be an object.",
                    "definition_type": "context",
                    "definition": c_def
                } 
            )

    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors
    }


def validate_identity_definitions(identity_definitions: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    errors = []
    id_types = []
    for id_def in identity_definitions:
        try:
            jsonschema.validate(id_def, identity_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Identity definition is not valid. Schema Error: {exc}'",
                    "definition_type": "identity",
                    "definition": id_def
                }
            )
            continue

        if id_def['identity_type'] not in id_types:
            id_types.append(id_def['identity_type'])
        else:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Identity types must be unique. '{id_def['identity_type']}' is present more than once.",
                    "definition_type": "identity",
                    "definition": id_def
                }
            )
        
        if "type" not in id_def['schema'] or id_def['schema']['type'] != "object": 
            errors.append(
                {
                    "is_critical": True,
                    "message": "Identity schemas must declare the the root type to be an object.",
                    "definition_type": "identity",
                    "definition": id_def
                } 
            )

    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors
    }


def validate_resource_definitions(resource_definitions: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    errors = []
    r_types = set()
    for r_def in resource_definitions:
        try:
            jsonschema.validate(r_def, resource_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Resource definition is not valid. Schema Error: {exc}",
                    "definition_type": "resource",
                    "definition": r_def
                }
            )
            continue

        if r_def['resource_type'] not in r_types:
            r_types.add(r_def['resource_type'])
        else:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Resource types must be unique. '{r_def['resource_type']}' is present more than once.",
                    "definition_type": "resource",
                    "definition": r_def
                }
            )
        
        if "type" not in r_def['schema'] or r_def['schema']['type'] != "object": 
            errors.append(
                {
                    "is_critical": True,
                    "message": "Resource schemas must declare the the root type to be an object.",
                    "definition_type": "resource",
                    "definition": r_def
                } 
            )
    
    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors
    }


def validate_grants(
    grants: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    actions = set()
    for r_def in resource_definitions:
        for action in r_def['actions']:
            actions.add(action)

    errors = []
    for g in grants:
        try:
            jsonschema.validate(g, grant_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The grant is not valid. Schema Error: {exc}" ,
                    "grant": g
                }
            )
            continue
        
        for action in g['actions']:
            if action not in actions:
                errors.append(
                    {
                        "is_critical": True,
                        "message": f"The '{action}' action is not valid.",
                        "grant": g
                    }
                )
    
    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors
    }

def _validate_request_identities(
    identities: Dict[str, AnyJSON],
    identity_lut: dict,
    errors: list
) -> None:
    for i_type in identities:
        if i_type not in identity_lut:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Identity Type '{i_type}' is not valid."
                }
            )
        else:
            for identity, i_num in zip(identities[i_type], range(len(identities[i_type]))):
                try:
                    jsonschema.validate(identity, identity_lut[i_type]['schema'])
                except jsonschema.exceptions.ValidationError as exc:
                    errors.append(
                        {
                            "is_critical": True,
                            "message": f"Identity '{i_type}[{i_num}]' is not valid. Schema Error: {exc}"
                        }
                    )


def _validate_request_resource(
    resource_type: str,
    resource: dict,
    action: str,
    resource_lut: dict,
    errors: list
) -> None:
    if resource_type not in resource_lut:
        errors.append(
            {
                "is_critical": True,
                "message": f"Resource type '{resource_type}' is not valid."
            }
        )
    else:
        try:
            jsonschema.validate(resource, resource_lut[resource_type]['schema'])
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The request resource is not valid for the '{resource_type}' resource type. Schema Error: {exc}"
                }
            )

        if action not in resource_lut[resource_type]['actions']:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"'{action}' is not a valid action for the '{resource_type}' resource type."
                }
            )

def _validate_request_context(
    context_type: str,
    context: dict,
    context_lut: dict,
    errors: list  
) -> None:
    if context_type not in context_lut:
        errors.append(
            {
                "is_critical": True,
                "message": f"Context type '{context_type}' is not valid."
            }
        )
    else:
        try:
            jsonschema.validate(context, context_lut[context_type]['schema'])
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The request context is not valid for the the '{context_type}' context type. Schema Error: {exc}"
                }
            )
    

def validate_request(
    request: Dict[str, AnyJSON],
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions:List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    try:
        jsonschema.validate(request, request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "is_valid": False,
            "errors" : [
                {
                    "is_critical": True,
                    "message": f"The request is not valid. Schema Error: {exc}"
                }
            ]
        }
       
    errors = []
    _validate_request_identities(
        identities=request['identities'],
        identity_lut={i['identity_type']: i for i in identity_definitions},
        errors=errors
    )
    _validate_request_resource(
        resource_type=request['resource_type'],
        resource=request['resource'],
        action=request['action'],
        resource_lut={r['resource_type']: r for r in resource_definitions},
        errors=errors
    )
    _validate_request_context(
        context_type=request['context_type'],
        context=request['context'],
        context_lut={c['context_type']: c for c in context_definitions},
        errors=errors
    )

    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors
    }


def validate_batch_request(
    batch_request: Dict[str, AnyJSON],
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions:List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    try:
        jsonschema.validate(batch_request, batch_request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "is_valid": False,
            "errors" : [
                {
                    "is_critical": True,
                    "message": f"The batch request is not valid. Schema Error: {exc}"
                }
            ],
            "results": None # return None if we can't validate the schema
        }

    errors = []
    batch_item_errors = [[] for _ in batch_request['batch']]
    identity_lut = {i['identity_type']: i for i in identity_definitions}
    resource_lut = {r['resource_type']: r for r in resource_definitions}
    context_lut = {c['context_type']: c for c in context_definitions}
    _validate_request_identities(
        identities=batch_request['identities'],
        identity_lut=identity_lut,
        errors=errors
    )
    _validate_request_resource(
        resource_type=batch_request['resource_type'],
        resource=batch_request['resource'],
        action=batch_request['action'],
        resource_lut=resource_lut,
        errors=errors
    )
    _validate_request_context(
        context_type=batch_request['context_type'],
        context=batch_request['context'],
        context_lut=context_lut,
        errors=errors
    )
    for item, bi_errors in zip(batch_request['batch'], batch_item_errors):
        if item.get("identities", None) is not None:
            _validate_request_identities(
                identities=item['identities'],
                identity_lut=identity_lut,
                errors=bi_errors
            )
        
        if (
            item.get("resource_type", None) is not None 
            or item.get("resource", None) is not None
        ):
            _validate_request_resource(
                resource_type=item.get("resource_type", batch_request['resource_type']),
                resource=item.get("resource", batch_request['resource']),
                action=batch_request['action'],
                resource_lut=resource_lut,
                errors=bi_errors
            )

        if (
            item.get("context_type", None) is not None 
            or item.get("context", None) is not None
        ):
            _validate_request_context(
                context_type=item.get("context_type", batch_request['context_type']),
                context=item.get("context", batch_request['context_type']),
                context_lut=context_lut,
                errors=bi_errors
            )
    
    return {
        "is_valid": True if len(errors) == 0 else False,
        "errors": errors,
        "batch_errors": [{"request": errors} for errors in batch_item_errors]
    }


def evaluate_one(
    request: Dict[str, AnyJSON], 
    grant: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON],
    only_crits: bool
) -> Dict[str, AnyJSON]:
    result = {
        "is_applicable": False,
        "query_result": None,
        "has_failed": False,
        "errors": {}
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
    if query_result['has_failed'] is False:
        result['query_result'] = query_result['result']
        if query_result['result'] == grant['equality']:
            result['is_applicable'] = True
    else:
        q_val = grant['query_validation'] if request['query_validation'] == "grant" else request['query_validation']
        is_q_val_crit = q_val == "critical"
        if (
            (
                q_val == "error"
                and only_crits is False
            )
            or is_q_val_crit is True
        ):
            result['errors']['query'] = [
                {
                    "is_critical": is_q_val_crit,
                    "message": f"A JSON Query error has occurred: {query_result['error_message']}."
                }
            ]
            if is_q_val_crit is True:
                result['has_failed'] = True

    return result


def audit(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
    result = {
        "grants": grants,
        "results": [],
        "has_failed": False,
        "errors": {}
    }
    for g in grants:
        g_eval = evaluate_one(request, g, execute, False)
        result['results'].append(
            {
                "is_applicable": g_eval['is_applicable'],
                "query_result": g_eval['query_result'],
                "errors": g_eval['errors']
            }
        )
        if g_eval['has_failed'] is True:
            result['has_failed'] = True
            result['errors'] = {
                "query": [
                    {
                        "is_critical": True,
                        "message": "A critical error occurred when processing the last returned result."
                    }
                ]
            }

            return result 

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
        g_eval = evaluate_one(request, g, execute, True)
        if g_eval['has_failed'] is True:
            return {
                "is_authorized": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "has_failed": True,
                "critical_errors":g_eval['errors']
            }
        
        if g_eval['is_applicable'] is True:
            return {
                "is_authorized": False,
                "grant": g,
                "message": "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "has_failed": False,
                "critical_errors": {}
            }
    
    for g in allow_grants:
        g_eval = evaluate_one(request, g, execute, True)
        if g_eval['has_failed'] is True:
            return {
                "is_authorized": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "has_failed": True,
                "critical_errors": g_eval['errors']
            }
        
        if g_eval['is_applicable'] is True:
            return {
                "is_authorized": True,
                "grant": g,
                "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "has_failed": False,
                "critical_errors": {}
            }
    
    return {
        "is_authorized": False,
        "grant": None,
        "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
        "has_failed": False,
        "critical_errors": {}
    }


def _validate(
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    is_batch: bool
) -> Dict[str, AnyJSON]:
    c_val = validate_context_definitions(context_definitions)
    if c_val['is_valid'] is False:
        return c_val
    
    i_val = validate_identity_definitions(identity_definitions)
    if i_val['is_valid'] is False:
        return i_val
    
    r_val = validate_resource_definitions(resource_definitions)
    if r_val['is_valid'] is False:
        return r_val

    g_val = validate_grants(grants, resource_definitions)
    if g_val['is_valid'] is False:
        return g_val
    
    if is_batch is True:
        req_val = validate_batch_request(
            request,
            context_definitions,
            identity_definitions,
            resource_definitions
        )
    else:
        req_val = validate_request(
            request,
            context_definitions,
            identity_definitions,
            resource_definitions
        )

    if req_val['is_valid'] is False:
        return req_val
    
    return {
        "is_valid": True
    }


def audit_workflow(
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_definitions,
        identity_definitions,
        resource_definitions,
        grants,
        request,
        False
    )
    if val['is_valid'] is False:
        return val

    return audit(request, grants, execute)


def authorize_workflow(
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_definitions,
        identity_definitions,
        resource_definitions,
        grants,
        request,
        False
    )
    if val['is_valid'] is False:
        return val

    return authorize(request, grants, execute)


def batch_audit(
    batch_request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
    batch_results = []
    for item in batch_request['batch']:
        audit_result = audit(
            {
                "identities": item.get("identities", batch_request['identities']),
                "action": batch_request['action'],
                "resource_type": item.get("resource_type", batch_request['resource_type']),
                "resource": item.get("resource", batch_request['resource']),
                "context_type": item.get("context_type", batch_request['context_type']),
                "context": item.get("context", batch_request['context']),
                "query_validation": item.get("query_validation", batch_request['query_validation'])
            },
            grants,
            execute
        )
        audit_result.pop("grants")
        batch_results.append(audit_result)
    
    return {
        "grants": grants,
        "batch_results": batch_results,
        "has_failed": False,
        "errors": {}
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
                    "identities": item.get("identities", batch_request['identities']),
                    "action": batch_request['action'],
                    "resource_type": item.get("resource_type", batch_request['resource_type']),
                    "resource": item.get("resource", batch_request['resource']),
                    "context_type": item.get("context_type", batch_request['context_type']),
                    "context": item.get("context", batch_request['context']),
                    "query_validation": item.get("query_validation", batch_request['query_validation'])
                },
                grants,
                execute
            )
        )
    
    return {
        "results": results,
        "has_failed": False,
        "errors": {}
    }


def batch_audit_workflow(
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_definitions,
        identity_definitions,
        resource_definitions,
        grants,
        batch_request,
        True
    )
    if val['is_valid'] is False:
        return val

    return batch_audit(batch_request, grants, execute)


def batch_authorize_workflow(
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    val = _validate(
        context_definitions,
        identity_definitions,
        resource_definitions,
        grants,
        batch_request,
        True
    )
    if val['is_valid'] is False:
        return val

    return batch_authorize(batch_request, grants, execute)