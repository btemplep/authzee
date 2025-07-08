# Authzee

<!-- ![authzee-logo](./docs/logo.svg) Documentation(Link TBD) -->
Authzee is a highly expressive grant-based authorization engine. <img src="https://raw.githubusercontent.com/btemplep/authzee/main/docs/logo.svg" alt="Authzee Logo" width="300">


- **Scalable** - Handle complex authorization scenarios across large systems.
- **Extensible** - Easily adapt to new identity types, resources, and authorization patterns.
- **Separation** - Keep authorization rules separate from business code.
- **Dependable** - Built on top of existing specifications that are widely used. JSON Schema and JMESPath standards.  Authzee has a specification and reference implementation as well.
- **ACL** - Access Control List support
- **RBAC** - Role-Based Access Control support
- **ABAC** - Attribute-Based Access Control support
- **ReBAC** - Relationship-Based Access Control support
- **Ultra expressive** - Create very fine-grained controls that are highly maintainable
- **Auditable** - Core auditing functionality built in from the ground up to easily perform access checks.
- **Multi-lingual** - Uses widespread standards to make the core easy to create in any language. 
    - The reference implementation in this repo uses python for ease of access. 
    - The reference implementation only defines the core Authzee engine. Compute and storage implementations are handled at the SDK level for each language. 
- **Agnostic** - Works with any identity provider and resources. New or existing. 


## Table of Contents

