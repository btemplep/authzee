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
from typing import Callable, Dict, List, Union

import jmespath
import jmespath.exceptions
import jsonschema
import jsonschema.exceptions


AnyJSON = Union[bool, str, int, float, None, list, dict]
_any_types = ["array", "boolean", "integer", "null", "number", "object", "string"]
_type_schema = {
    "type": "string",
    "pattern": "^[A-Za-z0-9_]*$",
    "minLength": 1,
    "maxLength": 256,
    "description": "A unique name to identity this type."
}
_action_schema = {
    "type": "string",
    "pattern": "^[A-Za-z0-9_.:-]*$",
    "minLength": 1,
    "maxLength": 512,
    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
}
_schema_schema = jsonschema.Draft202012Validator.META_SCHEMA

identity_definition_schema = {
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
    "type": "object",
    "additionalProperties": False,
    "required": [
        "effect",
        "actions",
        "query",
        "equality",
        "data",
        "context_schema",
        "validate_context",
        "invalid_context_deny"
    ],
    "properties": {
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": "A applicable deny grant will always deny a request.  If no applicable deny grants, an applicable allow grant will allow a request. By default, no applicable grants requests are denied."
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
        "equality": {
            "type": _any_types,
            "description": "Expected value for they query to return.  If the query result matches this value the grant is a considered applicable to the request."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "context_schema": _schema_schema, # schema for a schema must be of type object at a base
        "validate_context": {
            "type": "boolean",
            "description": "The request context is first validated against this schema. If it is invalid the grant is considered not applicable."
        },
        "invalid_context_deny": {
            "type": "boolean",
            "description": "The request context is first validated against this schema. If it is invalid, this is considered a deny.  Overrides the validate_context field."
        }
    }
}
_error_base_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "error_type",
        "message",
        "critical",
    ],
    "properties": {
        "error_type": {
            "type": "string",
            "enum": [
                "context", # include the grant that caused the error
                "definition", # include definition that caused the error
                "grant", # include the grant that caused the error
                "jmespath", # include the grant that caused the error
                "request" # Doesn't need any extra info besides the error message
            ],
            "description": "Source of the error."
        },
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
_authorize_response_base_schema = {
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
            "description": "The workflow completed or an error cause an early exit."
        },
        "grant": {
            "oneOf": [
                _grant_base_schema,
                {"type": None}
            ],
            "description": "Grant that was responsible for the authorization decision, if applicable."
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not."
        },
        "errors": {
            "type": "array",
            "description": "Errors that occurred when running the authorize workflow.",
            "items": _error_base_schema
        }
    }
}
_evaluate_response_base_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        
        "grants",
        "errors"
    ],
    "properties": {
        "completed": {
            "type": "boolean",
            "description": "The workflow completed or an error cause an early exit."
        },
        "grants": {
            "type": "array",
            "items": _grant_base_schema,
            "description": "List of grants that are applicable to the request."
        },
        "errors": {
            "type": "array",
            "items": _error_base_schema,
            "details": "Errors that occurred when running the evaluate workflow."
        }
    }
}
_request_base_schema = {
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
                        "error_type": "definition",
                        "message": f"Identity types must be unique. '{id_def['identity_type']}' is present more than once.",
                        "critical": True
                    }
                )
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "error_type": "definition",
                    "message": f"Identity definition schema was not valid. Definition: {json.dumps(id_def)} Schema Error: {exc}'",
                    "critical": True
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
                        "error_type": "definition",
                        "message": f"Resource types must be unique. '{r_def['resource_type']}' is present more than once.",
                        "critical": True
                    }
                )
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "error_type": "definition",
                    "message": f"Resource definition was not valid. Definition: {json.dumps(r_def)} Schema Error: {exc}'",
                    "critical": True
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
    result = {
        "schemas": {
            "grant": copy.deepcopy(_grant_base_schema),
            "error": copy.deepcopy(_error_base_schema),
            "request": copy.deepcopy(_request_base_schema),
            "authorize_response": copy.deepcopy(_authorize_response_base_schema),
            "evaluate": copy.deepcopy(_evaluate_response_base_schema)
        },
        "errors": []
    }
    # grant schema
    actions = set()
    for r_def in resource_defs:
        for a in r_def['actions']:
            actions.add(a)

    enum_action_schema = copy.deepcopy(_action_schema)
    enum_action_schema["enum"] = list(actions)
    result['schemas']['grant']['properties']['actions']['items'] = enum_action_schema

    # error schema
    one_of_grant = [
        result['schemas']['grant'],
        {"type": None}
    ]
    # result['schemas']['error']['properties']['grant']['oneOf'] = one_of_grant

    # authorize response schema
    result['schemas']['authorize_response']['properties']['grant']['oneOf'] = one_of_grant
    result['schemas']['authorize_response']['properties']['errors']['items'] = result['schemas']['error']

    # evaluate response schema
    result['schemas']['evaluate']['properties']['grants']['items'] = result['schemas']['grant']
    result['schemas']['evaluate']['properties']['errors']['items'] = result['schemas']['error']

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
    
    result['schemas']['request'] = request_schema

    return result


