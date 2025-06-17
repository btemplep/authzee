"""A reference implementation for the core functionality of Authzee. 

Other compute engines may use these directly or implement their own version that is functionally equivalent.

Authzee workflow:
1. A user creates identity and resource definitions
2. Run ``generate_request_schema()`` to validate the definitions and generate the request schema
3. User can customize the request schema at this point
- When requests are made they are validated against the request schema
- Create a list of grants and validate against the grant schema
- With the validated request, the user can call ``authorize()`` or ``match_grants()``
    - Loop through deny grants
        - 
"""

__all__ = []

import copy
from typing import Any, Dict, List, Union

import jmespath
import jmespath.exceptions
import jsonschema


_any_types = ["array", "boolean", "integer", "null", "number", "object", "string"]
_type_schema = {
    "type": "string",
    "pattern": "^[A-Za-z0-9_]*$",
    "maxLength": 256,
    "description": "A unique name to identity this type."
}
_action_schema = {
    "type": "string",
    "pattern": "^[A-Za-z0-9_.:-]*$",
    "maxLength": 512,
    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
}
_schema_schema = jsonschema.Draft202012Validator.META_SCHEMA


identity_definition_schema = {
    "type": "object",
    "additional_properties": False,
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
            "items": _action_schema
        },
        "schema": _schema_schema,
        "parent_types": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Types that are a parent of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        },
        "child_types": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Types that are a child of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        }
    }
}
# Grant schemas should always be valid before storing/using
grant_schema = {
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
        "deny_invalid_context"
    ],
    "properties": {
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": "A matching deny grant will always deny a request.  If no matching deny grants, a matching allow grant will allow a request. by default, no matched grants is denied."
        },
        "actions": {
            "type": "array",
            "items": _action_schema,
            "description": "List of actions this grant applies to."
        },
        "query": {
            "type": "string",
            "description": "JMESPath query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
        },
        "equality": {
            "type": _any_types,
            "description": "Expected value for they query to return.  If the query result matches this value the grant is a match."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "context_schema": {
            "type": _schema_schema, # schema for a schema must be of type object at a base
            "description": "Expected schema of the request context field."
        },
        "validate_context": {
            "type": "boolean",
            "description": "The request context is first validated against this schema. If it is invalid the grant is not a match."
        },
        "deny_invalid_context": {
            "type": "boolean",
            "description": "The request context is first validated against this schema. If it is invalid, this is considered a deny.  Overrides the validate_context field."
        }
    }
}
error_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "type",
        "message",
        "grant",
    ],
    "properties": {
        "error_type": {
            "type": "string",
            "enum": [
                "context", # error when validating the context against the grant context schema
                "definition", # error when validating the identity or resource definitions
                "jmespath", # JMESPath error
                "request" # error when validating the request against the request schema
            ],
            "description": "Enum of where the source of the error is from."
        },
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        },
        "grant": {
            "oneOf": [
                grant_schema,
                {"type": None}
            ],
            "description": "The grant that was being evaluated when the error occurred or null if none were."
        }
    }
}
authorize_response_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {
        "authorized": {
            "type": "boolean",
            "description": "true if the request is authorized.  false if it is not authorized."
        },
        "grant": {
            "oneOf": [
                grant_schema,
                {"type": None}
            ],
            "description": "Grant that was responsible for the authorization decision."
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not."
        },
        "errors": {
            "type": "array",
            "items": error_schema,
            "details": "Errors that occurred when trying to authorize the request."
        }
    }
}
match_response_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "matches",
        "errors"
    ],
    "properties": {
        "matches": {
            "type": "array",
            "items": grant_schema,
            "description": "List of grants that match for the request."
        },
        "errors": {
            "type": "array",
            "items": error_schema,
            "details": "Errors that occurred when trying to match the request."
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
            "type": "string" # this changes based on resource type - obj
        },
        "resource": {}, # this changes based on resource type - obj
        "parents": {}, # changes based on resource type. Must include all Parent types - object of arrays
        "children": {}, # changes based on resource type. Must include all Child types - object of arrays
        "context": {
            "$ref": "#/$defs/context"
        }
    }
}
_authorization_base_schema = {
    "type": "object",
    "description": "Base schema for authorization data that is evaluated by a grant query.",
    "additionalProperties": False,
    "required": [
        "grant",
        "request"
    ],
    "properties": {
        "grant": grant_schema,
        "request": {
            "type": "object",
            "description": "Request that is being evaluated."
        }
    }
}


