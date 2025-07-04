"""A reference implementation for the core functionality of Authzee. 

Core workflow:

1. A user creates identity and resource definitions
2. Validate definitions with ``validate_definitions()``.  If any errors are returned, return with those errors immediately.
3. Generate JSON Schemas based on definitions with  ``generate_schemas()``.  If any errors are returned, return with those errors immediately.
4. User can customize the schemas at this point
    - Should only really update request schema and can add additional controls like minimum number of a specific identity
5. User Create grants to allow or deny actions on resources
6. Validate grants with ``validate_grants()``.  If any errors are returned, return with those errors immediately.
7. User creates a request.
8. Validate request with ``validate_request()``.  If any errors are returned, return with those errors immediately.
9. Run authorize() or evaluate() with the the previously validated grants and request. 

For reference of the complete work
"""

__all__ = [
    "identity_definition_schema",
    "resource_definition_schema",
    "validate_definitions",
    "validate_grants",
    "authorize",
    "evaluate",
    "evaluate_workflow",
    "authorize_workflow"
]

import copy
import json
from typing import Callable, Dict, List, Literal, Union

import jmespath
import jmespath.exceptions
import jsonschema
import jsonschema.exceptions


AnyJSON = Union[bool, str, int, float, None, list, dict]
_any_types = ["array", "boolean", "integer", "null", "number", "object", "string"]
_type_schema = {
    "title": "Authzee Type",
    "description": "A unique name to identity this type.",
    "type": "string",
    "pattern": "^[A-Za-z0-9_]*$",
    "minLength": 1,
    "maxLength": 256
}
_action_schema = {
    "title": "Resource Action",
    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
    "type": "string",
    "pattern": "^[A-Za-z0-9_.:-]*$",
    "minLength": 1,
    "maxLength": 512
}
_schema_schema = jsonschema.Draft202012Validator.META_SCHEMA