def validate_grants(grants: List[Dict[str, AnyJSON]], schema: Dict[str, AnyJSON]) -> Dict[str, AnyJSON]:
    errors = []
    for g in grants:
        try:
            jsonschema.validate(g, schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "error_type": "grant",
                    "message": f"The grant is not valid for grant schema. Grant: {g} Error: {exc}" ,
                    "critical": True
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
                    "error_type": "request",
                    "message": f"The request is not valid for the request schema: {exc}",
                    "critical": True
                }
            ]
        }
    
    return {
        "valid": True,
        "errors": []
    }         


def evaluate(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    search: Callable[[str, AnyJSON], AnyJSON],
    report_jmespath_errors: bool
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
    result = {
        "completed": True,
        "grants": [],
        "errors": []
    }
    for g in grants:
        if request['action'] in g["actions"] or len(g['actions']) == 0:
            try:
                if g['equality'] == search(
                    g['query'], 
                            {
                        "request": request,
                        "grant": g
                    }
                ):
                    result['grants'].append(g)
            except jmespath.exceptions.JMESPathError as error:
                if report_jmespath_errors is True:
                    result['errors'].append(
                        {
                            "error_type": "jmespath",
                            "message": str(error),
                            "critical": False
                        }
                    )
    
    return result


def authorize(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    search: Callable[[str, AnyJSON], AnyJSON],
    report_jmespath_errors: bool,
    jmespath_error_abort: bool
) -> Dict[str, AnyJSON]:
    errors = []
    allow_grants = []
    deny_grants = []
    for g in grants:
        if request['action'] in g['actions'] or len(g['actions']) == 0:
            if g['effect'] == "allow":
                allow_grants.append(g)
            else:
                deny_grants.append(g)
    
    for g in deny_grants:
        try:
            result = search(
                g['query'], 
                {
                    "request": request,
                    "grant": g
                }
            )
            if result == g['equality']:
                return {
                    "authorized": False,
                    "completed": True,
                    "grant": g,
                    "message": f"The deny grant is applicable to the request. Therefore, the request is not authorized.",
                    "errors": errors
                }
        except jmespath.exceptions.JMESPathError as exc:
            if report_jmespath_errors is True:
                errors.append(
                    {
                        "error_type": "jmespath",
                        "message": f"Grant: {g} caused a JMESPath error: {exc}",
                        "critical": jmespath_error_abort
                    }
                )
            if jmespath_error_abort is True:
                return {
                    "authorized": False,
                    "completed": False,
                    "grant": g,
                    "message": f"A JMESPath error has occurred and abort on error is enabled. {exc}",
                    "errors": errors
                }
    
    for g in allow_grants:
        try:
            result = search(
                g['query'], 
                {
                    "request": request,
                    "grant": g
                }
            )
            if result == g['equality']:
                return {
                    "authorized": True,
                    "completed": True,
                    "grant": g,
                    "message": f"The allow grant is applicable to the request. There are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                    "errors": errors
                }
        except jmespath.exceptions.JMESPathError as error:
            if report_jmespath_errors is True:
                errors.append(
                    {
                        "error_type": "jmespath",
                        "message": f"Grant: {g} caused a JMESPath error: {exc}",
                        "critical": jmespath_error_abort
                    }
                )
            if jmespath_error_abort is True:
                return {
                    "authorized": False,
                    "completed": False,
                    "grant": g,
                    "message": f"A JMESPath error has occurred and abort on error is enabled. {exc}",
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
    report_jmespath_errors: bool
):
    def_val = validate_definitions(
        identity_defs,
        resource_defs
    )
    if def_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": def_val['errors']
        }
    
    schemas = generate_schemas(
        identity_defs,
        resource_defs
    )
    
    grant_val = validate_grants(grants, schemas['grant'])
    if grant_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": grant_val['errors']
        }

    request_val = validate_request(request, schemas['request'])
    if request_val['valid'] is False:
        return {
            "completed": False,
            "grants": [],
            "errors": request_val['errors']
        }

    return evaluate(request, grants, search, report_jmespath_errors)


def authorize_workflow(
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    search: Callable[[str, AnyJSON], AnyJSON],
    report_jmespath_errors: bool,
    jmespath_error_abort: bool
):
    def_val = validate_definitions(
        identity_defs,
        resource_defs
    )
    if def_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "",
            "completed": False,
            "errors": def_val['errors']
        }
    
    schemas = generate_schemas(
        identity_defs,
        resource_defs
    )
    
    grant_val = validate_grants(grants, schemas['grant'])
    if grant_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "",
            "completed": False,
            "errors": grant_val['errors']
        }

    request_val = validate_request(request, schemas['request'])
    if request_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "",
            "completed": False,
            "errors": request_val['errors']
        }

    return authorize(request, grants, search, report_jmespath_errors, jmespath_error_abort)

