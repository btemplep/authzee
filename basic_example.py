import json

import jmespath

from src.reference import authorize_workflow

# 1. Define the identities the calling entity has
identity_definitions = [
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
context_definitions = [
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
        "query_validation": "validate",
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
    "query_validation": "grant", # optionally override grant level query validation
    "context_type": "MySpecialContext",
    "context": {
        "Team": "ABC"
    }
}

# 6. Given all of the previous definitions and grants, check if the request is authorized.
result = authorize_workflow(
    context_definitions,
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search
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
#         "query_validation": "validate",
#         "equality": true,
#         "data": {}
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "has_failed": false,
#     "critical_errors": {}
# }
# ✅ Access granted!
