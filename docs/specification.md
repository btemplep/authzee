# Authzee Specification 
## Version 0.3.0

This document describes the specification for **Authzee**.

For a quick introduction to the core Authzee engine see the [README](../README). 

For language specific use and guidance see the [SDKs](./sdks)

Authzee is a highly expressive grant-based authorization engine.  It uses JSON Schemas (Draft 2020-12) to define and validate all inputs and outputs. Grants are evaluated against the request data and grant data using a JSON query language of your choice to make access control decisions. JMESpath is preferred because it has a specification and is extensible.

Authzee offers several standard *operations*.  A common use case is the "Authorize" operation which determines authorization.  These *operations* are fed *requests*.  *Requests* consist of Identities, a resource action, a resource type, a resource instance, a context type, and a context instance.  Identities are a way to describe a *calling entity's* identities.  They could be user, groups, roles, etc.  Resources represents resources that need to be authorized for.  Resource actions are actions that are performed on those resources. Context is a way to pass extra structured data into a request.  Identities, resources, and contexts are defined as needed.  These are then validated and can be used to validate requests.  The request are then passed to the operations like authorize, along with *grants*.  Grants are used to define authorization rules. 


## Specification Guidance and Limitations

- This is the Authzee Specification. It is not the best or most efficient way to use Authzee.  It is a succinct description of Authzee functionality that is hopefully presented in an implementation agnostic fashion.  
- Not all of the functionality described here is meant to be part of an implementation's "public" API.  It is just to establish standards for Authzee. 
- Case conventions can be changed to align with language conventions.
- Input and output data structures can have additional properties where allowed in their respective schemas.  Implementations are expected to build upon the base schemas. 
- Errors and especially critical errors are left up to implementations to decide the method of presenting the error. Whether it is directly returned from a function, raised via an exception, or by other means. 
    - Errors and results are still expected to follow the schemas laid out here. 
    - For example, an "Authorize" operation that encounters a critical error should always include the result matching the Authorize Result Schema when the error is presented. 
    - For something like a validation error on an identity, the return value or exception should include a data structure that matches the Definition Error Schema.
- Titles and descriptions included in the schema fields are considered part of the spec.  Check the schemas first for detailed information on the fields. 


### Table of Contents

