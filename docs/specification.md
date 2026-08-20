# Authzee Specification 
## Version 0.4.0

This document describes the specification for **Authzee**.

For a quick introduction to the core Authzee engine see the [README](../README.md). 

For language specific use and guidance see the [SDKs](./sdks.md)

Authzee is a highly expressive grant-based authorization engine.  It uses JSON Schemas (Draft 2020-12) to define and validate all inputs and outputs. Grants are evaluated against the request data and grant data using a JSON query language of your choice to make access control decisions. JMESpath is preferred because it has a specification and is extensible.

Authzee offers several standard *operations*.  A common use case is the "Authorize" operation which determines authorization.  These *operations* are fed *requests*.  *Requests* consist of Identities, a resource action, a resource type, a resource instance, a context type, and a context instance.  Identities are a way to describe a *calling entity's* identities.  They could be user, groups, roles, etc.  Resources represents resources that need to be authorized for.  Resource actions are actions that are performed on those resources. Context is a way to pass extra structured data into a request.  Identities, resources, and contexts are defined as needed.  These are then validated and can be used to validate requests.  The request are then passed to the operations like authorize, along with *grants*.  Grants are used to define authorization rules. 


## Specification Guidance and Limitations

- This is the Authzee Specification. It is not the best or most efficient way to use Authzee.  It is a succinct description of Authzee functionality that is hopefully presented in an implementation agnostic fashion.  
- Not all of the functionality described here is meant to be part of an implementation's "public" API.  It is just to establish standards for Authzee. 
- Case conventions can be changed to align with language conventions.
- Input and output data structures can have additional properties where allowed in their respective schemas.  Implementations are expected to build upon the base schemas. 
- Errors are left up to implementations to decide the method of presenting the error. Whether it is directly returned from a function, raised via an exception, or by other means. 
    - Errors and results are still expected to follow the schemas laid out here. 
    - For example, an "Authorize" operation that encounters an error should always include the result matching the Authorize Result Schema when the error is presented. 
    - For something like a validation error on an identity, the return value or exception should include a data structure that matches the [Error Schema](#error-schema).
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
        - [Authorize Result Error Example](#authorize-result-error-example)
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

- **Identity** - An object representing a unique type of identity to consider when authorizing.
- **Resource** - An object representing a unique type of resource to authorize for.
- **Resource Action (Action)** - A name for a unique action taken on a resource.
- **Grant** - Defines rules for authorization. 
- **Operation (Op)** - Distinct, named authorization functionality for a request. Audit, Authorize, Batch Audit, and Batch Authorize.
- **Authorization Request (Request)** - The object used to specify identities, resources, actions, and other configurations that are passed to functions.
- **Request Evaluation** - When a request data structure is evaluated against a grant to determine if the grant is applicable to the request.
- **Calling Entity (Entity)** - Who or what is represented by a request.  A calling entity can have many identities of the same and different types. 


## Context Definitions

Context is included in requests as extra structured data.  The definition includes a unique context type name, and the schema for the request context.

### Context Definition Example

```json
{
    "context_type": "event",
    "schema": {
        "type": "object",
        "properties": {
            "request_source": {
                "type": "string"
            },
            "timestamp": {
                "type": "string",
                "format": "date-time"
            },
            "event_type": {
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

If an error occurs when validating a context definition, a `definition` type [Error](#errors) should be returned/raised.


## Identity Definitions

Identity definitions describe the types of identities that a calling entity possesses to make requests. These represent "who" is trying to access the resources. Each identity type has a unique name and a JSON Schema that validates the structure and contents of identity objects that are passed in requests.

**Common Identity Types:**
- **Users**: Individual people with attributes like ID, email, department, roles
- **Groups**: Collections of users with shared characteristics (teams, departments, projects)
- **Roles**: Permission sets that define what actions can be performed
- **Applications**: Systems or services that act on behalf of users

This can also be extended to Identity Provider specific identities or anything else you could use to help identify a calling entity.

Identity definitions enable flexible representation of complex organizational structures and permission models.

### Identity Definition Example

```json
{
    "identity_type": "User",
    "schema": {
        "type": "object",
        "additionalProperties": true,
        "required": [
            "id",
            "department",
            "email"
        ],
        "properties": {
            "id": {
                "type": "string"
            },
            "department": {
                "type": "string",
                "enum": [
                    "balloon",
                    "string",
                    "disposal",
                    "party_planning"
                ]
            },
            "email": {
                "type": "string",
                "format": "email"
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

If an error occurs when validating an identity definition, a `definition` type [Error](#errors) should be returned/raised.


## Resource Definitions 

Resource definitions describe the types of resources that can be accessed and what actions can be performed on them. These represent "what" is being accessed. 

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


### Resource Definition Validation

Resource definitions are valid if all of the following conditions are met:
- The definition is valid against the resource definition schema
- The definition's `resource_type` is unique among resource definitions
- The definition schema's base type is "object"

If an error occurs when validating an resource definition, a `definition` type [Error](#errors) should be returned/raised.


## Grants

Grants are the Authzee authorization rules. They query the request and grant data using the specified JSON query language. 


### Grant Example

```json
{
    "effect": "allow",
    "actions": [
        "Balloon:Inflate"
    ],
    "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
    "equality": true,
    "applicable_on_failure": false,
    "data": {
        "allowed_departments": [
            "balloon",
            "string"
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
        "equality": {
            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
        },
        "applicable_on_failure": {
            "type": "boolean",
            "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
        }
    }
}
```


### Grant Validation

Grant are valid if all of the following conditions are met:
- The grant is valid against the grant schema

> **NOTE** - Grant actions are not validated so that grants can be created for future resource actions, and for performance purposes in the SDKs. 

If an error occurs when validating a grant, a `grant` type [Error](#errors) should be returned/raised.


## Requests

Requests represent a calling entity's request to perform an operation on identities, an action, a resource type, a resource instance, a context type, and a context instance. 


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
    "action": "Balloon:Inflate",
    "resource_type": "Balloon",
    "resource": {
        "color": "green",
        "max_diameter": 12.03,
        "psi": 27
    },
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
        "context"
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

If an error occurs when validating a request, a `request` type [Error](#errors) should be returned/raised.


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
    "action": "Balloon:Inflate",
    "resource_type": "Balloon",
    "resource": {
        "color": "green",
        "max_diameter": 12.03,
        "psi": 27
    },
    "context_type": "event",
    "context": {
        "request_source": "web_ui",
        "timestamp": "2023-12-07T10:30:00Z",
        "event_type": "birthday_party"
    },
    "batch": [
        {
            "resource": {
                "color": "purple",
                "max_diameter": 12.05,
                "psi": 29
            }
        },
        { 
            "identities": {
                "User": [
                    {
                        "id": "user345",
                        "department": "party_planning",
                        "email": "john.doe@company.com"
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
            "resource_type": "Balloon",
            "resource": {
                "color": "purple",
                "max_diameter": 12.03,
                "psi": 27
            },
            "context_type": "event", 
            "context":  {
                "request_source": "web_ui",
                "timestamp": "2023-12-07T10:30:00Z",
                "event_type": "birthday_party"
            }
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
        "batch": {
            "type": "array",
            "description": "Batch of items to process with shared resource types. When evaluated, each item is merged with the root request, where the batch item fields take precedence.",
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
                        "description": "Resource for this batch item, that is an instance of the given resource_type. Overrides the batch request level if the field exists and is not null."
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

If an error occurs when validating a batch request at the top level, a `request` type [Error](#errors) should be returned/raised. Individual batch item validation errors should also be reported as `request` type errors for the specific item that failed.


## Evaluations

Evaluations are the primary unit of work in Authzee.  Authzee operations evaluate requests against grants to determine if a grant is applicable to a request. What is done with the applicable grants is dependent upon the operation.  


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
        "failure"
    ],
    "properties": {
        "result": {
            "description": "Result from running the JSON query."
        },
        "failure": {
            "type": [
                "string",
                "null"
            ],
            "description": "A message describing why the query execution failed, or null if no failure occurred."
        }
    }
}
```

A grant is applicable to a request if all of the following are true:
- The grant has 0 actions OR the request action is in the grant actions.
- The JSON execute function is called with the grant's query as the `expression` parameter, along with the request and grant nested under an object as the `data` parameter like so: `execute(grant.query, {"request": <request body>, "grant": <grant_body>})` 
- One of the following scenarios:
    - The following are all true:
        - The JSON query execute function does not produce a failure.
        - The result of the JSON execute function is equal to the grant's `equality` property value.
    - The following are all true:
        - The JSON query execute function produces a failure.
        - The grant's `applicable_on_failure` is `true`.

If an error occurs during an evaluation, the evaluation is considered a failure. The failure message is recorded in the `failure` field of the result. The grant is not applicable to the request when an evaluation failure occurs, unless `applicable_on_failure` is `true`. The operation continues processing remaining grants regardless of evaluation failures.


### Batch Request Evaluation

Each item in a batch request is first formatted into a standard request, then processed like a normal [Request Evaluation](#request-evaluation).

Formatting a batch request into individual request:
- Create a request for each batch item 
- Each request starts with the fields from the batch item for the request.
- Any request fields that are not present at this point will be taken from the root batch request. 


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
- Each grant is evaluated against the request as described in [Request Evaluation](#request-evaluation).
- The evaluation produces `is_applicable`, `query_result`, and `failure`.
- Each result item copies these fields and includes the `grant` itself.


#### Audit Result Example

```json
{
    "results": [
        {
            "grant": {
                "effect": "allow",
                "actions": [
                    "inflate"
                ],
                "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
                "equality": true,
                "applicable_on_failure": false,
                "data": {
                    "allowed_departments": [
                        "balloon",
                        "string"
                    ]
                }
            },
            "is_applicable": false,
            "query_result": null,
            "failure": "A JSON Query error has occurred: invalid expression."
        }
    ],
    "error": {
        "error_type": "definition",
        "message": "Context schemas must declare the root type to be an object."
    }
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
        "results",
        "error"
    ],
    "properties": {
        "results": {
            "type": "array",
            "description": "List of grant evaluation results.",
            "items": {
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "grant",
                    "is_applicable",
                    "query_result",
                    "failure"
                ],
                "properties": {
                    "grant": {
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
                            "equality": {
                                "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                            },
                            "applicable_on_failure": {
                                "type": "boolean",
                                "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
                            }
                        }
                    },
                    "is_applicable": {
                        "type": "boolean",
                        "description": "If the grant is applicable to the request or not."
                    },
                    "query_result": {
                        "description": "Result from running the JSON query in the grant."
                    },
                    "failure": {
                        "type": [
                            "string",
                            "null"
                        ],
                        "description": "A message describing why the evaluation failed, or null if no failure occurred. Evaluation failures do not cause the operation to fail."
                    }
                }
            }
        },
        "error": {
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
    }
}
```

### Authorize

The Authorize operation gives an authorization decision for a request. 

By default, nothing is authorized in Authzee. 

A request is authorized if **all** of the following are true:
- A grant with an `allow` effect is applicable to the request
- No grants with a `deny` effect are applicable to the request. 

A request is not authorized if **any** of the following are true:
- A grant with a `deny` effect is applicable to the request.
- No grants are applicable to the request.
- An error was encountered (e.g., a validation error in the workflow).


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
        "equality": true,
        "applicable_on_failure": false,
        "data": {}
    },
    "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
    "error": null
}
```

#### Authorize Result Error Example

```json
{
    "is_authorized": false,
    "grant": null,
    "message": "An error has occurred. Therefore, the request is not authorized.",
    "error": {
        "error_type": "request",
        "message": "Identity Type 'Ghost' is not valid."
    }
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
                        "equality": {
                            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                        },
                        "applicable_on_failure": {
                            "type": "boolean",
                            "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
                        }
                    }
                }
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
        "error": {
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
            "equality": true,
            "applicable_on_failure": true,
            "data": {
                "allowed_departments": [
                    "balloon",
                    "string"
                ]
            }
        }
    ],
    "batch": [
        {
            "results": [
                {
                    "is_applicable": true,
                    "query_result": null,
                    "failure": "A JSON Query error has occurred: unknown function 'bad_func'."
                }
            ],
            "error": {
                "error_type": "request",
                "message": "Identity Type 'Ghost' is not valid."
            }
        }
    ],
    "error": {
        "error_type": "definition",
        "message": "Context types must be unique. 'event' is present more than once."
    }
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
        "batch",
        "error"
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
                    "equality": {
                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                    },
                    "applicable_on_failure": {
                        "type": "boolean",
                        "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
                    }
                }
            }
        },
        "batch": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "description": "Audit batch item result.",
                "additionalProperties": true,
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
                            "additionalProperties": true,
                            "required": [
                                "is_applicable",
                                "query_result",
                                "failure"
                            ],
                            "properties": {
                                "is_applicable": {
                                    "type": "boolean",
                                    "description": "If the grant is applicable to the request or not."
                                },
                                "query_result": {
                                    "description": "Result from running the JSON query."
                                },
                                "failure": {
                                    "type": [
                                        "string",
                                        "null"
                                    ],
                                    "description": "A message describing why the evaluation failed, or null if no failure occurred. Evaluation failures do not cause the operation to fail."
                                }
                            }
                        }
                    },
                    "error": {
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
                }
            }
        },
        "error": {
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
    }
}
```

### Batch Authorize

The Batch Authorize operation is used to run the Authorize operation for a batch request.  

#### Batch Authorize Result Example

```json
{
    "batch": [
        {
            "is_authorized": true,
            "grant": {
                "effect": "allow",
                "actions": [
                    "Balloon:Read",
                    "pop"
                ],
                "query": "contains(request.identities.User[0].role, 'admin')",
                "equality": true,
                "applicable_on_failure": false,
                "data": {
                    "role_required": "admin"
                }
            },
            "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
            "error": null
        },
        {
            "is_authorized": false,
            "grant": null,
            "message": "An error has occurred. Therefore, the request is not authorized.",
            "error": {
                "error_type": "request",
                "message": "Resource type 'Kite' is not valid."
            }
        }
    ],
    "error": {
        "error_type": "grant",
        "message": "The grant is not valid. Schema Error: 'effect' is a required property."
    }
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
        "batch",
        "error"
    ],
    "properties": {
        "batch": {
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
                                    "equality": {
                                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                                    },
                                    "applicable_on_failure": {
                                        "type": "boolean",
                                        "description": "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
                                    }
                                }
                            }
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
                    "error": {
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
                }
            }
        },
        "error": {
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
    }
}
```


## Errors

Errors are events that cause an Authzee operation, or batch item to fail. The `error` field is present in all operation result schemas.  It is either `null` (no error) or an object with `error_type` and `message` fields.

Errors can have slightly different effects depending on the operation:
- Audit - Causes the operation to halt.  May not have any, or a complete result set.
- Authorize - Causes the operation to halt. `is_applicable` is marked as `false`.
- Batch Audit 
    - At the root level, causes the whole batch operation to halt. May not have any, or a complete set of batch results.
    - At the batch item level - Same as Audit.
- Batch Authorize
    - At the root level, causes the whole batch operation to halt. May not have any, or a complete set of batch results. 
    - At the batch item level - Same as Authorize.


### Error Types

These error types are required by the specification:

- `definition` - An error occurred when validating a context, identity, or resource definition.
- `grant` - An error occurred when validating a grant.
- `request` - An error occurred when validating a request or batch request.

SDKs may add more error types as needed. 


### Error Example

```json
{
    "error_type": "request",
    "message": "The request is not valid. Schema Error: ..."
}
```


### Error Schema

```json
{
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
```
