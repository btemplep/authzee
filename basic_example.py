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