identity_definition_schema = {
    "title": "Identity Definition",
    "description": "An identity definition.  Defines a type of identity to use with Authzee.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "identity_type",
        "schema"
    ],
    "properties": {
        "identity_type": _type_schema,
        "schema": _schema_schema
    }
}
resource_definition_schema = {
    "title": "Resource Definition",
    "description": "An resource definition.  Defines a type of resource to use with Authzee.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "resource_type",
        "actions",
        "schema",
        "parent_types",
        "child_types"
    ],
    "properties": {
        "resource_type": _type_schema,
        "actions": {
            "type": "array",
            "uniqueItems": True,
            "items": _action_schema
        },
        "schema": _schema_schema,
        "parent_types": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            },
            "description": "Types that are a parent of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        },
        "child_types": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            },
            "description": "Types that are a child of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        }
    }
}
_grant_base_schema = {
    "title": "Grant",
    "description": "A grant is an object representing a enacted authorization rule.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "effect",
        "actions",
        "query",
        "query_validation",
        "equality",
        "data",
        "context_schema",
        "context_validation"
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
        "query": {
            "type": "string",
            "description": "JMESPath query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
        },
        "query_validation": {
            "type": "string",
            "description": (
                "Set how the query errors are treated. "
                "'validate' - Query errors cause the grant to be inapplicable to the request.  "
                "'error' - Includes the 'validate' setting checks, and also adds errors to the result.  "
                "'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early."
            ),
            "enum": [
                "validate",
                "error",
                "critical"
            ]
        },
        "equality": {
            "type": _any_types,
            "description": "Expected value for they query to return.  If the query result matches this value the grant is a considered applicable to the request."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "context_schema": _schema_schema, # schema for a schema must be of type object at a base
        "context_validation": {
            "type": "string",
            "description": (
                "Set how the request context is validated against the grant context schema.  "
                "'none' - there is no validation.  "
                "'validate' - Context is validated and if the context is invalid, the grant is not applicable to the request.  "
                "'error' - Includes the 'validate' setting checks, and also adds errors to the result.  "
                "'critical' Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early."
            ),
            "enum": [
                "none",
                "validate",
                "error",
                "critical"
            ]
        }
    }
}
_context_error_base_schema = {
    "title": "Context Error",
    "description": "Error when the request context is not valid against the expected context for the grant.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message",
        "critical",
        "grant"
    ],
    "properties": {
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "critical": {
            "type": "boolean",
            "description": "If this error caused the the workflow to exit early."
        },
        "grant": {
            "$ref": "#/$defs/grant"
        }
    }
}
_definition_error_base_schema = {
    "title": "Definition Error",
    "description": "Error when an identity or resource definition is not valid.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message",
        "critical",
        "definition_type",
        "definition"
    ],
    "properties": {
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "critical": {
            "type": "boolean",
            "description": "If this error caused the the workflow to exit early."
        },
        "definition_type": {
            "type": "string",
            "enum": [
                "identity",
                "resource"
            ]
        },
        "definition": {
            "type": _any_types
        }
    }
}
_grant_error_base_schema = {
    "title": "Grant Error",
    "description": "Error when an grant is not valid.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message",
        "critical",
        "grant"
    ],
    "properties": {
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "critical": {
            "type": "boolean",
            "description": "If this error caused the the workflow to exit early."
        },
        "grant": {
            "type": _any_types
        }
    }
}
_jmespath_error_base_schema = {
    "title": "JMESPath Error",
    "description": "Error when a JMESPath query for a grant produces an error.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message",
        "critical",
        "grant"
    ],
    "properties": {
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "critical": {
            "type": "boolean",
            "description": "If this error caused the the workflow to exit early."
        },
        "grant": {
            "$ref": "#/$defs/grant"
        }
    }
}
_request_error_base_schema = {
    "title": "Workflow Request Error",
    "description": "Error when a request is not valid.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "message",
        "critical",
    ],
    "properties": {
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "critical": {
            "type": "boolean",
            "description": "If this error caused the the workflow to exit early."
        }
    }
}
_errors_base_schema = {
    "title": "Workflow Errors",
    "description": "Errors returned from Authzee workflows.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "context",
        "definition",
        "grant",
        "jmespath",
        "request"
    ],
    "properties": {
        "context": {
            "type": "array",
            "items": _context_error_base_schema
        },
        "definition": {
            "type": "array",
            "items": _definition_error_base_schema
        },
        "grant": {
            "type": "array",
            "items": _grant_error_base_schema
        },
        "jmespath": {
            "type": "array",
            "items": _jmespath_error_base_schema
        },
        "request": {
            "type": "array",
            "items": _request_error_base_schema
        }
    },
    # "anyOf": [
    #     _context_error_base_schema,
    #     _definition_error_base_schema,
    #     _grant_error_base_schema,
    #     _jmespath_error_base_schema,
    #     _request_error_base_schema
    # ],
    "$defs": {
        "grant": None # Replaced with full grant schema
    }
}
_request_base_schema = {
    "title": "Workflow Request",
    "description": "Request for an Authzee workflow.",
    "anyOf": [],
    "$defs": {
        "context": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z0-9_]{1,256}$": {
                    "type": _any_types
                }
            }
        },
        "identities": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {}
        }
    }
}
_resource_request_base_schema = {
    "title": "",
    "description": "",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "identities",
        "resource_type",
        "action",
        "resource",
        "parents",
        "children",
        "context"
    ],
    "properties": {
        "identities": {
            "$ref": "#/$defs/identities"
        },
        "action": {
            "type": "string" # this changes based on resource type - obj
        },
        "resource_type": {
            "const": "" # this changes based on resource type - obj
        },
        "resource": {}, # this changes based on resource type - obj
        "parents": {}, # changes based on resource type. Must include all Parent types - object of arrays
        "children": {}, # changes based on resource type. Must include all Child types - object of arrays
        "context": {
            "$ref": "#/$defs/context"
        }
    }
}
_evaluate_response_base_schema = {
    "title": "Evaluate Response",
    "description": "Response for the evaluate workflow.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "grants",
        "errors"
    ],
    "properties": {
        "completed": {
            "type": "boolean",
            "description": "The workflow completed."
        },
        "grants": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/grant"
            },
            "description": "List of grants that are applicable to the request."
        },
        "errors": None # Replaced with full errors schema
    },
    "$defs": {
        "grant": None # Replaced with full grant schema
    }
}
_authorize_response_base_schema = {
    "title": "Authorize Response",
    "description": "Response for the authorize workflow.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "authorized",
        "completed",
        "grant",
        "message",
        "errors"
    ],
    "properties": {
        "authorized": {
            "type": "boolean",
            "description": "true if the request is authorized.  false if it is not authorized."
        },
        "completed": {
            "type": "boolean",
            "description": "The workflow completed."
        },
        "grant": {
            "description": "Grant that was responsible for the authorization decision, if applicable.",
            "anyOf": [
                {
                    "$ref": "#/$defs/grant"
                },
                {"type": "null"}
            ]
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not."
        },
        "errors": None # Replaced with full errors schema
    },
    "$defs": {
        "grant": None # Replaced with full grant schema
    }
}


