# Authzee Specification
## Version 0.1.0a1  

This document describes the specification for **Authzee**.

For a quick introduction to the core Authzee engine see the [README](../README). 

For language specific use and guidance see the [SDKs](./sdks)

Authzee is a highly expressive grant-based authorization engine.  It uses JSON Schemas to define and validate all inputs and outputs. Grants are evaluated against the request data and grant data using JMESpath to make access control decisions. 

### Table of Contents

- [Authzee Specification](#authzee-specification)
- [Definitions](#definitions)
- [Identity Definitions](#identity-definitions)
- [Resource Definitions](#resource-definitions)
- [Grants](#grants)
- [Requests](#requests)
- [Workflows](#workflows)
- [Common Workflow Steps](#common-workflow-steps)
- [Grant Evaluations](#grant-evaluations)
- [Workflow Errors](#workflow-errors)
- [Audit Workflow](#audit-workflow)
- [Authorize Workflow](#authorize-workflow)


## Definitions

- **Identity** - An object representing a specific type of identity to consider when authorizing.
- **Resource** - An object representing a specific type of resource to authorize for.
- **Resource Action (Action)** - A name for a specific action taken on a resource.
- **Workflow** - A specific authorization process and the detailed steps to complete it.
- **Authorization Request (Request)** - The object used to specify identities, resources, actions, and other configurations to start a wokflow.
- **Calling Entity (Entity)** - Who or what is represented by a request.  A calling entity can have many identities of the same and different types. 
- **Grant** - The unit of authorization that defines the conditions needed for an entity to perform an action on a resource, and the effect, if the grant is applicable.


## Identity Definitions

Identity definitions describe the types of identities that a calling entity possesses to make authorization requests. These represent "who" is trying to access the resources.  Authzee generally refer's to "who" as the calling entity. Each identity type has a unique name and a JSON Schema that validates the structure and contents of identity objects that are passed in requests.

**Common Identity Types:**
- **Users**: Individual people with attributes like ID, email, department, roles
- **Groups**: Collections of users with shared characteristics (teams, departments, projects)
- **Roles**: Permission sets that define what actions can be performed
- **Applications**: Systems or services that act on behalf of users
- **API Keys**: Programmatic access tokens with associated permissions

This can also be extended to Identity Provider specific identities like **EntraGroup**, **OktaRole**, **ADUser**

Identity definitions enable flexible representation of complex organizational structures and permission models.

**Identity Definition Example**

```json
{
    "identity_type": "User",
    "schema": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "name",
            "email",
            "role",
            "age"
        ],
        "properties": {
            "name": {
                "type": "string"
            },
            "email": {
                "type": "string"
            },
            "role": {
                "type": "string",
                "enum": [
                    "reader",
                    "contributor",
                    "admin"
                ]
            },
            "age": {
                "type": "integer"
            }
        }
    }
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `identity_type` | string | ✅ | Unique identifier for this identity type. Must be alphanumeric with underscores only. Used as a key in request identity objects. |
| `schema` | object | ✅ | JSON Schema (Draft 2020-12) that defines the structure and validation rules for identity objects of this type. All identity instances passed in requests must conform to this schema. |


## Resource Definitions 

Resource definitions describe the types of resources that can be accessed and what actions can be performed on them. These represent "what" is being accessed. 

**Resource Definition Example**

```json
{
    "resource_type": "Balloon",
    "actions": [
        "Balloon:ListBalloons",
        "Balloon:Inflate",
        "Balloon:Pop"
    ],
    "schema": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "color",
            "max_diameter",
            "psi"
        ],
        "properties": {
            "color": {
                "type": "string"
            },
            "max_diameter": {
                "type": "number"
            },
            "psi": {
                "type": "integer"
            }
        }
    },
    "parent_types": [],
    "child_types": [
        "BalloonString"
    ]
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `resource_type` | string | ✅ | Unique identifier for this resource type. Must be alphanumeric with underscores only. Used to identify the resource type in authorization requests. |
| `actions` | array[string] | ✅ | List of unique action names that can be performed on this resource type. Actions can include dots, hyphens, colons, and underscores. Common patterns include using a namespace like "Balloon:inflate". It is best to have actions unique to resource types but it is not strictly enforced.|
| `schema` | object | ✅ | JSON Schema (Draft 2020-12) that defines the structure and validation rules for resource objects of this type. All resource instances must conform to this schema. |
| `parent_types` | array[string] | ✅ | Array of resource type names that can be parents of this resource type. Parent resources represent containment relationships (e.g., a BalloonStore contains Balloons). Can be empty if no parents exist. |
| `child_types` | array[string] | ✅ | Array of resource type names that can be children of this resource type. Child resources are contained by this resource type (e.g., a Balloon contains BalloonStrings). Can be empty if no children exist. |


## Grants

Grants are the core authorization unit. They query the request and grant data using JMESPath. 

The grant schema is generated based on the identity and resource definitions. 

**Grant Example**

```json
{
    "effect": "allow",
    "actions": [
        "Balloon:Pop",
        "Balloon:Inflate"
    ],
    "query": "contains(request.identities.Group[? contains(grant.data.allowed_groups, cn)]",
    "query_validation": "validate",
    "equality": true,
    "data": {
        "allowed_groups": "MyGroup"
    },
    "context_schema": {
        "type": "object",
        "required": [
            "some_context_field"
        ]
    },
    "context_validation": "none"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `effect` | string | ✅ | Whether this grant allows or denies access. Must be either "allow" or "deny". Deny grants always take precedence over allow grants. |
| `actions` | array | ✅ | List of resource actions this grant applies to. If empty array, applies to all actions. Must match actions defined in resource definitions. |
| `query` | string | ✅ | JMESPath expression that evaluates the request data. Has access to `request` (the full request object) and `grant` (the current grant with its data). The top-level query data structure is: `{"request": <request_object>, "grant": <grant_object>}` |
| `query_validation` | string | ✅ | How to handle JMESPath query errors. Options: <ul><li>`"validate"` - Query errors cause the grant to be inapplicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |
| `equality` | any | ✅ | Expected result from the query for this grant to be applicable. Can be any JSON value (boolean, string, number, object, array, null). |
| `data` | object | ✅ | Additional data made available to the query as `grant.data`. Useful for storing metadata or values used in query evaluation. |
| `context_schema` | object | ✅ | JSON Schema for validating the request context. Used to ensure the request has the required context data for this grant. |
| `context_validation` | string | ✅ | How to handle context validation. Options: <ul><li>`"none"` - There is no validation</li><li>`"validate"` - Context is validated and if the context is invalid, the grant is not applicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |


## Requests

Requests represent a specific authorization question: "Should the calling entity, that has these identities, be allowed to perform this action on this resource?" 


The request schema is generated based on the identity and resource definitions. 

**Request Example**

```json
{
    "identities": {
        "User": [
            {
                "id": "user123",
                "department": "party_planning",
                "email": "john.doe@company.com"
            }
        ],
        "Group": [
            {
                "name": "balloon-specialists",
                "department": "party_planning",
                "type": "team"
            }
        ],
        "Role": [
            {
                "name": "balloon-artist",
                "permissions": [
                    "balloon:read",
                    "balloon:inflate",
                    "balloon:tie"
                ],
                "level": "advanced"
            }
        ]
    },
    "resource_type": "Balloon",
    "action": "inflate",
    "resource": {
        "id": "balloon456",
        "color": "red",
        "size": "large",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": false
    },
    "parents": {
        "BalloonStore": [
            {
                "id": "store123",
                "name": "Party Central",
                "owner_department": "party_planning",
                "location": "Building A"
            }
        ]
    },
    "children": {
        "BalloonString": [
            {
                "id": "string1",
                "length": 24.5,
                "color": "white",
                "material": "cotton"
            }
        ]
    },
    "query_validation": "error",
    "context": {
        "request_source": "web_ui",
        "timestamp": "2023-12-07T10:30:00Z",
        "event_type": "birthday_party"
    },
    "context_validation": "grant"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `identities` | object | ✅ | Map of identity type names to arrays of identity objects. Each identity type must match a defined identity definition and conform to its schema. |
| `resource_type` | string | ✅ | The type of resource being accessed. Must match a defined resource definition, `resource_type`. |
| `action` | string | ✅ | The specific action being requested on the resource. Must be one of the actions defined for the resource type. |
| `resource` | object | ✅ | The target resource object. Must conform to the schema defined for the resource type. |
| `parents` | object | ✅ | Map of parent resource type names to arrays of parent resource objects. Only includes types listed in the resource definition's `parent_types`. |
| `children` | object | ✅ | Map of child resource type names to arrays of child resource objects. Only includes types listed in the resource definition's `child_types`. |
| `query_validation` | string | ✅ | Request-level override for query validation. Options: <ul><li>`"grant"` - Use the grant level query validation setting</li><li>`"validate"` - Query errors cause the grant to be inapplicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |
| `context` | object | ✅ | Additional context data for authorization decisions. Available to grant queries as `request.context`. The structure can be flexible depending on grant and request level context validation settings. |
| `context_validation` | string | ✅ | Request-level override for context validation. Options: <ul><li>`"grant"` - Use the grant level context validation setting</li><li>`"none"` - There is no validation</li><li>`"validate"` - Context is validated and if the context is invalid, the grant is not applicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |


## Workflows

Authzee supports the following workflows.

|Workflow|Description|
|--------|-----------|
|[Audit](#audit-workflow)|Find all applicable grants for a given request.|
|[Authorize](#authorize-workflow)|Compute if the given request is authorized.|

> **NOTE** - The spec defines and describes *complete workflows*, inputs, and outputs in detail.  It does not describe a full on API. This is done to leave room for customization based on language, compute, and storage.  A reference implementation of the most literal form is given to demonstrate the the spec. See the SDKs or the [SDK Patterns](#recommended-sdk-patterns) for more usable code and patterns.


## Common Workflow Steps

Authzee Workflows share the same initial parts with minor differences. These initial steps are defined here:

1. [Define Identity and Resource Types](#1-define-identity-and-resource-types)
2. [Validate Definitions](#2-validate-definitions)
3. [Generate Schemas](#3-generate-schemas) 
4. [Create Grants](#4-create-grants)
5. [Validate Grants](#5-validate-grants)
6. [Create Request](#6-create-request)
7. [Validate Request](#7-validate-request)

Along with the above steps, workflows must perform [Grant Evaluations](#grant-evaluations) against a request.

Workflows also share the same format of [Error Results]()

### 1. Define Identity and Resource Types

Create definitions for your identities and resources like the examples given above.  

### 2. Validate Definitions

Ensure all definitions are valid by comparing them to the static schemas and other checks.

- See `validate_definitions(identity_defs, resource_defs)` in the reference implementation
- Validate identity definitions
    - For each identity definition validate it against the static identity definition schema.
        ```json
        {
            "title": "Identity Definition",
            "description": "An identity definition.  Defines a type of identity to use with Authzee.",
            "type": "object",
            "additionalProperties": false,
            "required": [
                "identity_type",
                "schema"
            ],
            "properties": {
                "identity_type": {
                    "title": "Authzee Type",
                    "description": "A unique name to identity this type.",
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_]*$",
                    "minLength": 1,
                    "maxLength": 256
                },
                "schema":{
                    "$ref": "https://json-schema.org/draft/2020-12/schema"
                }
            }
        }
        ```
    - Validate that `identity_type`s are unique
- Validate resource definitions
    - For each resource definition, validate it against the static resource definition schema.
        ```json
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Resource Definition",
            "description": "An resource definition.  Defines a type of resource to use with Authzee.",
            "type": "object",
            "additionalProperties": false,
            "required": [
                "resource_type",
                "actions",
                "schema",
                "parent_types",
                "child_types"
            ],
            "properties": {
                "resource_type": {
                    "title": "Authzee Type",
                    "description": "A unique name to identity this type.",
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_]*$",
                    "minLength": 1,
                    "maxLength": 256
                },
                "actions": {
                    "type": "array",
                    "uniqueItems": true,
                    "items": {
                        "title": "Resource Action",
                        "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
                        "type": "string",
                        "pattern": "^[A-Za-z0-9_.:-]*$",
                        "minLength": 1,
                        "maxLength": 512
                    }
                },
                "schema": {
                    "$ref": "https://json-schema.org/draft/2020-12/schema"
                },
                "parent_types": {
                    "type": "array",
                    "uniqueItems": true,
                    "items": {
                        "type": "string"
                    },
                    "description": "Types that are a parent of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
                },
                "child_types": {
                    "type": "array",
                    "uniqueItems": true,
                    "items": {
                        "type": "string"
                    },
                    "description": "Types that are a child of this resource.  When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
                }
            }
        }
        ```
- Validate that the `resource_type`s are unique
- If any errors occur during validation of this step:
    - add them to the result `errors.definition` field array as critical errors.  
    - After this step finishes, exit the workflow.
    - Errors when validating identity definitions should have error definition type of `"identity"`, and set the `definition` field to the invalid definition.

### 3. Generate Schemas

Create JSON schemas for grants, errors, requests, and responses based on the identity and resource definitions.   
- See `generate_schemas(identity_defs, resource_defs)` in the reference implementation
- **Grant Schema**
    - Start with a base schema 
        ```json
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Grant",
            "description": "A grant is an object representing an enacted authorization rule.",
            "type": "object",
            "additionalProperties": false,
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
                    "description": "Any applicable deny grant will always cause the request to be not authorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and not authorized."
                },
                "actions": {
                    "type": "array",
                    "uniqueItems": true,
                    "items": {
                        "type": "array",
                        "uniqueItems": true,
                        "items": {
                            "title": "Resource Action",
                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
                            "type": "string",
                            "pattern": "^[A-Za-z0-9_.:-]*$",
                            "minLength": 1,
                            "maxLength": 512
                        }
                    },
                    "description": "List of actions this grant applies to or null to match any resource action."
                },
                "query": {
                    "type": "string",
                    "description": "JMESPath query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
                },
                "query_validation": {
                    "type": "string",
                    "title": "Grant-Level Query Validation Setting",
                    "description": "Grant-level query validation setting. Set how the query errors are treated. 'validate' - Query errors cause the grant to be inapplicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                    "enum": [
                        "validate",
                        "error",
                        "critical"
                    ]
                },
                "equality": {
                    "description": "Expected value for they query to return.  If the query result matches this value the grant is a considered applicable to the request."
                },
                "data": {
                    "type": "object",
                    "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
                },
                "context_schema": {
                    "$ref": "https://json-schema.org/draft/2020-12/schema"
                },
                "context_validation": {
                    "type": "string",
                    "title": "Grant-Level Context Validation",
                    "description": "Grant-level context validation setting. Set how the request context is validated against the grant context schema. 'none' - there is no validation. 'validate' - Context is validated and if the context is invalid, the grant is not applicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                    "enum": [
                        "none",
                        "validate",
                        "error",
                        "critical"
                    ]
                }
            }
        }
        ```
    - On the base schema, the `properties.actions.items` is given an `enum` property that consists of the set of all available actions from all resource definitions

- **Error Schema** 
    - Start with a base schema
        ```json
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Workflow Errors",
            "description": "Errors returned from Authzee workflows.",
            "type": "object",
            "additionalProperties": false,
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
                    "items": {
                        "title": "Context Error",
                        "description": "Error when the request context is not valid against the expected context for the grant.",
                        "type": "object",
                        "additionalProperties": false,
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
                },
                "definition": {
                    "type": "array",
                    "items": {
                        "title": "Definition Error",
                        "description": "Error when an identity or resource definition is not valid.",
                        "type": "object",
                        "additionalProperties": false,
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
                            "definition": {}
                        }
                    }
                },
                "grant": {
                    "type": "array",
                    "items": {
                        "title": "Grant Error",
                        "description": "Error when an grant is not valid.",
                        "type": "object",
                        "additionalProperties": false,
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
                            "grant": {}
                        }
                    }
                },
                "jmespath": {
                    "type": "array",
                    "items": {
                        "title": "JMESPath Error",
                        "description": "Error when a JMESPath query for a grant produces an error.",
                        "type": "object",
                        "additionalProperties": false,
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
                },
                "request": {
                    "type": "array",
                    "items": {
                        "title": "Workflow Request Error",
                        "description": "Error when a request is not valid.",
                        "type": "object",
                        "additionalProperties": false,
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
                }
            },
            "$defs": {
                "grant": {}
            }
        }
        ```
    - On the base schema, the `$defs.grant` property is set to the grant schema generated before this.

- **Request Schema**
    - Start with a base schema
        ```json
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Workflow Request",
            "description": "Request for an Authzee workflow.",
            "anyOf": [],
            "$defs": {
                "identities": {
                    "type": "object",
                    "additionalProperties": false,
                    "required": [],
                    "properties": {}
                },
                "query_validation": {
                    "type": "string",
                    "title": "Request-Level Query Validation Setting",
                    "description": "Request-level query validation setting. Overrides grant-level settings for query validation. Set how the query errors are treated. 'grant' - Use the grant level query validation setting. 'validate' - Query errors cause the grant to be inapplicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                    "enum": [
                        "grant",
                        "validate",
                        "error",
                        "critical"
                    ]
                },
                "context": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-zA-Z0-9_]{1,256}$": {}
                    }
                },
                "context_validation": {
                    "type": "string",
                    "title": "Request-Level Context Validation",
                    "description": "Request-level context validation setting. Overrides grant-level settings for context validation. Set how the request context is validated against the grant context schema. 'grant' - Use the grant level context validation setting. 'none' - There is no validation. 'validate' - Context is validated and if the context is invalid, the grant is not applicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                    "enum": [
                        "grant",
                        "none",
                        "validate",
                        "error",
                        "critical"
                    ]
                }
            }
        }
        ```
    - For each resource definition:
        - Start with a resource base schema 
            ```json
            {
                "title": "'{{ resource_type }}' Resource Type Workflow Request",
                "description": "'{{ resource_type }}' resource type request for an Authzee workflow.",
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "identities",
                    "resource_type",
                    "action",
                    "resource",
                    "parents",
                    "children",
                    "query_validation",
                    "context",
                    "context_validation"
                ],
                "properties": {
                    "identities": {
                        "$ref": "#/$defs/identities"
                    },
                    "action": {
                        "type": "string" 
                    },
                    "resource_type": {
                        "const": "{{ resource_type }}" 
                    },
                    "resource": {
                        "$ref": "#/$defs/{{ resource_type }}"
                    }, 
                    "parents": {
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {}
                    }, 
                    "children": {
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {}
                    },
                    "query_validation": {
                        "$ref": "#/$defs/query_validation"
                    },
                    "context": {
                        "$ref": "#/$defs/context"
                    },
                    "context_validation": {
                        "$ref": "#/$defs/context_validation"
                    }
                }
            }
            ```
        - Replace all occurrences of `{{ resource_type }}` with the resource definition `resource_type`.
        - On the resource base schema, update the `properties.actions.enum` value as the resource definition `actions` field value
        - On the request base schema, add a field `$defs.{{ resource_type }}` with the value of the resource definition `schema` field, where `{{ resource_type }}` is replaced with the resource definition `resource_type`
        - For each Parent type in the resource definition `parent_types` field
            - Append the parent type to the resource base schema `properties.parents.required` array.
            - Create the new field on the resource base schema `properties.parents.properties.{{ parent_type }}` with value set to 
                ```json
                {
                    "type": "array",
                    "items": {
                        "$ref": "#/$defs/{{ parent_type }}"
                    }
                }
                ```
                replacing all occurrences of `{{ parent_type }}` with the parent type
        - For each Child type in the resource definition `child_types` field
            - Append the child type to the resource base schema `properties.children.required` array.
            - Create the new field on the resource base schema `properties.children.properties.{{ child_type }}` with value set to 
                ```json
                {
                    "type": "array",
                    "items": {
                        "$ref": "#/$defs/{{ child_type }}"
                    }
                }
                ```
                replacing all occurrences of `{{ child_type }}` with the child type
        - Append this base schema to the request schema `anyOf` field array.

### 4. Create Grants 

Define Grants as show above.

### 5. Validate Grants

Ensure grants are valid using the previously generated schemas and other checks.

- See `validate_grants(grants, schema)` in the reference implementation
- For each grant, validate against the grant schema generated in step 3.
- If any errors occur during validation of this step:
    -  add them to the result `errors.grant` field array as critical errors. 
    - After this step completes, exit the workflow.
    - Set the error `grant` field to the invalid grant.


### 6. Create Request

Build an authorization request as show above.

### 7. Validate Request
Ensure the request is valid using the previously generated request schema and other checks.
- See `validate_request(validate_request, schema)` in the reference implementation
- Validate the request against the request schema generated in step 3.
- If any errors occur during validation of this step:
    - add them to the result `errors.definition` field array as critical errors
    - After this step is complete, exit the workflow.


## Grant Evaluations

A common step to workflows is to evaluate a grant against a request to see if they are applicable. 

For a grant to be applicable it must follow this logic:

1. The request action is in the grant's `actions` field, or the grant's `actions` field is empty.
    - If not the grant is not applicable
2. The context validation setting is set to the grant's `context_validation` if the request's `context_validation` is set to grant, or else it is set to the request's value.
3. If the context validation is set to `"none"` then go to step 5.
4. If the context is invalid, and context validation is set to:
    - `"validate"` - The grant is not applicable.
    - `"error"` - The grant is not applicable and an error is added to the results `errors.context` field array.
    - `"critical"` - The grant is not applicable and a critical error is added to the results. This will cause the workflow to exit immediately.
5. The given JMESPath search function is used to run the query under the grant's `query` field against the request and current grant data 
    - as so:
        ```json
        {
            "grant": {{ grant data }},
            "request": {{ request data }}
        }
        ```
    - For example: To access the grant actions in the query you would use `grant.actions`.  To access the request resource type you would use `request.resource_type`. 

6. If the JMESPath search produces an error and the query validation is set to:
    - `"validate"` - The grant is not applicable.
    - `"error"` - The grant is not applicable and an error is added to the results
    - `"critical"` - the grant is not applicable and a critical error is added to the results.  The workflow immediately exits.
7. If the JMESPath result equals the grant's `equality` field value, then the grant is considered applicable.  If it does not match, then the grant is not applicable to the request.


## Workflow Errors

Workflows return the same format of error results. 
Error schemas are generated based on identity and resource definitions. 

```json
{
    "other_workflow_field": {},
    "errors": {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

Under the `errors` field is an object where each field is an error type.

- [Context Error](#context-error)
- [Definition Error](#definition-error)
- [Grant Error](#grant-error)
- [JMESpath Error](#jmespath-error)
- [Request Error](#request-error)


### Context Error

An error occurred when validating the request context against a grant context schema.

```json
{
    "errors": {
        "context": [
            {
                "message": "'request_source' is a required property",
                "critical": false,
                "grant": {
                    "effect": "allow",
                    "actions": [
                        "read"
                    ],
                    "query": "true",
                    "query_validation": "error",
                    "equality": true,
                    "data": {},
                    "context_schema": {
                        "type": "object",
                        "properties": {
                            "request_source": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "request_source"
                        ]
                    },
                    "context_validation": "error"
                }
            }
        ],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

| Field    | Type    | Required | Description                                                                          |
|----------|---------|:--------:|--------------------------------------------------------------------------------------|
| message  | string  | ✅       | A message describing the error.                                                      |
| critical | boolean | ✅       | A flag for if the error is critical. Critical errors will cause a workflow to halt. |
| grant    | object<[Grant](#grants)>  | ✅       | The grant whose context schema did not match the requests context.                   |


### Definition Error

An error occurred when validating an identity or resource definitions.

```json
{
    "errors": {
        "context": [],
        "definition": [
            {
                "message": "Identity types must be unique. 'User' is present more than once.",
                "critical": true,
                "definition_type": "identity",
                "definition": {
                    "identity_type": "User",
                    "schema": {
                        "type": "object"
                    }
                }
            }
        ],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

| Field           | Type    | Required | Description                                                                          |
|-----------------|---------|:--------:|--------------------------------------------------------------------------------------|
| message         | string  | ✅       | A message describing the error.                                                      |
| critical        | boolean | ✅       | A flag for if the error is critical.  Critical errors will cause a workflow to halt. |
| definition_type | string  | ✅       | The definition type that did not pass validation. `identity` or `resource`           |
| definition      | any     | ✅       | The value passed as the definition that did not pass validation.                     |


### Grant Error

An error occurred when validating a grant. 

```json
{
    "errors": {
        "context": [],
        "definition": [],
        "grant": [
            {
                "message": "The grant is not valid. Schema Error: 'invalid_action' is not one of ['read', 'inflate', 'deflate', 'pop', 'tie']",
                "critical": true,
                "grant": {
                    "effect": "allow",
                    "actions": [
                        "invalid_action"
                    ],
                    "query": "true",
                    "query_validation": "error",
                    "equality": true,
                    "data": {},
                    "context_schema": {
                        "type": "object"
                    },
                    "context_validation": "none"
                }
            }
        ],
        "jmespath": [],
        "request": []
    }
}
```

| Field    | Type    | Required | Description                                                                          |
|----------|---------|:--------:|--------------------------------------------------------------------------------------|
| message  | string  | ✅       | A message describing the error.                                                      |
| critical | boolean | ✅       | A flag for if the error is critical.  Critical errors will cause a workflow to halt. |
| grant    | any     | ✅       | The value that did not pass the grant validation.                                    |


### JMESPath Error

An error occurred when running the JMESPath query while evaluating a grant.

```json
{
    "errors": {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [
            {
                "message": "Invalid function name: invalid_function",
                "critical": false,
                "grant": {
                    "effect": "allow",
                    "actions": [
                        "read"
                    ],
                    "query": "invalid_function(request.identities.User[0].department)",
                    "query_validation": "error",
                    "equality": true,
                    "data": {},
                    "context_schema": {
                        "type": "object"
                    },
                    "context_validation": "none"
                }
            }
        ],
        "request": []
    }
}
```

| Field    | Type    | Required | Description                                                                          |
|----------|---------|:--------:|--------------------------------------------------------------------------------------|
| message  | string  | ✅       | A message describing the error.                                                      |
| critical | boolean | ✅       | A flag for if the error is critical. Critical errors will cause a workflow to halt. |
| grant    | object<[Grant](#grants)>| ✅       | The grant whose query resulted in a JMESPath error.                                  |


### Request Error

An error occurred when validating a request.

```json
{
    "errors": {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": [
            {
                "message": "The request is not valid for the request schema: 'invalid_action' is not one of ['read', 'inflate', 'deflate', 'pop', 'tie']",
                "critical": true
            }
        ]
    }
}
```

| Field    | Type    | Required | Description                                                                          |
|----------|---------|:--------:|--------------------------------------------------------------------------------------|
| message  | string  |    ✅    | A message describing the error.                                                      |
| critical | boolean |    ✅    | A flag for if the error is critical.  Critical errors will cause a workflow to halt. |



## Audit Workflow

The Audit Workflow is used to evaluate grants against a request, collect applicable grants, and collect errors. 

There are 8 steps.  The first 7 steps are same as in [Common Workflow Steps](#common-workflow-steps) except Step 3.

The Audit result schema is generated in addition to the others schemas
**Audit Result Schema**
- Start with a base schema 
    ```json
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Audit Response",
        "description": "Response for the audit workflow.",
        "type": "object",
        "additionalProperties": false,
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
            "errors": {}
        },
        "$defs": {
            "grant": {}
        }
    }
    ```
- Copy the previously generated errors schema from earlier, remove the `$defs` field, then set the audit result schema `properties.errors` value to the copied error schema.
- Set the audit result schema `$defs.grant` value to the grant schema generated earlier.

After the first 7 steps are complete then the Audit step starts.

**Audit**: Evaluate the request against all grants and collect the applicable grants and errors as the result.
- For each grant:
    - Evaluate the grant against the request
    - Capture any errors
    - If a critical error is captured, then exit early.
    - If a grant is applicable append it to the results `grant` field.
- The result will be valid against the Audit result schema generated in step 3. The fields are determined by the logic in the descriptions.


### Audit Workflow Result


```json
{
    "completed": true,
    "grants": [
        {
            "effect": "allow",
            "actions": [
                "read"
            ],
            "query": "request.identities.User[0].department == request.resource.owner_department",
            "query_validation": "error",
            "equality": true,
            "data": {
                "rule_name": "department_access"
            },
            "context_schema": {
                "type": "object"
            },
            "context_validation": "none"
        }
    ],
    "errors": {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

| Field | Type | Required | Description |
|---|---|:-:|---|
| completed | boolean | ✅ | If the workflow completed. |
| grants | array[object<[Grant](#grants)>] | ✅ | The grants that are applicable to the request. |
| errors | object<[Workflow Errors](#workflow-errors)> | ✅ | The collected workflow errors. |


## Authorize Workflow

The Authorize Workflow is used to check if a request is authorized. 

There are 8 steps.  The first 7 steps are same as in [Common Workflow Steps](#common-workflow-steps) except step 3. The Authorization Result schema is generated in addition to the others.
**Authorization Result Schema**
- Start with a base schema 
    ```json
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Authorize Response",
        "description": "Response for the authorize workflow.",
        "type": "object",
        "additionalProperties": false,
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
            "errors": {}
        },
        "$defs": {
            "grant": {}
        }
    }
    ```
- Copy the previously generated errors schema from earlier, remove the `$defs` field, then set the authorize result schema `properties.errors` value to the copied error schema.
- Set the audit result schema `$defs.grant` value to the grant schema generated earlier.

After those are complete the **Authorize** step runs.
Evaluate the request against until an authorization decision is determined.
- For each grant:
    - Evaluate the grant against the request
    - Capture any errors
    - If a critical error is captured, then exit early.  The request is not authorized.
- For the workflow to complete it must reach one of these conditions:
    - If a deny grant is applicable, the request is not authorized.
    - If a allow grant is applicable, and no deny grants are applicable, the request is authorized.
    - If no grants are applicable, the request is implicitly denied and it is not authorized.
- The result will be valid against the Authorize result schema generated in step 3. The fields are determined by the logic in the descriptions.

### Authorize Workflow Result

```json
{
    "authorized": true,
    "completed": true,
    "grant": {
        "effect": "allow",
        "actions": [
            "inflate"
        ],
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
        "query_validation": "error",
        "equality": true,
        "data": {
            "rule_name": "department_balloon_access",
            "created_by": "party_team"
        },
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    },
    "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
    "errors": {
        "context": [],
        "definition": [],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

| Field | Type | Required | Description |
|---|---|:-:|---|
| authorized | boolean | ✅ | If the request is authorized. |
| completed | boolean | ✅ | If the workflow completed. |
| grant | object<[Grant](#grants)> \| null | ✅ | The grant whose evaluation that led to the authorization decision, if applicable. |
| message | string | ✅ | The authorization message and reasoning. |
| errors | object<[Workflow Errors](#workflow-errors)> | ✅ | The collected workflow errors. |