def generate_request_schema(
    identity_defs: List[Dict[str, Any]],
    resource_defs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    for id_def in identity_defs:
        jsonschema.validate(id_def, identity_definition_schema)

    resource_types = []
    for r_def in resource_defs:
        jsonschema.validate(r_def, resource_definition_schema)
        resource_types.append(r_def['resource_type'])

    resource_definition_schema['properties']['parent_types']['items']['enum'] = resource_types
    resource_definition_schema['properties']['child_types']['items']['enum'] = resource_types
    for r_def in resource_defs:
        jsonschema.validate(r_def, resource_definition_schema)

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
        rt_request_schema['properties']['resource_type']['enum'] = [r_type]
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

    return request_schema


def authorize(
    request: Dict[str, Any], 
    grants: List[Dict[str, Any]],
    jmespath_options: Union[jmespath.Options, None],
    report_jmespath_errors: bool,
    abort_jmespath_errors: bool
) -> Dict[str, Any]:
    errors = []
    deny_grants = [g for g in grants if g['effect'] == "deny"]
    allow_grants = [g for g in grants if g['effect'] == "allow"]
    for g in deny_grants:
        try:
            result = jmespath.search(
                expression=g['query'], 
                data=request,
                options=jmespath_options
            )
            if result == g['equality']:
                return {
                    "authorized": False,
                    "allow_grant": None,
                    "deny_grant": g,
                    "message": f"The deny grant '{g['grant_uuid']}' is a match so the request is not authorized.",
                    "errors": errors
                }
        except jmespath.exceptions.JMESPathError as error:
            if report_jmespath_errors is True:
                errors.append(
                    {
                        "type": "jmespath",
                        "message": str(error),
                        "grant_uuid": g['grant_uuid']
                        
                    }
                )
                if abort_jmespath_errors is True:
                    return {
                        "authorized": False,
                        "allow_grant": None,
                        "deny_grant": None,
                        "message": f"Abort on error is enabled and a jmespath error has occurred for .",
                        "errors": errors
                    }
    
    for g in allow_grants:
        try:
            result = jmespath.search(
                expression=g['query'], 
                data=request,
                options=jmespath_options
            )
            if result == g['equality']:
                return {
                    "authorized": True,
                    "allow_grants": g,
                    "deny_grant": None,
                    "message": f"The allow grant '{g['grant_uuid']}' is a match and no deny grants match, so the request is authorized.",
                    "errors": errors
                }
        except jmespath.exceptions.JMESPathError as error:
            if report_jmespath_errors is True:
                errors.append(
                    {
                        "type": "jmespath",
                        "message": str(error),
                        "grant_uuid": g['grant_uuid']
                        
                    }
                )
                if abort_jmespath_errors is True:
                    return {
                        "authorized": False,
                        "allow_grant": None,
                        "deny_grant": None,
                        "message": f"Abort on error is enabled and a jmespath error has occurred",
                        "errors": errors
                    }
    
    return {
        "authorized": False,
        "allow_grant": None,
        "deny_grant": None,
        "message": "No matching allow or deny grants were found, so the request is not authorized.",
        "errors": errors
    }


def match_grants(
    request: Dict[str, Any], 
    grants: List[Dict[str, Any]],
    jmespath_options: jmespath.Options=None,
    report_jmespath_errors: bool = False,
    abort_jmespath_errors: bool = False
) -> List[Dict[str, Any]]: 
    matches = []
    errors = []
    for g in grants:
        try:
            if g['equality'] == jmespath.search(
                expression=g['query'], 
                data=request,
                options=jmespath_options
            ):
                matches.append(g)
        except jmespath.exceptions.JMESPathError as error:
            if report_jmespath_errors is True:
                errors.append(
                    {
                        "type": "jmespath",
                        "message": str(error),
                        "grant_uuid": g['grant_uuid']
                    }
                )
                if abort_jmespath_errors is True:
                    break
    
    return {
        "grants": matches,
        "errors": errors
    }