def validate_definitions(
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    errors = []
    id_types = []
    for id_def in identity_defs:
        try:
            jsonschema.validate(id_def, identity_definition_schema)
            if id_def['identity_type'] not in id_types:
                id_types.append(id_def['identity_type'])
            else:
                errors.append(
                    {
                        "message": f"Identity types must be unique. '{id_def['identity_type']}' is present more than once.",
                        "critical": True,
                        "definition_type": "identity",
                        "definition": id_def
                    }
                )
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "message": f"Identity definition schema was not valid. Schema Error: {exc}'",
                    "critical": True,
                    "definition_type": "identity",
                    "definition": id_def
                }
            )

    r_types = []
    for r_def in resource_defs:
        try:
            jsonschema.validate(r_def, resource_definition_schema)
            if r_def['resource_type'] not in r_types:
                r_types.append(r_def['resource_type'])
            else:
                errors.append(
                    {
                        "message": f"Resource types must be unique. '{r_def['resource_type']}' is present more than once.",
                        "critical": True,
                        "definition_type": "resource",
                        "definition": r_def
                    }
                )
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "message": f"Resource definition was not valid. Schema Error: {exc}'",
                    "critical": True,
                    "definition_type": "resource",
                    "definition": r_def
                }
            )

    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def generate_schemas(
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    schemas = {
        "grant": copy.deepcopy(_grant_base_schema),
        "errors": copy.deepcopy(_errors_base_schema),
        "request": copy.deepcopy(_request_base_schema),
        "evaluate": copy.deepcopy(_evaluate_response_base_schema),
        "authorize": copy.deepcopy(_authorize_response_base_schema)
    }
    # grant schema
    actions = set()
    for r_def in resource_defs:
        for a in r_def['actions']:
            actions.add(a)

    enum_action_schema = copy.deepcopy(_action_schema)
    enum_action_schema["enum"] = list(actions)
    schemas['grant']['properties']['actions']['items'] = enum_action_schema

    # error schema
    schemas['errors']['$defs']['grant'] = schemas['grant']

    # evaluate response schema
    workflow_errors_schema = copy.deepcopy(schemas['errors'])
    workflow_errors_schema.pop("$defs")
    schemas['evaluate']['properties']['errors'] = workflow_errors_schema
    schemas['evaluate']['$defs']['grant'] = schemas['grant']

    # authorize response schema
    schemas['authorize']['properties']['errors'] = workflow_errors_schema
    schemas['authorize']['$defs']['grant'] = schemas['grant']

    # request schema
    request_schema = copy.deepcopy(_request_base_schema)
    for id_def in identity_defs:
        request_schema['$defs']['identities']['required'].append(id_def['identity_type'])
        request_schema['$defs']['identities']['properties'][id_def['identity_type']] = {
            "type": "array",
            "items": id_def['schema']
        }

    type_to_def = {d['resource_type']: d for d in resource_defs}
    for r_type, r_def in type_to_def.items():
        rt_request_schema = copy.deepcopy(_resource_request_base_schema)
        rt_request_schema['title'] = f"'{r_type}' Resource Type Workflow Request"
        rt_request_schema['description'] = f"'{r_type}' resource type request for an Authzee workflow."
        rt_request_schema['properties']['action']['enum'] = r_def['actions']
        rt_request_schema['properties']['resource_type']['const'] = r_type
        request_schema['$defs'][r_type] = r_def['schema']
        rt_request_schema['properties']['resource'] = {
            "$ref": f"#/$defs/{r_type}"
        }
        rt_request_schema['properties']['parents'] = {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {}

        }
        for p_type in r_def['parent_types']:
            rt_request_schema['properties']['parents']['required'].append(p_type)
            rt_request_schema['properties']['parents']['properties'][p_type] = {
                "type": "array",
                "items": {
                    "$ref": f"#/$defs/{p_type}"
                }
            }
        
        rt_request_schema['properties']['children'] = {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {}

        }
        for c_type in r_def['child_types']:
            rt_request_schema['properties']['children']['required'].append(c_type)
            rt_request_schema['properties']['children']['properties'][c_type] = {
                "type": "array",
                "items": {
                    "$ref": f"#/$defs/{c_type}"
                }
            }
        
        request_schema['anyOf'].append(rt_request_schema)
    
    schemas['request'] = request_schema

    return schemas


def validate_grants(grants: List[Dict[str, AnyJSON]], schema: Dict[str, AnyJSON]) -> Dict[str, AnyJSON]:
    errors = []
    for g in grants:
        try:
            jsonschema.validate(g, schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "message": f"The grant is not valid. Schema Error: {exc}" ,
                    "critical": True,
                    "grant": g
                }
            )
    
    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }



