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
9. Run authorize() or audit() with the the previously validated grants and request. 

For reference of the complete work
"""

__all__ = [
    "identity_definition_schema",
    "resource_definition_schema",
    "validate_definitions",
    "generate_schemas",
    "validate_grants",
    "validate_request",
    "evaluate_one"
    "audit",
    "authorize",
    "audit_workflow",
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

context_definition_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Context Definition",
    "description": "A request context definition.  Defines a type of context that can be passed with Authzee requests.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "context_type",
        "schema"
    ],
    "properties": {
        "context_type": _type_schema,
        "schema": _schema_schema
    }
}
identity_definition_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
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
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Resource Definition",
    "description": "An resource definition.  Defines a type of resource to use with Authzee.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "resource_type",
        "actions",
        "schema"
    ],
    "properties": {
        "resource_type": _type_schema,
        "actions": {
            "type": "array",
            "uniqueItems": True,
            "items": _action_schema
        },
        "schema": _schema_schema
    }
}
_query_validation_schema = {
    "type": "string",
    "title": "Grant-Level Query Validation Setting",
    "description": (
        "Grant-level query validation setting. Set how the query errors are treated. "
        "'validate' - Query errors cause the grant to be inapplicable to the request. "
        "'error' - Includes the 'validate' setting checks, and also adds errors to the result. "
        "'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early."
    ),
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
    "additionalProperties": False,
    "required": [
        "effect",
        "actions",
        "query",
        "query_validation",
        "equality",
        "data",
        "context_type"
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
        "query_validation": _query_validation_schema,
        "equality": {
            "description": "Expected value for they query to return.  If the query result matches this value the grant is a considered applicable to the request."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "context_type": _type_schema
    }
}
_is_critical_schema = {
    "type": "boolean",
    "description": "If this error caused the the workflow to exit early."
}
_error_message_schema = {
    "type": "string",
    "description": "Detailed message about what caused the error."
}
definition_error_schema = {
    "title": "Definition Error",
    "description": "Error when an context, identity, or resource definition is not valid.",
    "type": "object",
    "additionalProperties": False,
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
    "additionalProperties": False,
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
jmespath_error_schema = {
    "title": "JMESPath Error",
    "description": "Error when a JMESPath query for a grant produces an error.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_critical",
        "message",
        "grant"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema,
        "grant": grant_schema
    }
}
request_error_schema = {
    "title": "Workflow Request Error",
    "description": "Error when a request is not valid.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_critical",
        "message"
    ],
    "properties": {
        "is_critical": _is_critical_schema,
        "message": _error_message_schema
    }
}
errors_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Workflow Errors",
    "description": "Errors returned from Authzee workflows.",
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {
        "definition": {
            "type": "array",
            "items": definition_error_schema
        },
        "grant": {
            "type": "array",
            "items": grant_error_schema
        },
        "jmespath": {
            "type": "array",
            "items": jmespath_error_schema
        },
        "request": {
            "type": "array",
            "items": request_error_schema
        }
    }
}
_request_query_validation_schema = {
    "type": "string",
    "title": "Request-Level Query Validation Setting",
    "description": "Request-level query validation setting. Overrides " + _query_validation_schema['description'],
    "enum": ["grant"] + _query_validation_schema['enum']
}
request_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Workflow Request",
    "description": "Request for an Authzee workflow.",
    "additionalProperties": False,
    "required": [
        "identities",
        "action",
        "resource_type",
        "resource",
        "query_validation",
        "context_type",
        "context"
    ],
    "properties": {
        "identities": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "patternProperties": {
                _type_regex: {
                    "type": "object"
                }
            }
        },
        "action": _action_schema,
        "resource_type": _type_schema,
        "resource": {
            "type": "object",
            "description": "Resource for the request."
        },
        "query_validation": _request_query_validation_schema,
        "context_type": _type_schema,
        "context": {
            "type": "object",
            "description": "Context for the request."
        }
    }
}
_completed_request_schema = {
    "type": "boolean",
    "description": "The workflow completed."
}
audit_response_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Audit Response",
    "description": "Response for the audit workflow.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "completed",
        "grants",
        "errors"
    ],
    "properties": {
        "completed": _completed_request_schema,
        "grants": {
            "type": "array",
            "description": "List of grants that are applicable to the request.",
            "items": grant_schema
        },
        "errors": errors_schema
    }
}
authorize_response_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authorize Response",
    "description": "Response for the authorize workflow.",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "completed",
        "authorized",
        "grant",
        "message",
        "critical_errors"
    ],
    "properties": {
        "completed": _completed_request_schema,
        "authorized": {
            "type": "boolean",
            "description": "true if the request is authorized.  false if it is not authorized."
        },
        "grant": {
            "description": "Grant that was responsible for the authorization decision, if applicable.",
            "anyOf": [
                {"type": "null"},
                grant_schema
            ]
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not."
        },
        "critical_errors": errors_schema
    }
}

batch_request_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Workflow Request",
    "description": "Request for an Authzee Batch workflow.",
    "additionalProperties": False,
    "required": [
        "identities",
        "action",
        "resource_type",
        "context_type",
        "batch"
    ],
    "properties": {
        "identities": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "patternProperties": {
                _type_regex: {
                    "type": "object"
                }
            }
        },
        "action": _action_schema,
        "resource_type": _type_schema,
        "context_type": _type_schema,
        "batch": {
            "type": "array",
            "description": "batch of resources and contexts to process with shared identities, action, resource type, and context type.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "resource",
                    "query_validation",
                    "context"
                ],
                "properties": {
                    "resource": {
                        "type": "object",
                        "description": "Resource for this batch item."
                    },
                    "query_validation": _request_query_validation_schema,
                    "context": {
                        "type": "object",
                        "description": "Context for this batch item."
                    }
                }
            }
        }
    }
}
batch_audit_response_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Audit Response",
    "description": "Response for the batch audit workflow.",
    "type": "array",
    "items": audit_response_schema
}
batch_authorize_response_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Authorize Response",
    "description": "Response for the batch authorize workflow.",
    "type": "array",
    "items": authorize_response_schema
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
                    "message": f"Context definition is not valid. Schema Error: {exc}'",
                    "is_critical": True,
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
                    "message": f"Context types must be unique. '{c_def['context_type']}' is present more than once.",
                    "is_critical": True,
                    "definition_type": "context",
                    "definition": c_def
                }
            )

    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def validate_identity_definitions(identity_defs: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    errors = []
    id_types = []
    for id_def in identity_defs:
        try:
            jsonschema.validate(id_def, identity_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "message": f"Identity definition is not valid. Schema Error: {exc}'",
                    "is_critical": True,
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
                    "message": f"Identity types must be unique. '{id_def['identity_type']}' is present more than once.",
                    "is_critical": True,
                    "definition_type": "identity",
                    "definition": id_def
                }
            )

    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def validate_resource_definitions(resource_defs: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
    errors = []
    r_types = set()
    for r_def in resource_defs:
        try:
            jsonschema.validate(r_def, resource_definition_schema)
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "message": f"Resource definition is not valid. Schema Error: {exc}",
                    "is_critical": True,
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
                    "message": f"Resource types must be unique. '{r_def['resource_type']}' is present more than once.",
                    "is_critical": True,
                    "definition_type": "resource",
                    "definition": r_def
                }
            )
    
    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def validate_grants(
    grants: List[Dict[str, AnyJSON]],
    context_definitions: List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    context_types = set([c['context_type'] for c in context_definitions])
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
                    "message": f"The grant is not valid. Schema Error: {exc}" ,
                    "is_critical": True,
                    "grant": g
                }
            )
            continue

        if g['context_type'] not in context_types:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The '{g['context_type']}' context_type is not valid.",
                    "grant": g
                }
            )
        
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
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def validate_request(
    request: Dict[str, AnyJSON],
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions:List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    errors = []
    try:
        jsonschema.validate(request, request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "valid": False,
            "errors" : [
                {
                    "is_critical": True,
                    "message": f"The request is not valid. Schema Error: {exc}"
                }
            ]
        }
    
    context_type_lut = {c['context_type']: c for c in context_definitions}
    if request['context_type'] not in context_type_lut:
        errors.append(
            {
                "is_critical": True,
                "message": f"Context type '{request['context_type']}' is not valid."
            }
        )
    else:
        try:
            jsonschema.validate(request['context'], context_type_lut[request['context_type']])
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The request context is not valid for the the '{request['context_type']}' context type. Schema Error: {exc}"
                }
            )
    
    identity_type_lut = {i['identity_type']: i for i in identity_definitions}
    for i_type in request['identities']:
        if i_type not in identity_type_lut:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"Identity Type '{i_type}' is not valid."
                }
            )
        else:
            i_num = 0
            for identity, i_num in zip(request['identities'][i_type], range(len(request['identities'][i_type]))):
                try:
                    jsonschema.validate(identity, identity_type_lut[i_type]['schema'])
                except jsonschema.exceptions.ValidationError as exc:
                    errors.append(
                        {
                            "is_critical": True,
                            "message": f"Identity '{i_type}[{i_num}]' is not valid. Schema Error: {exc}"
                        }
                    )
                i_num += 1

    resource_type_lut = {r['resource_type']: r for r in resource_definitions}
    if request['resource_type'] not in resource_type_lut:
        errors.append(
            {
                "is_critical": True,
                "message": f"Resource type '{request['resource_type']}' is not valid."
            }
        )
    else:
        try:
            jsonschema.validate(request['resource'], resource_type_lut[request['resource_type']]['schema'])
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(
                {
                    "is_critical": True,
                    "message": f"The request resource is not valid for the '{request['resource_type']}' resource type. Schema Error: {exc}"
                }
            )
    
    actions = set()
    for r_def in resource_definitions:
        for action in r_def['actions']:
            actions.add(action)

    if request['action'] not in actions:
        errors.append(
            {
                "is_critical": True,
                "message": f"Resource action '{request['action']}' is not valid."
            }
        )
    
    return {
        "valid": False if len(errors) > 0 else True,
        "errors": errors
    }


def validate_batch_request(
    batch_request: Dict[str, AnyJSON],
    context_definitions: List[Dict[str, AnyJSON]],
    identity_definitions:List[Dict[str, AnyJSON]],
    resource_definitions: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
    errors = []
    # Will need to split out errors to at least check batch request schema
    # if that fails we don't even try to evaluate any further
    # do we just copy that or put in separate errors
    # batch 
    try:
        jsonschema.validate(batch_request, batch_request_schema)
    except jsonschema.exceptions.ValidationError as exc:
        return {
            "valid": False,
            "errors" : [
                {
                    "is_critical": True,
                    "message": f"The request is not valid. Schema Error: {exc}"
                }
            ]
        }
        


def evaluate_one(
    request: Dict[str, AnyJSON], 
    grant: Dict[str, AnyJSON],
    search: Callable[[str, AnyJSON], AnyJSON],
    only_crits: bool
) -> Dict[str, AnyJSON]:
    result = {
        "is_critical": False,
        "applicable": False,
        "errors": {
            "context": [],
            "definition": [],
            "grant": [],
            "jmespath": [],
            "request": []
        }
    }
    if request['action'] not in grant['action'] and len(grant['actions']) > 0:
        return result
    
    c_val = grant['context_validation'] if request['context_validation'] == "grant" else request['context_validation']
    is_c_val_crit = c_val == "critical"
    if (
        c_val != "none"
        and (
            only_crits is False
            or is_c_val_crit is True # and only_crits is True
        )
    ):
        try:
            jsonschema.validate(request['context'], grant['context_schema'])
        except jsonschema.exceptions.ValidationError as exc:
            if (
                c_val == "error"
                or is_c_val_crit is True
            ):
                result['errors']['context'].append(
                    {
                        "is_critical": is_c_val_crit,
                        "message": str(exc),
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
        q_val = grant['query_validation'] if request['query_validation'] == "grant" else request['query_validation']
        is_q_val_crit = q_val == "critical"
        if (
            (
                q_val == "error"
                and only_crits is False
            )
            or is_q_val_crit is True
        ):
            result['errors']['jmespath'].append(
                {
                    "is_critical": is_q_val_crit,
                    "message": str(exc),
                    "grant": grant
                }
            )
            if is_q_val_crit is True:
                result['critical'] = True
                
        # return right after this anyway

    return result


def audit(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    search: Callable[[str, AnyJSON], AnyJSON]
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
        g_eval = evaluate_one(request, g, search, False)
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
        if g['effect'] == "allow":
            allow_grants.append(g)
        else:
            deny_grants.append(g)
    
    for g in deny_grants:
        g_eval = evaluate_one(request, g, search, True)
        errors['context'] += g_eval['errors']['context']
        errors['jmespath'] += g_eval['errors']['jmespath']
        if g_eval['critical'] is True:
            return {
                "authorized": False,
                "completed": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "critical_errors": errors
            }
        
        if g_eval['applicable'] is True:
            return {
                "authorized": False,
                "completed": True,
                "grant": g,
                "message": "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "critical_errors": errors
            }
    
    for g in allow_grants:
        g_eval = evaluate_one(request, g, search, True)
        errors['context'] += g_eval['errors']['context']
        errors['jmespath'] += g_eval['errors']['jmespath']
        if g_eval['critical'] is True:
            return {
                "authorized": False,
                "completed": False,
                "grant": g,
                "message": "A critical error has occurred. Therefore, the request is not authorized.",
                "critical_errors": errors
            }
        
        if g_eval['applicable'] is True:
            return {
                "authorized": True,
                "completed": True,
                "grant": g,
                "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "critical_errors": errors
            }
    
    return {
        "authorized": False,
        "completed": True,
        "grant": None,
        "message": "No allow or deny grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
        "critical_errors": errors
    }


def audit_workflow(
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

    return audit(request, grants, search)


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
            "critical_errors": errors
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
            "critical_errors": errors
        }

    request_val = validate_request(request, schemas['request'])
    errors['request'] = request_val['errors']
    if request_val['valid'] is False:
        return {
            "authorized": False,
            "grant": None,
            "message": "The request is not valid. Therefore the request is not authorized.",
            "completed": False,
            "critical_errors": errors
        }

    return authorize(request, grants, search)

