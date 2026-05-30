# Authzee 

<!-- ![authzee-logo](./docs/logo.svg) Documentation(Link TBD) -->
<img src="https://raw.githubusercontent.com/btemplep/authzee/main/docs/authzee_balloon.svg" alt="Authzee Balloon" width="100"> 

Authzee is a highly expressive grant-based authorization engine. It focuses on creating authorization around patterns within an organization or application. 

Less authorization rules, granular control, and support for all forms of authorization and identity.

- **Scalable** - Handle complex authorization scenarios across large systems.
- **Separation** - Keep authorization rules separate from business code.
- **Dependable** - Built on top of existing specifications that are widely used. JSON Schema (Draft 2020-12) and JMESPath standards (or other JSON query language).  Authzee has a specification and reference implementation as well.
- **Extensible** - Easily adapt to new identity types, resources, and authorization patterns.  Extend the JMESPath query language for custom capabilities. 
- **ACL** - Access Control List support
- **RBAC** - Role-Based Access Control support
- **ABAC** - Attribute-Based Access Control support
- **ReBAC** - Relationship-Based Access Control support
- **Ultra expressive** - Create very fine-grained controls that are highly maintainable.
- **Auditable** - Core auditing functionality built in from the ground up to easily perform access checks.
- **Agnostic** - Works with any identity provider and resources. New or existing.  Authzee is not an identity provider and does not provide a means to store and source identity.
- **Multi-lingual** - Uses widespread standards that are available in most programming languages. 
    - The example reference implementation in this repo uses python for ease of access. 
    - Other single file reference implementations are available as well.
    - The reference implementation only defines the core Authzee engine. Compute and storage implementations are handled at the SDK level for each language. 


### Table of Contents

- [Basic Example](#basic-example)
- [Complex Example](#complex-example)
- [Tests](#tests)

### Other Docs

- [Specification](./docs/specification.md#authzee-specification)
- [SDKs](./docs/sdks.md#official-authzee-sdks)


## Basic Example

This example shows all of the basic ideas behind Authzee using the python reference implementation [reference.py](./src/reference.py).

Run [basic_example.py](./basic_example.py) from the root of the project after installing the dependencies from the `requirements.txt` file.

```python
import json
from typing import Any

import jmespath

from src.reference import authorize_workflow

# 1. Define the identities the calling entity has
identity_defs = [
    {
        "identity_type": "User", # unique identity type
        "schema": { # JSON Schema for Users
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "role": {
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
                "role",
                "department",
                "email"
            ]
        }
    }
]

# 2. Define resources that can be accessed
resource_defs = [
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
            "required": [
                "id",
                "color",
                "size"
            ],
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
            }
        }
    }
]

# 3. Define Contexts - Context is extra data that is passed to the request
context_defs = [
    { # no context
        "context_type": "NULL",
        "schema": {
            "type": "object",
            "additionalProperties": False
        }
    },
    { # any context
        "context_type": "ANY",
        "schema": {
            "type": "object"
        }
    },
    {
        "context_type": "MySpecialContext",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "Team"
            ],
            "properties": {
                "Team": {
                    "type": "string"
                }
            }
        }
    }
]

# 4. Define Grants - access rules 
grants = [
    {
        "effect": "allow", # allow or deny
        "actions": [ # any actions from your resources or empty to match all actions
            "Balloon:Read",
            "pop"
        ],
        "query": "contains(request.identities.User[0].role, 'admin')", # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>} 
        # In this case, the above query will return `true` if the calling entity's zeroth User type identity has the admin role
        "evaluation_handler": "evaluate",
        "equality": True, # If the request action is in the grants actions and the query result matches this, then the grant is "applicable". 
        "data": {}, # extra free from data to store with this grant
    }
]

# 5. Create an authorization request
request = {
    "identities": { # create zero or more instances of any identity
        "User": [
            {
                "id": "balloon_luvr",
                "role": "admin",
                "department": "eng",
                "email": "ldfkjdf@myorg.org"
            }
        ]
    },
    "resource_type": "Balloon", # Request access to a specific resource type
    "action": "pop", # to perform a specific action,  
    "resource": { # on a specific resource.
        "id": "b123",
        "color": "green",
        "size": "medium"
    },
    "evaluation_handler": "grant", # optionally override grant level evaluation
    "context_type": "MySpecialContext",
    "context": {
        "Team": "ABC"
    }
}


# 6. Define a function wrapping your preferred JSON query language to return the expected schema.
def execute(expression: str, data: Any) -> Any:
    result = {
        "result": None,
        "has_failed": False,
        "error_message": None
    }
    try:
        result['result'] = jmespath.search(expression, data)
    except Exception as exc:
        result['has_failed'] = True
        result['error_message'] = f"A JMESPath Query error has occurred: {exc}"
    
    return result


# 7. Given all of the previous defs and grants, check if the request is authorized.
result = authorize_workflow(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    request,
    execute
)
print(json.dumps(result, indent=4))
if result['is_authorized'] is True:
    print("✅ Access granted!")
else:
    print("❌ Access denied!")

# OUTPUT:
# {
#     "is_authorized": true,
#     "grant": {
#         "effect": "allow",
#         "actions": [
#             "Balloon:Read",
#             "pop"
#         ],
#         "query": "contains(request.identities.User[0].role, 'admin')",
#         "evaluation_handler": "evaluate",
#         "equality": true,
#         "data": {}
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "has_failed": false,
#     "critical_errors": {}
# }
# ✅ Access granted!
```

This basic example shows:
- A calling entity with a "User" identity "balloon_luvr", requesting to pop a balloon.
- A grant that allows admin users to read and pop balloons.
- The authorization succeeds because the calling entity has a user identity with the admin role.  


## Complex Example

This is a more complex example that shows how to handle multiple identities, resources, and grants. 
It utilizes all these elements to create a more complex request for the audit, authorize, batch audit, and batch authorize workflows.

Run [complex_example.py](./complex_example.py) from the root of the project after installing the dependencies from the `requirements.txt` file.

## Tests

Run the tests and generate a coverage report from the root of the project after installing the dependencies from the `requirements.txt` file.

```console
pytest -vvv --cov=./src --cov-report=term --cov-report=html tests/unit
```
