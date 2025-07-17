# Authzee

<!-- ![authzee-logo](./docs/logo.svg) Documentation(Link TBD) -->
Authzee is a highly expressive grant-based authorization engine. <img src="https://raw.githubusercontent.com/btemplep/authzee/main/docs/logo.svg" alt="Authzee Logo" width="300">


- **Scalable** - Handle complex authorization scenarios across large systems.
- **Separation** - Keep authorization rules separate from business code.
- **Dependable** - Built on top of existing specifications that are widely used. JSON Schema and JMESPath standards.  Authzee has a specification and reference implementation as well.
- **Extensible** - Easily adapt to new identity types, resources, and authorization patterns.  Extend the JMESPath query language for custom capabilities.
- **ACL** - Access Control List support
- **RBAC** - Role-Based Access Control support
- **ABAC** - Attribute-Based Access Control support
- **ReBAC** - Relationship-Based Access Control support
- **Ultra expressive** - Create very fine-grained controls that are highly maintainable.
- **Auditable** - Core auditing functionality built in from the ground up to easily perform access checks.
- **Multi-lingual** - Uses widespread standards to make the core easy to create in any language. 
    - The reference implementation in this repo uses python for ease of access. 
    - The reference implementation only defines the core Authzee engine. Compute and storage implementations are handled at the SDK level for each language. 
- **Agnostic** - Works with any identity provider and resources. New or existing. 


### Table of Contents

- [Basic Example](#basic-example)
- [Complex Example](#complex-example)
- [Tests](#tests)

### Other Docs

- [Specification](./docs/specification.md#authzee-specification)
- [SDKs](./docs/sdk_patterns.md#sdks)


## Basic Example

This example shows all of the basic ideas behind Authzee using the python reference implementation.

Run [basic_example.py](./basic_example.py) from the root of the project after installing the dependencies from the `requirements.txt` file.

This basic example shows:
- A calling entity with a User identity "balloon_luvr", requesting to pop a balloon.
- A grant that allows admin users to read and pop balloons.
- The authorization succeeds because the calling entity has the admin role


```python
import jmespath

from src.reference import authorize_workflow

# 1. Define the identities the calling entity has
identity_definitions = [
    {
        "identity_type": "User", # unique identity type
        "schema": { # JSON Schema 
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
        "query": "contains(request.identities.User[*].role, 'admin')", # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>} and will return `true` if any of the calling entities, User type identities have the admin role
        "query_validation": "validate",
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

## Complex Example

This more complex example shows how to handle multiple identities, resources, and grants. 
It utilizes all these elements to create a more complex request for both the audit and authorize workflows.

Run [complex_example.py](./complex_example.py) from the root of the project after installing the dependencies from the `requirements.txt` file.

## Tests

Run the tests and generate a coverage report from the root of the project after installing the dependencies from the `requirements.txt` file.

```console
pytest -vvv --cov=./src --cov-report=term --cov-report=html tests/unit
```