- [Basic Example](#basic-example)
- [Complete Example](#complete-example)
- [Full Specification](#full-specification)
  - [Core Concepts](#core-concepts)
  - [Workflow Overview](#workflow-overview)
  - [API Reference](#api-reference)


## Basic Example


```python
import jmespath
from src.reference import authorize_workflow

# 1. Define who can make requests (User identity type)
identity_definitions = [
    {
        "identity_type": "User", # unique identity type
        "schema": { # JSON Schema 
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "department": {
                    "type": "string"
                },
                "email": {
                    "type": "string",
                    "pattern": "^.+@myorg.org$"
                }
            },
            "required": [
                "id",
                "department",
                "email"
            ]
        }
    }
]

# 2. Define resources that can be accessed
resource_definitions = [
    {
        "resource_type": "Balloon", # Resource types must be unique
        "actions": [
            "Balloon:Read", # Action types can be prefaced by a namespace - preferred so they are not shared across resources
            "inflate", # or just plain
            "deflate",
            "pop",
            "tie"
        ],
        "schema": { # JSON Schema
            "type": "object", 
            "properties": {
                "id": {
                    "type": "string"
                },
                "color": {
                    "type": "string"
                },
                "size": {
                    "type": "string",
                    "enum": [
                        "small",
                        "medium",
                        "large"
                    ]
                }
            },
            "required": [
                "id",
                "color",
                "size"
            ]
        },
        "parent_types": [], # parent resource types, if any
        "child_types": [] # child resource types, if any
    }
]

# 3. Define Grants - access rules 
grants = [
    {
        "effect": "allow", # allow or deny
        "actions": [ # any actions from your resources or empty to match all actions
            "Balloon:Read",
            "pop"
        ],
        "query": "request.identities.User[0].role == 'admin'", # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>}
        "query_validation": "none",
        "equality": True, # If the request action is in the grants actions and the query result matches this, then the grant is "applicable". 
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    }
]

# 4. Create an authorization request
request = {
    "identities": {
        "User": [
            {
                "id": "balloon person",
                "role": "admin"
            }
        ]
    },
    "resource_type": "Balloon",
    "action": "pop",
    "resource": {
        "id": "b123",
        "color": "green",
        "size": "medium"
    },
    "parents": {},
    "children": {},
    "query_validation": "grant", # optionally override grant level query validation
    "context": {
        "TEAM": "ABC" # free from data 
    },
    "context_validation": "grant" # optionally override grant level context validation
}

# 5. Check authorization
result = authorize_workflow(
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search
)

if result["authorized"]:
    print("✅ Access granted!")
else:
    print("❌ Access denied!")

# Output: ✅ Access granted!
```

This basic example shows:
- balloon person requesting to read a document
- A grant that allows admin users to read and write documents
- The authorization succeeds because balloon person has the admin role

## Complete Example

Here's a complete example showing how to use Authzee 

```python
import jmespath
import jmespath.functions
from authzee import authorize_workflow, evaluate_workflow

# Step 1: Define identity types (who can make requests)
identity_definitions = [
    {
        "identity_type": "User",
        "schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "department": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                }
            },
            "required": [
                "id",
                "department",
                "email"
            ]
        }
    },
    {
        "identity_type": "Group", 
        "schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "department": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "team",
                        "project",
                        "department"
                    ]
                }
            },
            "required": [
                "name",
                "department",
                "type"
            ]
        }
    },
    {
        "identity_type": "Role",
        "schema": {
            "type": "object", 
            "properties": {
                "name": {
                    "type": "string"
                },
                "permissions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "level": {
                    "type": "string",
                    "enum": [
                        "basic",
                        "advanced",
                        "admin"
                    ]
                }
            },
            "required": [
                "name",
                "permissions",
                "level"
            ]
        }
    }
]

# Step 2: Define resource types (what can be accessed)
resource_definitions = [
    {
        "resource_type": "BalloonStore",
        "actions": [
            "read",
            "manage",
            "create_balloon"
        ],
        "schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "owner_department": {
                    "type": "string"
                },
                "location": {
                    "type": "string"
                }
            },
            "required": [
                "id",
                "name",
                "owner_department",
                "location"
            ]
        },
        "parent_types": [],
        "child_types": [
            "Balloon"
        ]
    },
    {
        "resource_type": "Balloon",
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "schema": {
            "type": "object", 
            "properties": {
                "id": {
                    "type": "string"
                },
                "color": {
                    "type": "string"
                },
                "size": {
                    "type": "string",
                    "enum": [
                        "small",
                        "medium",
                        "large"
                    ]
                },
                "material": {
                    "type": "string"
                },
                "owner_department": {
                    "type": "string"
                },
                "inflated": {
                    "type": "boolean"
                }
            },
            "required": [
                "id",
                "color",
                "size",
                "material",
                "owner_department",
                "inflated"
            ]
        },
        "parent_types": [
            "BalloonStore"
        ],
        "child_types": [
            "BalloonString"
        ]
    },
    {
        "resource_type": "BalloonString",
        "actions": [
            "read",
            "cut",
            "tie",
            "untie"
        ],
        "schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "length": {
                    "type": "number"
                },
                "color": {
                    "type": "string"
                },
                "material": {
                    "type": "string"
                }
            },
            "required": [
                "id",
                "length",
                "color",
                "material"
            ]
        },
        "parent_types": [
            "Balloon"
        ],
        "child_types": []
    }
]

# Step 3: Create authorization grants (rules)
grants = [
    # Allow users to read balloons in their department
    {
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "request.identities.User[0].department == request.resource.owner_department",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    },
    
    # Allow users with admin role to perform any action
    {
        "effect": "allow", 
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "query": "contains(request.identities.Role[*].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    },
    
    # Allow members of department groups to read balloons in that department
    {
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)",
        "query_validation": "error", 
        "equality": True,
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    },
    
    # Allow inflate access if user has balloon permission in their role
    {
        "effect": "allow",
        "actions": [
            "inflate"
        ],
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    },
    
    # Deny pop access for large balloons unless admin
    {
        "effect": "deny",
        "actions": [
            "pop"
        ],
        "query": "request.resource.size == 'large' && !contains(request.identities.Role[*].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_schema": {
            "type": "object"
        },
        "context_validation": "none"
    }
]

# Step 4: Create an authorization request
request = {
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
    "resource_type": "Balloon",
    "action": "inflate",
    "resource": {
        "id": "balloon456",
        "color": "red",
        "size": "medium",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": False
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
    "query_validation": "grant",  # Use grant-level validation settings
    "context": {},   # Additional context data
    "context_validation": "grant"
}

# Optional Step 4b: Add custom JMESPath functions
class CustomFunctions(jmespath.functions.Functions):
    @jmespath.functions.signature({'types': ['number']}, {'types': ['number']})
    def _func_my_add(self, x, y):
        return x + y

options = jmespath.Options(custom_functions=CustomFunctions())

def my_search(expression: str, data):
    return jmespath.search(expression, data, options)

# Step 5a: Evaluate which grants are applicable (useful for auditing)
evaluation_result = evaluate_workflow(
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search # JMESPath search function or custom function
)

print("📋 Evaluation Results (for auditing):")
print(f"   Completed: {evaluation_result['completed']}")
print(f"   Applicable grants: {len(evaluation_result['grants'])}")
for i, grant in enumerate(evaluation_result['grants']):
    print(f"   Grant {i+1}: {grant['effect']} - {grant['query']}")

# Step 5b: Make authorization decision
authorization_result = authorize_workflow(
    identity_definitions,
    resource_definitions, 
    grants,
    request,
    jmespath.search  # JMESPath search function or custom function
)

# Step 6: Check the result
if authorization_result["authorized"]:
    print(f"✅ Access granted: {authorization_result['message']}")
    print(f"Grant responsible: {authorization_result['grant']['query'] if authorization_result['grant'] else 'None'}")
else:
    print(f"❌ Access denied: {authorization_result['message']}")

# Print any errors that occurred during evaluation
if any(authorization_result["errors"].values()):
    print("\n⚠️  Errors occurred during evaluation:")
    for error_type, errors in authorization_result["errors"].items():
        if errors:
            print(f"  {error_type.title()} errors: {len(errors)}")

# The evaluation result will show applicable grants:
# 📋 Evaluation Results (for auditing):
#    Completed: True
#    Applicable grants: 3
#    Grant 1: allow - request.identities.User[0].department == request.resource.owner_department
#    Grant 2: allow - contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)
#    Grant 3: allow - contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department

# The authorization result will be:
# ✅ Access granted: An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.
# Grant responsible: contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department
```

## Full Specification

### Core Concepts

**Authzee** is a policy-based authorization engine that uses a schema-driven approach to define authorization rules and evaluate access control decisions. The system is built around four primary concepts:

- Identity Definitions
- Resource Definitions
- Grants
- Requests

#### 1. Identity Definitions

Identity definitions describe the types of entities that can make authorization requests. These represent "who" is trying to access resources.  Authzee generally refer's to "who" as the calling entity. Each identity type has a unique name and a JSON Schema that validates the structure and content of identity objects.

**Common Identity Types:**
- **Users**: Individual people with attributes like ID, email, department, roles
- **Groups**: Collections of users with shared characteristics (teams, departments, projects)
- **Roles**: Permission sets that define what actions can be performed
- **Applications**: Systems or services that act on behalf of users
- **API Keys**: Programmatic access tokens with associated permissions

Identity definitions enable flexible representation of complex organizational structures and permission models.

##### Identity Definition Schema

Identity definitions are checked against a static schema. See `reference.py` for full schema.

```json
{
    "title": "Identity Definition",
    "description": "An identity definition. Defines a type of identity to use with Authzee.",
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
        "schema": {
            "description": "JSON Schema (Draft 2020-12) that validates identity objects of this type"
        }
    }
}
```

##### Identity Definition Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identity_type` | string | ✅ | Unique identifier for this identity type. Must be alphanumeric with underscores only. Used as a key in request identity objects. |
| `schema` | object | ✅ | JSON Schema (Draft 2020-12) that defines the structure and validation rules for identity objects of this type. All identity instances must conform to this schema. |

#### 2. Resource Definitions 

Resource definitions describe the types of resources that can be accessed and what actions can be performed on them. These represent "what" is being accessed. Each resource type defines:

- Available actions (read, write, delete, etc.)
- A JSON Schema for validating resource objects
- Hierarchical relationships with parent and child resource types

**Resource Hierarchy:**
Resources can have parent-child relationships that model real-world resource hierarchies:
- **Parents**: Higher-level resources that contain this resource (e.g., a BalloonStore contains Balloons)
- **Children**: Lower-level resources contained by this resource (e.g., a Balloon contains BalloonStrings)

This hierarchy allows for sophisticated authorization rules that consider resource containment and inheritance.

##### Resource Definition Schema

Resource definitions are checked against a static schema. See `reference.py` for full schema.

```json
{
    "title": "Resource Definition", 
    "description": "A resource definition. Defines a type of resource to use with Authzee.",
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
            "description": "JSON Schema (Draft 2020-12) that validates resource objects of this type"
        },
        "parent_types": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "description": "Types that are a parent of this resource. When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        },
        "child_types": {
            "type": "array", 
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "description": "Types that are a child of this resource. When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
        }
    }
}
```

##### Resource Definition Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `resource_type` | string | ✅ | Unique identifier for this resource type. Must be alphanumeric with underscores only. Used to identify the resource type in authorization requests. |
| `actions` | array | ✅ | List of unique action names that can be performed on this resource type. Actions can include dots, hyphens, colons, and underscores. Common patterns include "read", "write", "delete" or namespaced like "Balloon:inflate". |
| `schema` | object | ✅ | JSON Schema (Draft 2020-12) that defines the structure and validation rules for resource objects of this type. All resource instances must conform to this schema. |
| `parent_types` | array | ✅ | Array of resource type names that can be parents of this resource type. Parent resources represent containment relationships (e.g., a BalloonStore contains Balloons). Can be empty if no parents exist. |
| `child_types` | array | ✅ | Array of resource type names that can be children of this resource type. Child resources are contained by this resource type (e.g., a Balloon contains BalloonStrings). Can be empty if no children exist. |

**Resource Hierarchy Example:**
```json
{
    "resource_type": "Balloon",
    "parent_types": [
        "BalloonStore"
    ], 
    "child_types": [
        "BalloonString"
    ]
}
```

This means Balloons can be contained in BalloonStores, and Balloons can contain BalloonStrings. During authorization, you can include parent BalloonStores and child BalloonStrings in the request to enable hierarchy-aware authorization rules.

#### 3. Grants (Authorization Rules)

Grants are the core authorization policies that determine whether requests should be allowed or denied. Each grant contains:

- **Effect**: Whether the grant allows or denies access
- **Actions**: Which resource actions the grant applies to
- **Query**: A JMESPath expression that evaluates request data
- **Equality**: The expected result from the query for the grant to be applicable
- **Context Schema**: Validation schema for additional request context
- **Error Handling**: Configuration for how validation errors are treated

**Grant Evaluation Logic:**
1. **Deny grants are evaluated first** - Any applicable deny grant immediately blocks access
2. **Allow grants are evaluated second** - An applicable allow grant permits access
3. **Implicit deny** - If no grants are applicable, access is denied by default

##### Grant Example

The grant schema is generated based on the identity and resource definitions. 

```json
{
    "effect": "allow",
    "actions": [
        "inflate",
        "tie"
    ],
    "query": "request.identities.User[0].department == request.resource.owner_department && contains(request.identities.Role[*].permissions[], 'balloon:inflate')",
    "query_validation": "error",
    "equality": true,
    "data": {
        "rule_name": "department_balloon_access",
        "created_by": "party_team"
    },
    "context_schema": {
        "type": "object",
        "properties": {
            "request_source": {
                "type": "string"
            },
            "timestamp": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": [
            "request_source"
        ]
    },
    "context_validation": "validate"
}
```

##### Grant Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `effect` | string | ✅ | Whether this grant allows or denies access. Must be either "allow" or "deny". Deny grants always take precedence over allow grants. |
| `actions` | array | ✅ | List of resource actions this grant applies to. If empty array, applies to all actions. Must match actions defined in resource definitions. |
| `query` | string | ✅ | JMESPath expression that evaluates the request data. Has access to `request` (the full request object) and `grant` (the current grant with its data). The top-level query data structure is: `{"request": <request_object>, "grant": <grant_object>}` |
| `query_validation` | string | ✅ | How to handle JMESPath query errors. Options: <ul><li>`"validate"` - Query errors cause the grant to be inapplicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |
| `equality` | any | ✅ | Expected result from the query for this grant to be applicable. Can be any JSON value (boolean, string, number, object, array, null). |
| `data` | object | ✅ | Additional data made available to the query as `grant.data`. Useful for storing metadata or values used in query evaluation. |
| `context_schema` | object | ✅ | JSON Schema for validating the request context. Used to ensure the request has the required context data for this grant. |
| `context_validation` | string | ✅ | How to handle context validation errors. Options: <ul><li>`"none"` - There is no validation</li><li>`"validate"` - Context is validated and if the context is invalid, the grant is not applicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |

#### 4. Requests

Requests represent a specific authorization question: "Should this identity be allowed to perform this action on this resource?" Requests contain:

- **Identities**: All identity objects associated with the request (user, groups, roles, etc.)
- **Resource**: The target resource and its type
- **Action**: The specific action being requested
- **Parents/Children**: Related resources in the hierarchy
- **Context**: Additional data for authorization decisions
- **Validation Settings**: How errors should be handled during evaluation

##### Request Example

The request schema is generated based on the identity and resource definitions.

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

##### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identities` | object | ✅ | Map of identity type names to arrays of identity objects. Each identity type must match a defined identity definition and conform to its schema. |
| `resource_type` | string | ✅ | The type of resource being accessed. Must match a defined resource definition. |
| `action` | string | ✅ | The specific action being requested on the resource. Must be one of the actions defined for the resource type. |
| `resource` | object | ✅ | The target resource object. Must conform to the schema defined for the resource type. |
| `parents` | object | ✅ | Map of parent resource type names to arrays of parent resource objects. Only includes types listed in the resource definition's `parent_types`. |
| `children` | object | ✅ | Map of child resource type names to arrays of child resource objects. Only includes types listed in the resource definition's `child_types`. |
| `query_validation` | string | ✅ | Request-level override for query validation. Options: <ul><li>`"grant"` - Use the grant level query validation setting</li><li>`"validate"` - Query errors cause the grant to be inapplicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |
| `context` | object | ✅ | Additional context data for authorization decisions. Available to grant queries as `request.context`. Structure is flexible but should match grant context schemas. |
| `context_validation` | string | ✅ | Request-level override for context validation. Options: <ul><li>`"grant"` - Use the grant level context validation setting</li><li>`"none"` - There is no validation</li><li>`"validate"` - Context is validated and if the context is invalid, the grant is not applicable to the request</li><li>`"error"` - Includes the 'validate' setting checks, and also adds errors to the result</li><li>`"critical"` - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early</li></ul> |

### Workflow Overview

The core Authzee workflow follows these steps:

1. **Define Identity and Resource Types**: Create schema definitions for your identities and resources
2. **Validate Definitions**: Ensure all definitions are valid using `validate_definitions()`
3. **Generate Schemas**: Create JSON schemas for grants and requests using `generate_schemas()`
4. **Create Grants**: Define authorization rules (allow/deny policies)
5. **Validate Grants**: Ensure grants are valid using `validate_grants()`
6. **Create Request**: Build an authorization request
7. **Validate Request**: Ensure the request is valid using `validate_request()`
8. **Evaluate**: Use `authorize()` or `evaluate()` to make authorization decisions

> **NOTE** - Generally, steps 1-3 only happen once. Steps 4 and 5 are only done when adding grants.  6-8 happen for each authorization.

### API Reference

#### Core Functions

**`validate_definitions(identity_defs, resource_defs)`**

Validates identity and resource definitions against their schemas.

**Parameters:**
- `identity_defs` (list): List of identity definition objects
- `resource_defs` (list): List of resource definition objects

**Returns:**
```json
{
    "valid": false,
    "errors": [
        {
            "message": "Identity definition schema was not valid. Schema Error: ...",
            "critical": true,
            "definition_type": "identity",
            "definition": {
                "..."
            }
        }
    ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | Whether all definitions are valid |
| `errors` | array | List of definition error objects |

**Definition Error Object:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Detailed message about what caused the error |
| `critical` | boolean | Whether this error prevents further processing (always true for definition errors) |
| `definition_type` | string | Type of definition that failed ("identity" or "resource") |
| `definition` | any | The definition object that caused the error |

---

**`generate_schemas(identity_defs, resource_defs)`**

Generates JSON schemas for grants, requests, and responses based on your definitions.

**Parameters:**
- `identity_defs` (list): List of validated identity definition objects
- `resource_defs` (list): List of validated resource definition objects

**Returns:**
```json
{
    "grant": {
        "..."
    },
    "request": {
        "..."
    },
    "errors": {
        "..."
    },
    "evaluate": {
        "..."
    },
    "authorize": {
        "..."
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `grant` | object | JSON Schema for validating grant objects |
| `request` | object | JSON Schema for validating request objects |
| `errors` | object | JSON Schema for error response objects |
| `evaluate` | object | JSON Schema for evaluate response objects |
| `authorize` | object | JSON Schema for authorize response objects |

---

**`validate_grants(grants, schema)`**

Validates grants against the generated grant schema.

**Parameters:**
- `grants` (list): List of grant objects to validate
- `schema` (object): Generated grant schema from `generate_schemas()`

**Returns:**
```json
{
    "valid": false,
    "errors": [
        {
            "message": "The grant is not valid. Schema Error: ...",
            "critical": true,
            "grant": {
                "..."
            }
        }
    ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | Whether all grants are valid |
| `errors` | array | List of grant error objects |

**Grant Error Object:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Detailed message about what caused the error |
| `critical` | boolean | Whether this error prevents further processing (always true for grant validation errors) |
| `grant` | any | The grant object that caused the error |

---

**`validate_request(request, schema)`**

Validates a request against the generated request schema.

**Parameters:**
- `request` (object): Request object to validate
- `schema` (object): Generated request schema from `generate_schemas()`

**Returns:**
```json
{
    "valid": false,
    "errors": [
        {
            "message": "The request is not valid for the request schema: ...",
            "critical": true
        }
    ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | Whether the request is valid |
| `errors` | array | List of request error objects |

**Request Error Object:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Detailed message about what caused the error |
| `critical` | boolean | Whether this error prevents further processing (always true for request validation errors) |

---

**`evaluate(request, grants, search)`**

Evaluates which grants are applicable to a request.

**Parameters:**
- `request` (object): Validated request object
- `grants` (list): List of validated grant objects
- `search` (function): JMESPath search function (e.g., `jmespath.search`)
    - Accepts 2 args
        - JMESPath query
        - Data
    - Uses a pointer to a function so that custom JMESPath functions can be added.

**Returns:**
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
            "equality": true,
            "data": {},
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
        "jmespath": [
            {
                "message": "Invalid JMESPath expression: ...",
                "critical": false,
                "grant": {
                    "..."
                }
            }
        ],
        "request": []
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `completed` | boolean | Whether the evaluation completed without critical errors |
| `grants` | array | List of grant objects that are applicable to the request |
| `errors` | object | Categorized error objects that occurred during evaluation |

**Errors Object:**

| Field | Type | Description |
|-------|------|-------------|
| `context` | array | List of context validation error objects |
| `definition` | array | List of definition error objects (empty for this function) |
| `grant` | array | List of grant error objects (empty for this function) |
| `jmespath` | array | List of JMESPath query error objects |
| `request` | array | List of request error objects (empty for this function) |

**Context Error Object:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Detailed message about the context validation failure |
| `critical` | boolean | Whether this error caused the workflow to exit early |
| `grant` | object | The grant object whose context schema validation failed |

**JMESPath Error Object:**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Detailed message about the JMESPath query error |
| `critical` | boolean | Whether this error caused the workflow to exit early |
| `grant` | object | The grant object whose query caused the error |

---

**`authorize(request, grants, search)`**

Makes an authorization decision (allow/deny) based on applicable grants.

**Parameters:**
- `request` (object): Validated request object
- `grants` (list): List of validated grant objects
- `search` (function): JMESPath search function (e.g., `jmespath.search`)
    - Accepts 2 args
        - JMESPath query
        - Data
    - Uses a pointer to a function so that custom JMESPath functions can be added.

**Returns:**
```json
{
    "authorized": true,
    "completed": true,
    "grant": {
        "effect": "allow",
        "actions": [
            "inflate"
        ],
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate')",
        "equality": true,
        "data": {},
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `authorized` | boolean | Whether the request is authorized (true) or denied (false) |
| `completed` | boolean | Whether the authorization completed without critical errors |
| `grant` | object/null | Grant object responsible for the decision, or null if no applicable grants |
| `message` | string | Human-readable explanation of the authorization decision |
| `errors` | object | Categorized error objects that occurred during authorization (same structure as `evaluate()`) |

#### Workflow Functions

**`evaluate_workflow(identity_defs, resource_defs, grants, request, search)`**

Complete workflow that validates everything and returns applicable grants. This function is particularly useful for auditing purposes, as it shows all grants that would apply to a request without making an authorization decision.

**Parameters:**
- `identity_defs` (list): List of identity definition objects
- `resource_defs` (list): List of resource definition objects
- `grants` (list): List of grant objects
- `request` (object): Request object
- `search` (function): JMESPath search function (e.g., `jmespath.search`)
    - Accepts 2 args
        - JMESPath query
        - Data
    - Uses a pointer to a function so that custom JMESPath functions can be added.

**Workflow Steps:**
1. **Validate Definitions** - Validates identity and resource definitions using `validate_definitions()`
2. **Generate Schemas** - Creates JSON schemas using `generate_schemas()`
3. **Validate Grants** - Validates grants against the generated schema using `validate_grants()`
4. **Validate Request** - Validates the request against the generated schema using `validate_request()`
5. **Evaluate Grants** - Runs `evaluate()` to determine which grants are applicable to the request

**Returns:** Same as `evaluate()` but includes validation errors from all steps

**Use Cases:**
- **Auditing**: Determine which grants apply to specific requests for compliance reporting
- **Testing**: Verify that grants are working as expected during development
- **Debugging**: Understand why authorization decisions are being made
- **Policy Analysis**: Review which grants are applicable across different scenarios

---

**`authorize_workflow(identity_defs, resource_defs, grants, request, search_func)`**

Complete workflow that validates everything and returns authorization decision.

**Parameters:**
- `identity_defs` (list): List of identity definition objects
- `resource_defs` (list): List of resource definition objects
- `grants` (list): List of grant objects
- `request` (object): Request object
- `search_func` (function): JMESPath search function

**Workflow Steps:**
1. **Validate Definitions** - Validates identity and resource definitions using `validate_definitions()`
2. **Generate Schemas** - Creates JSON schemas using `generate_schemas()`
3. **Validate Grants** - Validates grants against the generated schema using `validate_grants()`
4. **Validate Request** - Validates the request against the generated schema using `validate_request()`
5. **Authorize Request** - Runs `authorize()` to make the final authorization decision

**Returns:** Same as `authorize()` but includes validation errors from all steps

## Workflow Examples

### Successful Evaluate Workflow Example

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
        },
        {
            "effect": "allow",
            "actions": [
                "inflate"
            ],
            "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate')",
            "query_validation": "error",  
            "equality": true,
            "data": {
                "rule_name": "role_permission_access"
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

### Successful Authorize Workflow Example

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

### Workflow Examples with All Error Types

#### Definition Errors Example

```json
{
    ...
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
            },
            {
                "message": "Parent type 'InvalidParent' does not have a corresponding resource definition.",
                "critical": true,
                "definition_type": "resource",
                "definition": {
                    "resource_type": "Balloon",
                    "actions": [
                        "read"
                    ],
                    "schema": {
                        "type": "object"
                    },
                    "parent_types": [
                        "InvalidParent"
                    ],
                    "child_types": []
                }
            }
        ],
        "grant": [],
        "jmespath": [],
        "request": []
    }
}
```

#### Grant Validation Errors Example

```json
{
    ...
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

#### Request Validation Errors Example

```json
{
    ...
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

#### JMESPath Query Errors Example

```json
{
    ...
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

#### Context Validation Errors Example

```json
{
    ...
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


### Error Handling

Authzee provides comprehensive error handling with different validation settings that control how errors are treated during evaluation. Critical errors will cause the workflow to halt execution and return immediately with an incomplete result.

**Validation Settings:**

Both query and context validation can be configured at the grant level and overridden at the request level:

**Query Validation Options:**
- `validate`: Query errors make grants non-applicable (silent failure)
- `error`: Query errors make grants non-applicable and add to error collection
- `critical`: Query errors make grants non-applicable, add to errors, and halt workflow execution

At the request level it can be set to `grant` to accept the grant value, or override with one of the above values.

**Context Validation Options:**
- `none`: No context validation is performed
- `validate`: Context validation errors make grants non-applicable (silent failure)
- `error`: Context validation errors make grants non-applicable and add to error collection
- `critical`: Context validation errors make grants non-applicable, add to errors, and halt workflow execution

At the request level it can be set to `grant` to accept the grant value, or override with one of the above values.

All workflows return detailed error information categorized by type to help with debugging and monitoring authorization decisions.