def validate_request(request: Dict[str, AnyJSON], schema: Dict[str, AnyJSON]) -> Dict[str, AnyJSON]:
    try:
        jsonschema.validate(request, schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "valid": False,
            "errors": [
                {
                    "message": f"The request is not valid for the request schema: {exc}",
                    "critical": True
                }
            ]
        }
    
    return {
        "valid": True,
        "errors": []
    }         


def _evaluate_one(
    request: Dict[str, AnyJSON], 
    grant: Dict[str, AnyJSON],
    search: Callable[[str, AnyJSON], AnyJSON],
    context_validation: Literal["grant", "none", "validate", "error", "critical"],
    query_validation: Literal["grant", "validate", "error", "critical"]
):
    result = {
        "critical": False,
        "applicable": False,
        "errors": {
            "context": [],
            "definition": [],
            "grant": [],
            "jmespath": [],
            "request": []
        }
    }
    if request['action'] not in grant["actions"] and len(grant['actions']) > 0:
        return result
    
    c_val = grant['context_validation'] if context_validation == "grant" else context_validation
    if c_val != "none":
        try:
            jsonschema.validate(request['context'], grant['context_schema'])
        except jsonschema.exceptions.ValidationError as exc:
            is_c_val_crit = c_val == "critical"
            if (
                c_val == "error"
                or is_c_val_crit is True
            ):
                result['errors']['context'].append(
                    {
                        "message": str(exc),
                        "critical": is_c_val_crit,
                        "grant": grant
                    }
                )
                if is_c_val_crit is True:
                    result['critical'] = True
                    
            return result

    try:
        if grant['equality'] == search(
            grant['query'], 
            {
                "request": request,
                "grant": grant
            }
        ):
            result['applicable'] = True
    except jmespath.exceptions.JMESPathError as exc:
        q_val = grant['query_validation'] if query_validation == "grant" else query_validation
        is_q_val_crit = q_val == "critical"
        if (
            q_val == "error"
            or is_q_val_crit is True
        ):
            result['errors']['jmespath'].append(
                {
                    "message": str(exc),
                    "critical": is_q_val_crit,
                    "grant": grant
                }
            )
            if is_q_val_crit is True:
                result['critical'] = True
                
        # return right after this anyway

    return result


