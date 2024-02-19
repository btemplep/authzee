# `authzee`

<!-- ![authzee-logo](./docs/logo.svg) Documentation(Link TBD) -->
<img src="./docs/logo.svg" alt="Authzee Logo" width="300">

Authzee is a highly expressive grant-based authorization framework that is async, extensible, and scalable. 

Authzee was originally developed with a focus on authorization for existing infrastructure 
like AD users, AD roles, AWS roles etc. Users, roles, groups and other identities are not stored in authzee. 

Authzee supports **ABAC** (Attribute Based Access Control) and **ACL** (Access Control List) style authorization.
It does not support self-contained **RBAC** (Role Based Access Control) since roles are not stored in authzee.
The relationships between users, roles, and groups is deferred to external systems.
Authzee is not **ReBAC** based, but supports many of the ideas.  Tying users to specific actions on specific resources,
and expressions to authorize. Note that this can be done on a user by user basis but authzee is more compute intense than 
other options.

For prod ready, large scale **ReBAC** check out [authzed](https://authzed.com/).

- [Installation](#installation)
- [Tutorial](#tutorial)
    - [Identity](#identity)
    - [Resource](#resource)
    - [Resource Actions](#resource-actions)
    - [Resource Authz](#resource-authz)
    - [Grant](#grant)
    - [`authzee` App](#authzee-app)
    - [`authzee` Sync App](#authzee-sync-app)
    - [`authzee` App Grant Management](#authzee-app-grant-management)
    - [`authzee` App Authorization Methods](#authzee-app-authorization-methods)
    - [`authzee` App Helper Methods](#authzee-app-helper-methods)
- [Full Tutorial Example](#full-tutorial-example)
- [Definitions](#definitions)


## Installation

Install from pip

```text
$ pip install authzee
```

For different compute or storage backends you may need to install extra deps. 

```text
$ pip install authzee[sql]
```

Extra dependencies:

- `sql` - For `SQLStorage`. 


## Tutorial

Let's start with a simple example.  An authorization request where an entity needs to perform an action on a resource, 
and authzee should tell us if it is allowed to or not.

> **NOTE** - The tutorial here covers a basic setup, but for more details please see the Documentation(Link TBD).

You can go straight to the [full code example](#full-tutorial-example), or follow along with the tutorial to get all of the definitions and smaller examples.


### Identity

Authzee expects the calling entity to be described by its identities. 
An entity could be a person, a service user, a role etc. 
An identity could be anything used to describe who or what an entity is.  The calling entity can have many identities. 
Common identity types could be AD user, AD groups, AWS User, AWS Role.  A single identity could have all of these and multiples of them. 


In Authzee actions can be limited based on identities.
Identity models are made with pydantic.

```python
from pydantic import BaseModel

class ADUser(BaseModel):
    cn: str

```


### Resource

Resources in Authzee represent resources that authorization is needed for. 
The resource type and fields can be used in authorization.
Resource Models are made with pydantic.

```python
from pydantic import BaseModel

class Balloon(BaseModel):
    color: str
    size: str
```


### Resource Actions

Resource actions are used to enumerate operations that can be performed on a resources.
You can define resource actions as enums that are based on `authzee.ResourceAction`.
Each resource type must have it's own set of resource actions.

```python
from enum import auto

from authzee import ResourceAction

class BalloonAction(ResourceAction):
    CreateBalloon: str = auto()
    DeleteBalloon: str = auto()
    ListBalloons: str = auto()

```

### Resource Authz

"Resource Authz" is a metadata wrapper for resources, resource actions, and their relationships. 

Create them as a child class of `authzee.ResourceAuthz`, and fill in the default values to declare the resource type, resource action type, as well as parent and child relationships.  

Authzee does not keep a a hierarchy of relationships, and defining these is purely up to the user, and how they would like to authorize their resources.  
If you create a resource authz then you can set up the parent and child relationships however you want.  What Authzee will do with the defined relationships is:

- check parent and child resource types against the authz
- normalize the parent and child resources so you can query them in authorization requests

```python
from enum import auto
from typing import Set, Type

from pydantic import BaseModel, Field

from authzee import ResourceAction, ResourceAuthz


class Balloon(BaseModel):
    color: str
    size: float


class BalloonAction(ResourceAction):
    CreateBalloon: str = auto()
    DeleteBalloon: str = auto()
    ListBalloons: str = auto()

  
class BalloonString(BaseModel):
    color: str
    length: float


class BalloonStringActions(ResourceAction):
    CreateBalloonString: str = auto()
    DeleteBalloonString: str = auto()
    ListBalloonsString: str = auto()


BalloonAuthz = ResourceAuthz(
    resource_type=Balloon,
    resource_action_type=BalloonAction,
    parent_resource_types=set(),
    child_resource_types={BalloonString}
)
BalloonStringAuthz = ResourceAuthz(
    resource_type=BalloonString,
    resource_action_type=BalloonStringAction,
    parent_resource_types={Balloon},
    child_resource_types=set()
)
```

### Grant 

By default everything in Authzee is unauthorized/not allowed.  
In order to allow anything, grants must be created. 

There are two types of grants denoted by their effect. 

- Allow - Grants that authorize/allow matching requests.
- Deny - Grants that deny matching requests.  Requests with matching deny grants are unauthorized. Even if there are matching allow grants.

Grants are created with the `authzee.Grant` model, then added to the authzee app. 


```python
from pydantic import BaseModel

from authzee import Grant, GrantEffect


class Balloon(BaseModel):
    color: str
    size: float


class BalloonAction(ResourceAction):
    CreateBalloon: str = auto()
    DeleteBalloon: str = auto()
    ListBalloons: str = auto()


new_grant = Grant(
    name="Human friendly name",
    description="human friendly description",
    resource_type=Balloon, # The class resource type
    resource_actions={ # the set of resource actions
        BalloonAction.CreateBalloon,
        BalloonAction.DeleteBalloon
    },
    # JMESpath is the JSON query language for verifying identities and 
    # resources, as well as their relationships
    jmespath_expression=""" 
    contains(identities.ADUser[].cn, 'authzee_user_1')
    && resource.color == 'blue'
    """,
    result_match=True # If the result of the jmespath search query matches this, then the grant is considered a match!
)

# add to an authzee app. See more in authzee app section
# new_grant = authzee_app.add_grant(
#     effect=GrantEffect.ALLOW,
#     grant=new_grant
# )
```

The grant above will match with:

- resources of the `Balloon` type
- resource actions of `CreateBalloon` or `DeleteBalloon`

But what are `jmespath_expression` and `result_match` for?

[JMESPath](https://jmespath.org/) is a JSON query language with a complete specification. Authzee uses it as the query tool for authorizations. 

The request data is normalized into a JSON object. The JMESPath query from `jmespath_expression`
is evaluated and then checked if it is an exact match of `result_match`.  If so, then the grant
is considered a match.

Example of normalized request data:

```json
{
    "identities": {
        "ADUser": [
            {
                "cn": "authzee_user_1"
            }
        ],
        "ADGroup": []
    },
    "resource_type": "Balloon",
    "resource": {
        "color": "green",
        "size": 12.27
    },
    "resource_action": "BalloonAction.CreateBalloon",
    "parent_resources": {},
    "child_resources": {
        "BalloonString": [
            {
                "color": "purple",
                "length": 27
            }
        ]
    }
}
```

The data for this is normalized as follows:

- `identities` is a JSON object whose keys include all identity types, and the value of each is an array.
- Any identities passed will be serialized and added to the array of their respective identity types. 
- `resource_type` is the class name of the resource type model for the request.
- `resource` is the serialized resource model for the request
- `resource_action` is the full name of the action for the request. `<class name>.<enum member>`
- `parent_resources` and `child_resources` are JSON objects that include all of the parent and child resource types class names as keys, and the value of each is an array.
- Any child or parent resources will be serialized and added to the array of their respective parent or child resource types. 

The above json is used as the data in `jmespath.search()`, along with the jmespath expression from the grant used as the expression.


### `authzee` App

The central interface of authzee is with the creation of an authzee app. 
An Authzee app requires a storage backend and a compute backend. 

Available Storage Backends:

- `SQLStorage` - Store data in a SQL database - async enabled

Available Compute Backends:

- `MainProcessCompute` - process authorization requests synchronously in the main thread - not async
- `MultiprocessCompute` - process authorization requests asynchronously.  Distributes work to a process pool
- `ThreadedCompute` - Process authorization requests asynchronously.  Distributes work to a thread pool.  Note that because of the GIL, using multiple threads may actually be slightly slower than `MainProcessCompute`.  While it's not truly parallel processing, it will not block the main thread. 

```python
from authzee import (
    Authzee,
    MultiprocessCompute,
    SQLStorage
)

compute = MultiprocessCompute()
storage = SQLStorage(
    sqlalchemy_async_engine_kwargs={
        "url": "sqlite+aiosqlite:///test.sqlite",
        "echo": True
    }
)
authzee_app = Authzee(
    compute_backend=compute,
    storage_backend=storage
)

```

### `authzee` Sync App

There is also a synchronous wrapper for the Authzee app. 
It has all of the same methods but they are synchronous. 

```python
from authzee import (
    Authzee,
    AuthzeeSync,
    MultiprocessCompute,
    SQLStorage
)

compute = MultiprocessCompute()
storage = SQLStorage(
    sqlalchemy_async_engine_kwargs={
        "url": "sqlite+aiosqlite:///test.sqlite",
        "echo": True
    }
)
authzee_app = Authzee(
    compute_backend=compute,
    storage_backend=storage
)
authzee_sync_app = AuthzeeSync(
    authzee_app=authzee_app
)
```

### `authzee` App Grant Management

After initialization of the Authzee app you can manage grants with these async methods:

- `list_grants` - List grants with an iterator.
- `add_grant` - Add a new grant.
- `delete_grant` - Delete a grant.
- `get_grants_page` - Retrieve a single page of grants.


### `authzee` App Authorization Methods

Of course you can also use the async authorization methods!

- `authorize` - Determine if the request is authorized.
- `authorize_many` - Determine if several of the same resource type are authorized for the request. 
- `list_matching_grants` - List matching grants with an iterator. 
- `get_matching_grants_page` - Retrieve a single page of matching grants. 


### `authzee` App Helper Methods

- `grant_matches` - Check if the request matches the given grant.


## Full Tutorial Example

```python
import asyncio
from enum import auto
from typing import Set, Type

from pydantic import BaseModel, Field

from authzee import (
    Authzee,
    AuthzeeSync,
    Grant, 
    GrantEffect,
    MultiprocessCompute,
    ResourceAction, 
    ResourceAuthz,
    SQLStorage
)

# Identity Models
# Create identity models that represent the calling entities identities 
class ADUser(BaseModel):
    cn: str


class ADGroup(BaseModel):
    cn: str


# Resource Models
# Used to authorize actions on resources
# Can use authorization specific resource models
class Balloon(BaseModel):
    color: str
    size: float

  
class BalloonString(BaseModel):
    color: str
    length: float


# Resource Actions
# One resource action per resource type to represent the actions that can be taken on the resource
class BalloonAction(ResourceAction):
    CreateBalloon: str = auto()
    DeleteBalloon: str = auto()
    ListBalloons: str = auto()


class BalloonStringAction(ResourceAction):
    CreateBalloonString: str = auto()
    DeleteBalloonString: str = auto()
    ListBalloonsString: str = auto()


# Resource Authzs
# Tie resource types, resource actions, as well as child and parent relationships together

BalloonAuthz = ResourceAuthz(
    resource_type=Balloon,
    resource_action_type=BalloonAction,
    parent_resource_types=set(),
    child_resource_types={BalloonString}
)
BalloonStringAuthz = ResourceAuthz(
    resource_type=BalloonString,
    resource_action_type=BalloonStringAction,
    parent_resource_types={Balloon},
    child_resource_types=set()
)

# Create a compute and storage backend
compute = MultiprocessCompute()
storage = SQLStorage(
    sqlalchemy_async_engine_kwargs={
        "url": "sqlite+aiosqlite:///test.sqlite",
        "echo": False
    }
)
# Pass those to the Authzee app
authzee_app = Authzee(
    compute_backend=compute,
    storage_backend=storage
)
# Most methods to authzee are async, but you can use the synchronous wrapper if you aren't using async
authzee_sync = AuthzeeSync(authzee_app=authzee_app)
# Register Identity types
authzee_app.register_identity_type(ADUser)
authzee_app.register_identity_type(ADGroup)
# Then register ResourceAuthzs
authzee_app.register_resource_authz(BalloonAuthz)
authzee_app.register_resource_authz(BalloonStringAuthz)

if __name__ == "__main__":
    # By default no requests are authorized in authzee
    # Grants are the base unit for describing how to match an authorization request
    # Grants are added to the authzee app as either ALLOW or DENY. 
    # Authorization requests that match a DENY grant are not authorized.
    # Requests that match an ALLOW grant but not any DENY grants are authorized.
    # Create new grant objects
    my_balloon = Balloon(
        color="blue",
        size=27.0
    )
    identities = [
        ADUser(
            cn="authzee_user_1"
        ),
        ADGroup(
            cn="some_group"
        ),
        ADGroup(
            cn="another_group"
        )
    ]
    
    # as long as the compute and storage backends support is there is also 
    # async versions for all of these besides grant_matches. 
    # Simply append "_async" to the method. 
    async def tutorial() -> None:

        # It's recommended to initialize the authzee app with a __main__ block
        # or a frameworks startup function.
        # Some compute backends me actually mandate it to be done like this.
        await authzee_app.initialize()

        # Run the one time setup.  This should only be done once per configuration.
        # Creates DB tables, other storage setup, and other compute setup
        #await authzee_app.setup()

        # To tear down, delete everything that did run
        #await authzee_app.teardown()

        new_grant = Grant(
            name="Human friendly name",
            description="human friendly description",
            resource_type=Balloon, # The class resource type
            resource_actions={ # the set of resource actions
                BalloonAction.CreateBalloon,
                BalloonAction.DeleteBalloon
            },
            # JMESpath is the JSON query language for verifying identities and 
            # resources, as well as their relationships
            jmespath_expression=""" 
            contains(identities.ADUser[].cn, 'authzee_user_1')
            && resource.color == 'blue'
            """,
            result_match=True # If the result of the jmespath search query matches this, then the grant is considered a match!
        )
        match_everything_grant = Grant(
            name="everything",
            description="",
            resource_type=Balloon,
            resource_actions={BalloonAction.CreateBalloon},
            jmespath_expression="`true`",
            result_match=True
        )
        # Add the new grant to authzee as an ALLOW Grant
        new_grant = await authzee_app.add_grant( 
            effect=GrantEffect.ALLOW,
            grant=new_grant
        )
        match_everything_grant = await authzee_app.add_grant( 
            effect=GrantEffect.ALLOW,
            grant=match_everything_grant
        )
        # Get an iterator for the grants
        async for grant in authzee_app.list_grants(effect=GrantEffect.ALLOW):
            print(grant)
        
        # Delete a grant
        await authzee_app.delete_grant(
            effect=GrantEffect.ALLOW, 
            uuid=match_everything_grant.uuid
        )

        # Get a single page of grants
        grants_page = await authzee_app.get_grants_page(
            effect=GrantEffect.ALLOW
        )
        for grant in grants_page.grants:
            print(grant)
        
        # Authorize a request
        authorized = await authzee_app.authorize(
            resource=my_balloon,
            resource_action=BalloonAction.CreateBalloon,
            parent_resources=[],
            child_resources=[],
            identities=identities
        )
        print(authorized) # True

        # Authorize many resources in a request
        authorized_many = await authzee_app.authorize_many(
            resources=[
                my_balloon,
                Balloon(
                    color="red",
                    size=100.8
                )
            ],
            resource_action=BalloonAction.CreateBalloon,
            parent_resources=[],
            child_resources=[],
            identities=identities
        )
        print(authorized_many) # [True, False]
        
        # iterator for matching grants
        matching_grants_iter = authzee_app.list_matching_grants(
            effect=GrantEffect.ALLOW,
            resource=my_balloon,
            resource_action=BalloonAction.CreateBalloon,
            parent_resources=[],
            child_resources=[],
            identities=identities
        )
        async for grant in matching_grants_iter:
            print(grant)
        
        # Get a single page of matching grants
        matching_grants_page = await authzee_app.get_matching_grants_page(
            effect=GrantEffect.ALLOW,
            resource=my_balloon,
            resource_action=BalloonAction.CreateBalloon,
            parent_resources=[],
            child_resources=[],
            identities=identities
        )
        for grant in matching_grants_page.grants:
            print(grant)
    
    asyncio.run(tutorial())
```

### Definitions

- Authorization Request (Request) - A request to see if a the calling entity is authorized to perform a specific resource action on a resource. 

- Calling Entity (Entity) - In an authorization request, the calling entity is essentially "who" is being authorized. The entity could be a person, service account, role etc.   

- Identity - A way to identify an entity. An identity could be AD users, AD groups, AWS roles, AWS users etc.

- Resource - Resources in Authzee represent resources that authorization is needed for.  Example: My application deals with balloons, balloons are resources we authorize against.

- Resource Type - The type of a "Resource".  Example: My app needs to authorize around balloons. So, "Balloon" is the resource type.

- Resource Actions - Actions that can be done to resources.  Example: Balloon resource type could have actions of "InflateBalloon", "PopBalloon", "ListBalloons", "CreateBalloon".

- Grant - The unit that defines how to query and match against authorization requests.  Grants are added to authzee to allow of explicitly deny authorization requests.  Requests that match any DENY grants are not authorized.  Requests that match any ALLOW grants and does not match any DENY grants are allowed. 

