import json

import jmespath
import jmespath.functions

from src.reference import authorize_workflow, audit_workflow

# Define the identities the calling entity has
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

# 2. Define resources that can be accessed
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

# 3. Define Grants - access rules 
grants = [
    # Allow users to read balloons in their department
    {
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.User[].department, request.resource.owner_department)",
        "query_validation": "error", # if the query has an error return it
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
        "query": "contains(request.identities.Role[].level, 'admin')",
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
    },

    # Deny if they don't have any user identities
    {
        "effect": "deny",
        "actions": [],
        "query": "length(request.identities.User)",
        "query_validation": "error",
        "equality": 0,
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

# Step 5a: Audit which grants are applicable (useful for auditing)
audit_result = audit_workflow(
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search # JMESPath search function or custom function
)
print(f"Audit Result:\n{json.dumps(audit_result, indent=4)}")
# Audit Result:
# {
#     "completed": true,
#     "grants": [
#         {
#             "effect": "allow",
#             "actions": [
#                 "inflate"
#             ],
#             "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#             "query_validation": "error",
#             "equality": true,
#             "data": {},
#             "context_schema": {
#                 "type": "object"
#             },
#             "context_validation": "none"
#         }
#     ],
#     "errors": {
#         "context": [],
#         "definition": [],
#         "grant": [],
#         "jmespath": [],
#         "request": []
#     }
# }



# Step 5b: Make authorization decision
authorization_result = authorize_workflow(
    identity_definitions,
    resource_definitions, 
    grants,
    request,
    my_search # JMESPath search function or custom function
)
print(f"Authorization Result:\n{json.dumps(authorization_result, indent=4)}")
# Authorization Result:
# {
#     "authorized": true,
#     "completed": true,
#     "grant": {
#         "effect": "allow",
#         "actions": [
#             "inflate"
#         ],
#         "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#         "query_validation": "error",
#         "equality": true,
#         "data": {},
#         "context_schema": {
#             "type": "object"
#         },
#         "context_validation": "none"
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "errors": {
#         "context": [],
#         "definition": [],
#         "grant": [],
#         "jmespath": [],
#         "request": []
#     }
# }