def evaluate(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    search: Callable[[str, AnyJSON], AnyJSON],
    query_validation: Literal["grant", "validate", "error", "critical"],
    context_validation: Literal["grant", "none", "validate", "error", "critical"]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
    result = {
        "completed": True,
        "grants": [],
        "errors": {
            "context": [],
            "definition": [],
            "grant": [],
            "jmespath": [],
            "request": []
        }
    }
    for g in grants:
        g_eval = _evaluate_one(request, g, search, context_validation, query_validation)
        result['errors']['context'] += g_eval['errors']['context']
        result['errors']['jmespath'] += g_eval['errors']['jmespath']
        if g_eval['critical'] is True:
            result['completed'] = False

            return result 

        elif g_eval['applicable'] is True:
            result['grants'].append(g)

    return result


def authorize(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    search: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
    errors =  {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
    allow_grants = []
    deny_grants = []
    for g in grants:
        if request['action'] in g['actions'] or len(g['actions']) == 0:
            if g['effect'] == "allow":
                allow_grants.append(g)
            else:
                deny_grants.append(g)
    
    for g in deny_grants:
        g_eval = _evaluate_one(request, g, search, "grant", "grant")
        errors['context'] += g_eval['errors']['context']
        errors['jmespath'] += g_eval['errors']['jmespath']
        if g_eval['critical'] is True:
            return {
                "authorized": False,
                "completed": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "errors": errors
            }
        
        if g_eval['applicable'] is True:
            return {
                "authorized": False,
                "completed": True,
                "grant": g,
                "message": "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "errors": errors
            }
    
    for g in allow_grants:
        g_eval = _evaluate_one(request, g, search, "grant", "grant")
        errors['context'] += g_eval['errors']['context']
        errors['jmespath'] += g_eval['errors']['jmespath']
        if g_eval['critical'] is True:
            return {
                "authorized": False,
                "completed": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "errors": errors
            }
        
        if g_eval['applicable'] is True:
            return {
                "authorized": True,
                "completed": True,
                "grant": g,
                "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "errors": errors
            }
    
    return {
        "authorized": False,
        "completed": True,
        "grant": None,
        "message": "No allow or deny grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
        "errors": errors
    }


def evaluate_workflow(
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    search: Callable[[str, AnyJSON], AnyJSON],
    query_validation: Literal["grant", "validate", "error", "critical"],
    context_validation: Literal["grant", "none", "validate", "error", "critical"]
):
    errors = {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
    def_val = validate_definitions(
        identity_defs,
        resource_defs
    )
    errors['definition'] = def_val['errors']
    if def_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": errors
        }
    
    schemas = generate_schemas(
        identity_defs,
        resource_defs
    )
    grant_val = validate_grants(grants, schemas['grant'])
    errors['grant'] = grant_val['errors']
    if grant_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": errors
        }

    request_val = validate_request(request, schemas['request'])
    errors['request'] = request_val['errors']
    if request_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": errors
        }

    return evaluate(request, grants, search, query_validation, context_validation)


def authorize_workflow(
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    search: Callable[[str, AnyJSON], AnyJSON]
):
    errors = {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
    def_val = validate_definitions(
        identity_defs,
        resource_defs
    )
    errors['definition'] = def_val['errors']
    if def_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "One or more identity and/or resource definitions are not valid. Therefore, the request is not authorized.",
            "completed": False,
            "errors": errors
        }
    
    schemas = generate_schemas(
        identity_defs,
        resource_defs
    )
    grant_val = validate_grants(grants, schemas['grant'])
    errors['grant'] = grant_val['errors']
    if grant_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "One or more grants are not valid.  Therefore, the request is not authorized.",
            "completed": False,
            "errors": errors
        }

    request_val = validate_request(request, schemas['request'])
    errors['request'] = request_val['errors']
    if request_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "The request is not valid. Therefore the request is not authorized.",
            "completed": False,
            "errors": errors
        }

    return authorize(request, grants, search)