- [Definition of Terms](#definition-of-terms)
- [Context Definitions](#context-definitions)
    - [Context Definition Example](#context-definition-example)
    - [Context Definition Schema](#context-definition-schema)
    - [Context Definition Validation](#context-definition-validation)
- [Identity Definitions](#identity-definitions)
    - [Identity Definition Example](#identity-definition-example)
    - [Identity Definition Schema](#identity-definition-schema)
    - [Identity Definition Validation](#identity-definition-validation)
- [Resource Definitions](#resource-definitions)
    - [Resource Definition Example](#resource-definition-example)
    - [Resource Definition Schema](#resource-definition-schema)
    - [Resource Definition Validation](#resource-definition-validation)
- [Grants](#grants)
    - [Grant Example](#grant-example)
    - [Grant Schema](#grant-schema)
    - [Grant Validation](#grant-validation)
- [Requests](#requests)
    - [Request Example](#request-example)
    - [Request Schema](#request-schema)
    - [Request Validation](#request-validation)
- [Batch Requests](#batch-requests)
    - [Batch Request Example](#batch-request-example)
    - [Batch Request Schema](#batch-request-schema)
    - [Batch Request Validation](#batch-request-validation)
- [Evaluations](#evaluations)
    - [Request Evaluation](#request-evaluation)
    - [Batch Request Evaluation](#batch-request-evaluation)
- [Operations](#operations)
    - [Audit](#audit)
        - [Audit Result Example](#audit-result-example)
        - [Audit Result Schema](#audit-result-schema) 
    - [Authorize](#authorize)
        - [Authorize Result Example](#authorize-result-example)
        - [Authorize Result Schema](#authorize-result-schema) 
    - [Batch Audit](#batch-audit)
        - [Batch Audit Result Example](#batch-audit-result-example)
        - [Batch Audit Result Schema](#batch-audit-result-schema) 
    - [Batch Authorize](#batch-authorize)
        - [Batch Authorize Result Example](#batch-authorize-result-example)
        - [Batch Authorize Result Schema](#batch-authorize-result-schema) 
- [Errors](#errors)
    - [Error Types](#error-types)
    - [Error Example](#error-example)
    - [Error Schema](#error-schema)



## Definition of Terms

Definitions specific to Authzee and used throughout the specification:

- **Identity** - An object representing a specific type of identity to consider when authorizing.
- **Resource** - An object representing a specific type of resource to authorize for.
- **Resource Action (Action)** - A name for a specific action taken on a resource.
- **Grant** - Defines rules for authorization. 
- **Operation (Op)** - Distinct, named authorization functionality for a request. Audit, Authorize, Batch Audit, and Batch Authorize.
- **Authorization Request (Request)** - The object used to specify identities, resources, actions, and other configurations that are passed to functions.
- **Request Evaluation** - When a request data structure is evaluated against a grant to determine if the grant is applicable to the request.
- **Calling Entity (Entity)** - Who or what is represented by a request.  A calling entity can have many identities of the same and different types. 



## Context Definitions

Context is included in requests as extra structured data.  The definition included a unique context type name, and the schema for the request context.

### Context Definition Example

```json
{
    "context_type": "MyExampleContext",
    "schema": {
        "type": "object",
        "properties": {
            "myProperty": {
                "type": "string"
            }
        }
    }
}
```


### Context Definition Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Context Definition",
    "description": "A request context definition.  Defines a type of context that can be passed with Authzee requests.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "context_type",
        "schema"
    ],
    "properties": {
        "context_type": {
            "title": "Authzee Context Type",
            "description": "A unique name to identity this context type.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://json-schema.org/draft/2020-12/schema",
            "$vocabulary": {
                "https://json-schema.org/draft/2020-12/vocab/core": true,
                "https://json-schema.org/draft/2020-12/vocab/applicator": true,
                "https://json-schema.org/draft/2020-12/vocab/unevaluated": true,
                "https://json-schema.org/draft/2020-12/vocab/validation": true,
                "https://json-schema.org/draft/2020-12/vocab/meta-data": true,
                "https://json-schema.org/draft/2020-12/vocab/format-annotation": true,
                "https://json-schema.org/draft/2020-12/vocab/content": true
            },
            "$dynamicAnchor": "meta",
            "title": "Core and Validation specifications meta-schema",
            "allOf": [
                {
                    "$ref": "meta/core"
                },
                {
                    "$ref": "meta/applicator"
                },
                {
                    "$ref": "meta/unevaluated"
                },
                {
                    "$ref": "meta/validation"
                },
                {
                    "$ref": "meta/meta-data"
                },
                {
                    "$ref": "meta/format-annotation"
                },
                {
                    "$ref": "meta/content"
                }
            ],
            "type": [
                "object",
                "boolean"
            ],
            "$comment": "This meta-schema also defines keywords that have appeared in previous drafts in order to prevent incompatible extensions as they remain in common use.",
            "properties": {
                "definitions": {
                    "$comment": "\"definitions\" has been replaced by \"$defs\".",
                    "type": "object",
                    "additionalProperties": {
                        "$dynamicRef": "#meta"
                    },
                    "deprecated": true,
                    "default": {}
                },
                "dependencies": {
                    "$comment": "\"dependencies\" has been split and replaced by \"dependentSchemas\" and \"dependentRequired\" in order to serve their differing semantics.",
                    "type": "object",
                    "additionalProperties": {
                        "anyOf": [
                            {
                                "$dynamicRef": "#meta"
                            },
                            {
                                "$ref": "meta/validation#/$defs/stringArray"
                            }
                        ]
                    },
                    "deprecated": true,
                    "default": {}
                },
                "$recursiveAnchor": {
                    "$comment": "\"$recursiveAnchor\" has been replaced by \"$dynamicAnchor\".",
                    "$ref": "meta/core#/$defs/anchorString",
                    "deprecated": true
                },
                "$recursiveRef": {
                    "$comment": "\"$recursiveRef\" has been replaced by \"$dynamicRef\".",
                    "$ref": "meta/core#/$defs/uriReferenceString",
                    "deprecated": true
                }
            }
        }
    }
}
```


### Context Definition Validation

Context definitions are valid if all of the following conditions are met:
- The definition is valid against the context definition schema
- The definition's `context_type` is unique among context definitions
- The definition schema's base type is "object"

If an error occurs when validating an context definition, a critical, `definition` type [Error](#errors) should be returned/raised.


## Identity Definitions

Identity definitions describe the types of identities that a calling entity possesses to make requests. These represent "who" is trying to access the resources. Each identity type has a unique name and a JSON Schema that validates the structure and contents of identity objects that are passed in requests.

**Common Identity Types:**
- **Users**: Individual people with attributes like ID, email, department, roles
- **Groups**: Collections of users with shared characteristics (teams, departments, projects)
- **Roles**: Permission sets that define what actions can be performed
- **Applications**: Systems or services that act on behalf of users
- **API Keys**: Programmatic access tokens with associated permissions

This can also be extended to Identity Provider specific identities like **EntraGroup**, **OktaRole**, **ADUser**

Identity definitions enable flexible representation of complex organizational structures and permission models.

### Identity Definition Example

```json
{
    "identity_type": "User",
    "schema": {
        "type": "object",
        "additionalProperties": true,
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


### Identity Definition Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Identity Definition",
    "description": "An identity definition.  Defines a type of identity to use with Authzee.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "identity_type",
        "schema"
    ],
    "properties": {
        "identity_type": {
            "title": "Authzee Identity Type",
            "description": "A unique name to identity this identity type.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://json-schema.org/draft/2020-12/schema",
            "$vocabulary": {
                "https://json-schema.org/draft/2020-12/vocab/core": true,
                "https://json-schema.org/draft/2020-12/vocab/applicator": true,
                "https://json-schema.org/draft/2020-12/vocab/unevaluated": true,
                "https://json-schema.org/draft/2020-12/vocab/validation": true,
                "https://json-schema.org/draft/2020-12/vocab/meta-data": true,
                "https://json-schema.org/draft/2020-12/vocab/format-annotation": true,
                "https://json-schema.org/draft/2020-12/vocab/content": true
            },
            "$dynamicAnchor": "meta",
            "title": "Core and Validation specifications meta-schema",
            "allOf": [
                {
                    "$ref": "meta/core"
                },
                {
                    "$ref": "meta/applicator"
                },
                {
                    "$ref": "meta/unevaluated"
                },
                {
                    "$ref": "meta/validation"
                },
                {
                    "$ref": "meta/meta-data"
                },
                {
                    "$ref": "meta/format-annotation"
                },
                {
                    "$ref": "meta/content"
                }
            ],
            "type": [
                "object",
                "boolean"
            ],
            "$comment": "This meta-schema also defines keywords that have appeared in previous drafts in order to prevent incompatible extensions as they remain in common use.",
            "properties": {
                "definitions": {
                    "$comment": "\"definitions\" has been replaced by \"$defs\".",
                    "type": "object",
                    "additionalProperties": {
                        "$dynamicRef": "#meta"
                    },
                    "deprecated": true,
                    "default": {}
                },
                "dependencies": {
                    "$comment": "\"dependencies\" has been split and replaced by \"dependentSchemas\" and \"dependentRequired\" in order to serve their differing semantics.",
                    "type": "object",
                    "additionalProperties": {
                        "anyOf": [
                            {
                                "$dynamicRef": "#meta"
                            },
                            {
                                "$ref": "meta/validation#/$defs/stringArray"
                            }
                        ]
                    },
                    "deprecated": true,
                    "default": {}
                },
                "$recursiveAnchor": {
                    "$comment": "\"$recursiveAnchor\" has been replaced by \"$dynamicAnchor\".",
                    "$ref": "meta/core#/$defs/anchorString",
                    "deprecated": true
                },
                "$recursiveRef": {
                    "$comment": "\"$recursiveRef\" has been replaced by \"$dynamicRef\".",
                    "$ref": "meta/core#/$defs/uriReferenceString",
                    "deprecated": true
                }
            }
        }
    }
}
```

### Identity Definition Validation

Identity definitions are valid if all of the following conditions are met:
- The definition is valid against the identity definition schema
- The definition's `identity_type` is unique among identity definitions
- The definition schema's base type is "object"

If an error occurs when validating an identity definition, a critical, `definition` type [Error](#errors) should be returned/raised.


## Resource Definitions 

Resource definitions describe the types of resources that can be accessed and what actions can be performed on them. These represent "what" is being accessed. 


### Resource Definition Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Resource Definition",
    "description": "A resource definition.  Defines a type of resource to use with Authzee.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "resource_type",
        "actions",
        "schema"
    ],
    "properties": {
        "resource_type": {
            "title": "Authzee Resource Type",
            "description": "A unique name to identity this resource type.",
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
                "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                "type": "string",
                "pattern": "^[A-Za-z0-9_.:-]*$",
                "minLength": 1,
                "maxLength": 512
            }
        },
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://json-schema.org/draft/2020-12/schema",
            "$vocabulary": {
                "https://json-schema.org/draft/2020-12/vocab/core": true,
                "https://json-schema.org/draft/2020-12/vocab/applicator": true,
                "https://json-schema.org/draft/2020-12/vocab/unevaluated": true,
                "https://json-schema.org/draft/2020-12/vocab/validation": true,
                "https://json-schema.org/draft/2020-12/vocab/meta-data": true,
                "https://json-schema.org/draft/2020-12/vocab/format-annotation": true,
                "https://json-schema.org/draft/2020-12/vocab/content": true
            },
            "$dynamicAnchor": "meta",
            "title": "Core and Validation specifications meta-schema",
            "allOf": [
                {
                    "$ref": "meta/core"
                },
                {
                    "$ref": "meta/applicator"
                },
                {
                    "$ref": "meta/unevaluated"
                },
                {
                    "$ref": "meta/validation"
                },
                {
                    "$ref": "meta/meta-data"
                },
                {
                    "$ref": "meta/format-annotation"
                },
                {
                    "$ref": "meta/content"
                }
            ],
            "type": [
                "object",
                "boolean"
            ],
            "$comment": "This meta-schema also defines keywords that have appeared in previous drafts in order to prevent incompatible extensions as they remain in common use.",
            "properties": {
                "definitions": {
                    "$comment": "\"definitions\" has been replaced by \"$defs\".",
                    "type": "object",
                    "additionalProperties": {
                        "$dynamicRef": "#meta"
                    },
                    "deprecated": true,
                    "default": {}
                },
                "dependencies": {
                    "$comment": "\"dependencies\" has been split and replaced by \"dependentSchemas\" and \"dependentRequired\" in order to serve their differing semantics.",
                    "type": "object",
                    "additionalProperties": {
                        "anyOf": [
                            {
                                "$dynamicRef": "#meta"
                            },
                            {
                                "$ref": "meta/validation#/$defs/stringArray"
                            }
                        ]
                    },
                    "deprecated": true,
                    "default": {}
                },
                "$recursiveAnchor": {
                    "$comment": "\"$recursiveAnchor\" has been replaced by \"$dynamicAnchor\".",
                    "$ref": "meta/core#/$defs/anchorString",
                    "deprecated": true
                },
                "$recursiveRef": {
                    "$comment": "\"$recursiveRef\" has been replaced by \"$dynamicRef\".",
                    "$ref": "meta/core#/$defs/uriReferenceString",
                    "deprecated": true
                }
            }
        }
    }
}
```

### Resource Definition Example

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
    }
}
```


### Resource Definition Validation

Resource definitions are valid if all of the following conditions are met:
- The definition is valid against the resource definition schema
- The definition's `resource_type` is unique among resource definitions
- The definition schema's base type is "object"

If an error occurs when validating an resource definition, a critical, `definition` type [Error](#errors) should be returned/raised.


## Grants

Grants are the Authzee unit of authorization. They query the request and grant data using the specified JSON query language. 


### Grant Example

```json
{
    "effect": "allow",
    "actions": [
        "Balloon:Inflate"
    ],
    "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
    "evaluation_handler": "evaluate",
    "equality": true,
    "data": {
        "allowed_departments": [
            "Maintenance",
            "Balloon Sales"
        ]
    }
}
```


### Grant Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Grant",
    "description": "A grant is an object representing enacted authorization rules.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "effect",
        "actions",
        "data",
        "query",
        "evaluation_handler",
        "equality"
    ],
    "properties": {
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
        },
        "actions": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "title": "Resource Action",
                "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                "type": "string",
                "pattern": "^[A-Za-z0-9_.:-]*$",
                "minLength": 1,
                "maxLength": 512
            },
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
        "evaluation_handler": {
            "title": "Grant-Level Evaluation Handler Setting",
            "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
            "type": "string",
            "enum": [
                "evaluate",
                "error",
                "critical"
            ]
        },
        "equality": {
            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
        }
    }
}
```


### Grant Validation

Grant are valid if all of the following conditions are met:
- The grant is valid against the grant schema

> **NOTE** - Grant actions are not validated so that grants can be created for future resource actions, and for performance purposes in the SDKs. 

If an error occurs when validating a grant, a critical, `grant` type [Error](#errors) should be returned/raised.


## Requests

Requests represent a calling entity's request for perform an operation on identities, an action, a resource type, a resource instance, a context type, and a context instance. 


### Request Example

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
            },
            {
                "name": "balloon-reader",
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
    "action": "inflate",
    "resource_type": "Balloon",
    "resource": {
        "id": "balloon456",
        "color": "red",
        "size": "large",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": false
    },
    "evaluation_handler": "error",
    "context_type": "event",
    "context": {
        "request_source": "web_ui",
        "timestamp": "2023-12-07T10:30:00Z",
        "event_type": "birthday_party"
    }
}
```

### Request Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authzee Operation Request",
    "description": "Request for an Authzee Operation.",
    "additionalProperties": false,
    "required": [
        "identities",
        "action",
        "resource_type",
        "resource",
        "context_type",
        "context",
        "evaluation_handler"
    ],
    "properties": {
        "identities": {
            "description": "Object whose keys are the identity types, and values are an array of instances of that identity type.",
            "type": "object",
            "additionalProperties": false,
            "required": [],
            "patternProperties": {
                "^[A-Za-z0-9_]*$": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
        "action": {
            "title": "Resource Action",
            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_.:-]*$",
            "minLength": 1,
            "maxLength": 512
        },
        "resource_type": {
            "title": "Authzee Resource Type",
            "description": "A unique name to identity this resource type.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "resource": {
            "type": "object",
            "description": "Resource for the request that is an instance of the given resource_type."
        },
        "context_type": {
            "title": "Authzee Context Type",
            "description": "A unique name to identity this context type.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "context": {
            "type": "object",
            "description": "Context for the request that is an instance of the given context_type."
        },
        "evaluation_handler": {
            "title": "Request-Level Evaluation Error Handling Setting",
            "description": "Request-level Evaluation Handler Setting. Can be used to override grant level evaluation handling. 'grant' - Use the grant level setting. No override. 'evaluation' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result. 'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
            "type": "string",
            "enum": [
                "grant",
                "evaluate",
                "error",
                "critical"
            ]
        }
    }
}
```

### Request Validation

Requests are valid if all of the following conditions are met:
- The request is valid against the request schema
- The context type is equal to one of the passed in/registered context definition's context type.
- The context instance is valid against the schema of the matching context definition.
- All identity types are valid against passed in/registered identity definitions.
- All identity instances are valid against the schemas given in their respective passed in/registered identity definitions.
- The resource type is equal to one of the passed in/registered resource definition's resource type.
- The resource instance is valid against the schema of the matching resource definition.
- The resource action is equal to one of the actions in the matching resource definition.


If an error occurs when validating a request, a critical, `request` type [Error](#errors) should be returned/raised.


## Batch Requests

Batch requests represent a calling entity's request to perform an operation on a list of items with a specific action.  This includes the ability to specify the same or different fields for:
- Identities
- Resource Type
- Resource
- Query Validation
- Context Type
- Context

Grants are naturally partitioned on actions. Batch requests try to take advantage of this by balancing the time to retrieve grants vs the time to process them.

### Batch Request Example

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
                "name": "event-team",
                "department": "party_planning", 
                "type": "team"
            },
            {
                "name": "party-planning-dept",
                "department": "party_planning",
                "type": "department"
            }
        ],
        "Role": [
            {
                "name": "party-coordinator",
                "permissions": [
                    "balloon:read",
                    "balloon:inflate",
                    "balloon:tie"
                ],
                "level": "advanced"
            }
        ]
    },
    "action": "inflate",
    "resource_type": "Balloon",
    "resource": { 
        "id": "balloon123",
        "color": "green",
        "size": "medium",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": false
    },
    "context_type": "MySpecialContext",
    "context": {
        "Team": "ABC"
    },
    "evaluation_handler": "grant",
    "batch": [
        {
            "resource": { 
                "id": "balloon456",
                "color": "red",
                "size": "medium",
                "material": "latex",
                "owner_department": "party_planning",
                "inflated": false
            }
        },
        { 
            "identities": {
                "User": [
                    {
                        "id": "Store123",
                        "department": "Store 123",
                        "owner_department": "IDK",
                        "location": "Somewhere"
                    }
                ],
                "Group": [
                    {
                        "name": "My Special group",
                        "department": "special_dept", 
                        "type": "team"
                    }
                ]
            },
            "resource_type": "BalloonStore",
            "resource": {
                "id": "1234",
                "name": "Special store",
                "owner_department": "special_dept",
                "location": "Somewhere"
            },
            "context_type": "NULL", 
            "context":  {},
            "evaluation_handler": "error"
        },
        {} 
    ]  
}
```

### Batch Request Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Operation Request",
    "description": "Request for an Authzee Batch Operation.",
    "additionalProperties": true,
    "required": [
        "identities",
        "action",
        "resource_type",
        "resource",
        "context_type",
        "context",
        "evaluation_handler",
        "batch"
    ],
    "properties": {
        "identities": {
            "description": "Object whose keys are the identity types, and values are an array of instances of that identity type. Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value.",
            "type": "object",
            "additionalProperties": false,
            "required": [],
            "patternProperties": {
                "^[A-Za-z0-9_]*$": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
        "action": {
            "title": "Resource Action",
            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_.:-]*$",
            "minLength": 1,
            "maxLength": 512
        },
        "resource_type": {
            "title": "Authzee Resource Type",
            "description": "A unique name to identity this resource type. Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "resource": {
            "type": "object",
            "description": "Resource for the request that is an instance of the given resource_type. Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value."
        },
        "context_type": {
            "title": "Authzee Context Type",
            "description": "A unique name to identity this context type.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_]*$",
            "minLength": 1,
            "maxLength": 256
        },
        "context": {
            "type": "object",
            "description": "Context for the request that is an instance of the given context_type. Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value."
        },
        "evaluation_handler": {
            "title": "Request-Level Evaluation Error Handling Setting",
            "description": "Request-level Evaluation Handler Setting. Can be used to override grant level evaluation handling. 'grant' - Use the grant level setting. No override. 'evaluation' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result. 'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early. Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value.",
            "type": "string",
            "enum": [
                "grant",
                "evaluate",
                "error",
                "critical"
            ]
        },
        "batch": {
            "type": "array",
            "description": "Batch of resources and contexts to process with shared identities, action, resource type, and context type.",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": false,
                "required": [],
                "properties": {
                    "identities": {
                        "description": "Object whose keys are the identity types, and values are an array of instances of that identity type. Overrides the batch request level if the field exists and is not null.",
                        "type": [
                            "object",
                            "null"
                        ],
                        "additionalProperties": false,
                        "required": [],
                        "patternProperties": {
                            "^[A-Za-z0-9_]*$": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            }
                        }
                    },
                    "resource_type": {
                        "title": "Authzee Resource Type",
                        "description": "A unique name to identity this resource type. Overrides the batch request level if the field exists and is not null.",
                        "type": [
                            "string",
                            "null"
                        ],
                        "pattern": "^[A-Za-z0-9_]*$",
                        "minLength": 1,
                        "maxLength": 256
                    },
                    "resource": {
                        "type": "object",
                        "description": "Resource for this batch item, that is an instance of the given resource_type"
                    },
                    "context_type": {
                        "title": "Authzee Context Type",
                        "description": "A unique name to identity this context type. Overrides the batch request level if the field exists and is not null.",
                        "type": [
                            "string",
                            "null"
                        ],
                        "pattern": "^[A-Za-z0-9_]*$",
                        "minLength": 1,
                        "maxLength": 256
                    },
                    "context": {
                        "type": [
                            "object",
                            "null"
                        ],
                        "description": "Context for the request that is an instance of context_type. Overrides the batch request level if the field exists and is not null."
                    },
                    "evaluation_handler": {
                        "title": "Request-Level Evaluation Error Handling Setting",
                        "description": "Request-level Evaluation Handler Setting. Can be used to override grant level evaluation handling. 'grant' - Use the grant level setting. No override. 'evaluation' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result. 'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early. Overrides the batch request level if the field exists and is not null.",
                        "type": [
                            "string",
                            "null"
                        ],
                        "enum": [
                            "grant",
                            "evaluate",
                            "error",
                            "critical"
                        ]
                    }
                }
            }
        }
    }
}
```

### Batch Request Validation

Batch Requests are valid if all of the following conditions are met:
- The batch request is valid against the batch request schema
- All root fields are valid as outlined in [Request Validation](#request-validation).
- Each item in the batch is formatted into a standard request as outlined in [Batch Request Evaluation](#batch-request-evaluation), and then each request is valid as outlined in [Request Validation](#request-validation)

If an error occurs when validating a batch request at the top level, a critical, `request` type [Error](#errors) should be returned/raised. Besides that, the individual requests within a batch request are returned within the result items.


## Evaluations

Evaluations are the primary unit of work in Authzee.  Authzee operations evaluate requests against grants to determine if a grant is applicable to a request. What is done with the applicable grants is dependent on the operation.  


### Request Evaluation

> **NOTE**: Use of "AND" stands for logical AND.  Use of "OR" stands for logical OR.

Request evaluation requires that all inputs must be validated: identity definitions, resource definitions, context definitions, request/batch request, and grants.

Request evaluation requires the request, a grant, and an execute function.  

The execute function runs a JSON query on JSON data and returns the results. Here is an example in python where the `AnyJSON` type represents the python equivalent of all valid JSON types:

```python
def execute(expression: str, data: AnyJSON) -> AnyJSON:
    pass
```

Expected return schema for JSON query execute functions. 

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Result for a JSON query execute function",
    "description": "Result from evaluating a JSON query against the given input data.",
    "type": "object",
    "additionalProperties": false,
    "required": [
        "result",
        "has_failed",
        "error_message"
    ],
    "properties": {
        "result": {
            "description": "Result from running the JSON query."
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "error_message": {
            "type": [
                "string",
                "null"
            ],
            "description": "Details of why the query failed. `null` if there are no errors."
        }
    }
}
```

A grant is applicable to a request if all of the following are true:
- The grant has 0 actions OR the request action is in the grant actions.
- The JSON execute function is called with the grant's query as the `expression` parameter, along with the request and grant nested under an object as the `data` parameter like so: `execute(grant.query, {"request": <request body>, "grant": <grant_body>})` 
- The JSON query execute function call produces no errors
- The result of the JSON execute function is equal to the grant's equality property value

If an error occurs during an evaluation (generally from the JSON query), an `evaluation` type [Error](#errors) should be returned/raised.
This error is determined to be critical depending on the grant and request `evaluation_handler` setting. 

The error will be critical if any of the following are true or else it is not critical:
    - The request `evaluation_handler` is set to `grant` AND the grant `evaluation_handler` is set to `critical`
    - The request `evaluation_handler` is set to `critical`


### Batch Request Evaluation

Each item in a batch request is first formatted into a standard request, then processed like a normal [Request Evaluation](#request-evaluation).

Formatting a batch request into individual request:
- Create a request for each batch item 
- Each request starts with the fields from the batch item for the request.
- Any request fields that are not present at this point will be taken from the root batch request. 


### Evaluation Error Example

Errors that happen during an evaluation or running a JSON query will result in an `evaluation` error.  

```json
{
    "is_critical": true,
    "message": "A JSON query error occurred "
}
```


### Evaluation Error Schema

```json
{
    "title": "Evaluation Error",
    "description": "Error when an Authzee Evaluation fails.",
    "type": "object",
    "additionalProperties": false,
    "required": [
        "is_critical",
        "message"
    ],
    "properties": {
        "is_critical": {
            "type": "boolean",
            "description": "If this error is critical. Critical errors generally halt further operations."
        },
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        }
    }
}
```

## Operations

Operations are the core functionality of Authzee. Before running an Authzee operation, all relevant inputs must be validated as per this specification:

- Identity Definitions
- Resource Definitions
- Context Definitions
- Grants
- Request or Batch Request


### Audit

The Audit operation is used to collect grant evaluation results against a request. 

Audit Steps for each grant:
- The grants are added to the result.
- Each grant is evaluated against the request and the result is appended to the results. 
- If an error occurs and it is critical, `has_failed` is set to `true`, an error is added at the request level, and the operation exits.


#### Audit Result Example

```json
{
    "grants": [
        {
            "effect": "allow",
            "actions": [
                "inflate"
            ],
            "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
            "evaluation_handler": "error",
            "equality": true,
            "data": {}
        }
    ],
    "results": [
        {
            "is_applicable": true,
            "query_result": true,
            "errors": {}
        }
    ],
    "has_failed": false,
    "errors": {}
}
```

#### Audit Result Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Audit Result",
    "description": "Result for the audit operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "grants",
        "results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": {
            "type": "array",
            "description": "List of grants that have been processed for the request.",
            "items": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Grant",
                "description": "A grant is an object representing enacted authorization rules.",
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "effect",
                    "actions",
                    "data",
                    "query",
                    "evaluation_handler",
                    "equality"
                ],
                "properties": {
                    "effect": {
                        "type": "string",
                        "enum": [
                            "allow",
                            "deny"
                        ],
                        "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                    },
                    "actions": {
                        "type": "array",
                        "uniqueItems": true,
                        "items": {
                            "title": "Resource Action",
                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                            "type": "string",
                            "pattern": "^[A-Za-z0-9_.:-]*$",
                            "minLength": 1,
                            "maxLength": 512
                        },
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
                    "evaluation_handler": {
                        "title": "Grant-Level Evaluation Handler Setting",
                        "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                        "type": "string",
                        "enum": [
                            "evaluate",
                            "error",
                            "critical"
                        ]
                    },
                    "equality": {
                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                    }
                }
            }
        },
        "results": {
            "type": "array",
            "description": "List of grant evaluation results for each respective grant index.",
            "items": {
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "is_applicable",
                    "query_result",
                    "errors"
                ],
                "properties": {
                    "is_applicable": {
                        "type": "boolean",
                        "description": "If the grant is applicable to the request or not."
                    },
                    "query_result": {
                        "description": "Result from running the JSON query."
                    },
                    "errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations.",
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Operation Result Errors",
            "description": "Errors returned from Authzee Operations.",
            "type": "object",
            "additionalProperties": false,
            "required": [],
            "properties": {
                "query": {
                    "type": "array",
                    "items": {
                        "title": "Query Error",
                        "description": "Error when a JSON query fails.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [
                            "is_critical",
                            "message"
                        ],
                        "properties": {
                            "is_critical": {
                                "type": "boolean",
                                "description": "If this error is critical. Critical errors generally halt further operations."
                            },
                            "message": {
                                "type": "string",
                                "description": "Detailed message about what caused the error."
                            }
                        }
                    }
                }
            }
        }
    }
}
```

### Authorize

The Authorize operation gives an authorization decision for a request. 

By default, nothing is authorized in Authzee. 

A request is authorized if **all** of the following are true:
- A grant with an `allow` effect is applicable to the request
- No grants with a `deny` effect are applicable to the request. 
- No critical errors were encountered when processing the request.

A request is not authorized if **any** of the following are true:
- A grant with a `deny` effect is applicable to the request.
- No grants are applicable to the request. 
- A critical errors was encountered when processing the request.


#### Authorize Result Example

```json
{
    "is_authorized": true,
    "grant": {
        "effect": "allow",
        "actions": [
            "Balloon:Read",
            "pop"
        ],
        "query": "contains(request.identities.User[0].role, 'admin')",
        "evaluation_handler": "evaluate",
        "equality": true,
        "data": {}
    },
    "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
    "has_failed": false,
    "critical_errors": {}
}
```

#### Authorize Result Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authorize Result",
    "description": "Result for the authorize operation.",
    "type": "object",
    "additionalProperties": true,
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
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "title": "Grant",
                    "description": "A grant is an object representing enacted authorization rules.",
                    "type": "object",
                    "additionalProperties": true,
                    "required": [
                        "effect",
                        "actions",
                        "data",
                        "query",
                        "evaluation_handler",
                        "equality"
                    ],
                    "properties": {
                        "effect": {
                            "type": "string",
                            "enum": [
                                "allow",
                                "deny"
                            ],
                            "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                        },
                        "actions": {
                            "type": "array",
                            "uniqueItems": true,
                            "items": {
                                "title": "Resource Action",
                                "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                                "type": "string",
                                "pattern": "^[A-Za-z0-9_.:-]*$",
                                "minLength": 1,
                                "maxLength": 512
                            },
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
                        "evaluation_handler": {
                            "title": "Grant-Level Evaluation Handler Setting",
                            "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                            "type": "string",
                            "enum": [
                                "evaluate",
                                "error",
                                "critical"
                            ]
                        },
                        "equality": {
                            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                        }
                    }
                }
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
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "critical_errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Operation Result Errors",
            "description": "Errors returned from Authzee Operations.",
            "type": "object",
            "additionalProperties": false,
            "required": [],
            "properties": {
                "query": {
                    "type": "array",
                    "items": {
                        "title": "Query Error",
                        "description": "Error when a JSON query fails.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [
                            "is_critical",
                            "message"
                        ],
                        "properties": {
                            "is_critical": {
                                "type": "boolean",
                                "description": "If this error is critical. Critical errors generally halt further operations."
                            },
                            "message": {
                                "type": "string",
                                "description": "Detailed message about what caused the error."
                            }
                        }
                    }
                }
            }
        }
    }
}
```

### Batch Audit

The Batch Audit operation is used to run the Audit operation over a batch request with the same list of grants. 


#### Batch Audit Result Example

```json
{
    "grants": [
        {
            "effect": "allow",
            "actions": [
                "inflate"
            ],
            "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
            "evaluation_handler": "error",
            "equality": true,
            "data": {}
        }
    ],
    "batch_results": [
        {
            "results": [
                {
                    "is_applicable": true,
                    "query_result": true,
                    "errors": {}
                }
            ],
            "has_failed": false,
            "errors": {}
        }
    ],
    "has_failed": false,
    "errors": {}
}
```


#### Batch Audit Result Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Audit Result",
    "description": "Result for the Batch Audit Operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "grants",
        "batch_results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": {
            "type": "array",
            "description": "List of grants that have been processed for the request.",
            "items": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Grant",
                "description": "A grant is an object representing enacted authorization rules.",
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "effect",
                    "actions",
                    "data",
                    "query",
                    "evaluation_handler",
                    "equality"
                ],
                "properties": {
                    "effect": {
                        "type": "string",
                        "enum": [
                            "allow",
                            "deny"
                        ],
                        "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                    },
                    "actions": {
                        "type": "array",
                        "uniqueItems": true,
                        "items": {
                            "title": "Resource Action",
                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                            "type": "string",
                            "pattern": "^[A-Za-z0-9_.:-]*$",
                            "minLength": 1,
                            "maxLength": 512
                        },
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
                    "evaluation_handler": {
                        "title": "Grant-Level Evaluation Handler Setting",
                        "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                        "type": "string",
                        "enum": [
                            "evaluate",
                            "error",
                            "critical"
                        ]
                    },
                    "equality": {
                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                    }
                }
            }
        },
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "description": "Audit batch item result.",
                "additionalProperties": true,
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
                            "additionalProperties": true,
                            "required": [
                                "is_applicable",
                                "query_result",
                                "errors"
                            ],
                            "properties": {
                                "is_applicable": {
                                    "type": "boolean",
                                    "description": "If the grant is applicable to the request or not."
                                },
                                "query_result": {
                                    "description": "Result from running the JSON query."
                                },
                                "errors": {
                                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                                    "title": "Operation Result Errors",
                                    "description": "Errors returned from Authzee Operations.",
                                    "type": "object",
                                    "additionalProperties": false,
                                    "required": [],
                                    "properties": {
                                        "query": {
                                            "type": "array",
                                            "items": {
                                                "title": "Query Error",
                                                "description": "Error when a JSON query fails.",
                                                "type": "object",
                                                "additionalProperties": true,
                                                "required": [
                                                    "is_critical",
                                                    "message"
                                                ],
                                                "properties": {
                                                    "is_critical": {
                                                        "type": "boolean",
                                                        "description": "If this error is critical. Critical errors generally halt further operations."
                                                    },
                                                    "message": {
                                                        "type": "string",
                                                        "description": "Detailed message about what caused the error."
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "has_failed": {
                        "type": "boolean",
                        "description": "If the request has failed from a critical error or not."
                    },
                    "errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations.",
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the batch request could not be validated and failed or not. "
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Batch Result Errors",
            "description": "Errors returned from Authzee Batch requests.",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {}
        }
    }
}
```

### Batch Authorize

The Batch Authorize operation is used to run the Authorize operation for a batch request.  

#### Batch Authorize Result Example

```json
{
    "batch_results": [
        {
            "is_authorized": true,
            "grant": {
                "effect": "allow",
                "actions": [
                    "Balloon:Read",
                    "pop"
                ],
                "query": "contains(request.identities.User[0].role, 'admin')",
                "evaluation_handler": "evaluate",
                "equality": true,
                "data": {}
            },
            "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
            "has_failed": false,
            "critical_errors": {}
        },
        {
            "is_authorized": false,
            "grant": null,
            "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
            "has_failed": false,
            "critical_errors": {}
        },

    ],
    "has_failed": false,
    "errors": {}
}
```


#### Batch Authorize Result Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Authorize Result",
    "description": "Result for the Batch Authorize Operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "batch_results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Authorize Result",
                "description": "Result for the authorize operation.",
                "type": "object",
                "additionalProperties": true,
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
                            {
                                "$schema": "https://json-schema.org/draft/2020-12/schema",
                                "title": "Grant",
                                "description": "A grant is an object representing enacted authorization rules.",
                                "type": "object",
                                "additionalProperties": true,
                                "required": [
                                    "effect",
                                    "actions",
                                    "data",
                                    "query",
                                    "evaluation_handler",
                                    "equality"
                                ],
                                "properties": {
                                    "effect": {
                                        "type": "string",
                                        "enum": [
                                            "allow",
                                            "deny"
                                        ],
                                        "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                                    },
                                    "actions": {
                                        "type": "array",
                                        "uniqueItems": true,
                                        "items": {
                                            "title": "Resource Action",
                                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                                            "type": "string",
                                            "pattern": "^[A-Za-z0-9_.:-]*$",
                                            "minLength": 1,
                                            "maxLength": 512
                                        },
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
                                    "evaluation_handler": {
                                        "title": "Grant-Level Evaluation Handler Setting",
                                        "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                                        "type": "string",
                                        "enum": [
                                            "evaluate",
                                            "error",
                                            "critical"
                                        ]
                                    },
                                    "equality": {
                                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                                    }
                                }
                            }
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
                    "has_failed": {
                        "type": "boolean",
                        "description": "If the request has failed from a critical error or not."
                    },
                    "critical_errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations.",
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the batch request could not be validated and failed or not. "
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Batch Result Errors",
            "description": "Errors returned from Authzee Batch requests.",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {}
        }
    }
}
```


## Errors

Errors are included for all validations, evaluation, and operation calls. 

In general errors take the same basic shape, although this can be built upon to include extra context if needed.  

For validation calls, there is generally only one type of error returned for that specific validation.  

Operation calls will return an object under `errors` where the fields are the error type, and the value is an array of errors for that type. 


### Error Types

- `definition` - An error occurred when validation a context, identity, or resource definition
- `evaluation` - An error occurred during an evaluation. Usually triggered from a JSON query error.
- `grant` - An error occurred when validating a grant.
- `request` - An error occurred when validating a request or batch request.


### Error Example

```json
{
    "is_critical": false,
    "message": "Some error has occurred"
}
```


### Error Schema

```json
{
    "title": "Error Item",
    "description": "Error details.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "is_critical",
        "message"
    ],
    "properties": {
        "is_critical": {
            "type": "boolean",
            "description": "If this error is critical. Critical errors generally halt further steps and cause the validation or operation to exit early."
        },
        "message": {
            "type": "string",
            "description": "Detailed message about what caused the error."
        }
    }
}
```
