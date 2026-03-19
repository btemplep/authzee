# TODO


- [x] update function and class docs to reflect all previous decisions.
    - make sure to add self

- [x] Add more standard types for "Result" types.

- [x] Return values for SDK functions should include errors right? 
    - I need to make return types for everything? or do they just return errors??
    - since nothing changes after the initial add
    - Generic result dataclass, and then the rest are unique where needed

- [x] Should SDK be includes in the error normal result as well? 
    - Yes, but should start with `sdk_`
    - Errors should only be raised at the Authzee class level as much as possible

- [x] SDK - Can we create a simple class that integrates with a storage back end, then you just scale the whole thing?
    - What's the benefit of having dedicated compute module vs just scaling and having an integration with storage
    - parallel multi-thread stuff for processing a single request
    - If you just split by storage then they need to implement their own parallel execution and essentially is just doing the compute module
    - **SOLUTION** - need to find the line of what compute module to create, vs what can just be scaled outside of the authzee class.

- [x] SDK - How to architect interactions?
    - Should everything just go through the compute class including validation?
        - Validation deferred to compute 
            - can be a whole different step that authzee app runs on compute before orchestrating further 
        - Validation done in Authzee
            - Positives
                - is reduced code
                - compute modules are easier to make
            - negatives
                - Largish batch requests could take a while to validate a batch request
    - a bigger question of how does this scale outside of the authzee app and what do I want that to look like. 
    - Like how much compute should be offloaded? 
    - offload to compute
        - compute
            - validate request
            - validate batch request
        
    - what is even the point of having 
    - **SOLUTION** there will still be some reuse in the authzee classes or there will be more in the future.  Split it out and have the authzee class be the orchestrator. 
S
- [x] create and delete
    - context 
        - Only checked for requests - not linked to other resources
    - identity
        - only checked for requests - not linked to other resources
    - resource def
        - resource type - only checked for request not linked to other resources
        - resource actions are linked to grants directly since we check them
            - But we shouldn't check them 
            - if we don't check them you can create grants for things that don't exist yet
            - if the resource action doesn't exist anymore, the grant won't be effected 
            - thus the only check for this is also on requests and it has to check the action against the type
    - TODO - Update grant checks to not check the action

- [x] easier way for grants to do identity checks? 
    - I think this just comes down to adding custom jmespath operations? 
    - If you add anything outside of the grant level it is going to limit everything else
    - maybe just run through some scenarios and add some new standard operations
        - LEFT JOIN
        - OUTER JOIN
        - check if identity type exists in request and has length > 0


- [x] SDK - Updates for defs and grants
    - Instead of register and update just a put - This makes it more stateless
    - Stateless PUT and DELETE - no need for locks 
    - put with simultaneous put is whoever get's there first
    - put with delete, whoever gets there first. 
    - **Solution** use puts - at least for something like a database that has only one table it's just left up to whoever succeeds first
    - for other things like S3 there will still need to be a source of truth for this if we want it to be eventually consistent
    - what if defs are puts, but grants are create and delete only? 
    - **Solution** part 2 - should only create grants and generate UUID client side.  We try to check if UUID exists but there is no guarantee what will happen if you put a grant with the same UUID

- [x] add ability for full scan to repeal grant which will scan all tables for that grant UUID and delete it
    - Much slower but allows a way to clean up corrupted grants. 

- [x] Update SDK docs with all new spec
    - Update all naming conventions to match. 
    - still need to do authorize results types and after - these are only filled in with the spec types


- [x] naming for page refs 
    - ref and next_ref
    - page_ref and next_page_ref
        - This one especially for get_grants_page_refs_page

- [x] Fill in last of spec for operations


- [x] SDK - should grants be updatable? 
    - If they are updatable then they should be by name so it is more stateless
    - For human management it makes sense to make them able to update and also by name
    - But for scaling this means they will need to be removed from tables and added to several tables and it is not stateless
    - 2 writes at the same time could leave the grants in a corrupted state
        - a added it to an actions table but then deleted while the other actions are still being added
    - for defs, they are only held in one place and can be updated as long as it spreads from a single source
    - **SOLUTION**Grants should be create and delete only then. 

- [x] final naming conventions
    - definitions vs defs - I say defs - full name
    - reference vs ref - I say ref - ref is good
    - I WANT THE SHORT VERSIONS
    - **solution** - short version

- [x] query errors no longer include grant, but how do we tell what grant happened during the query error? 
    - Just put it in the message as grant[n] was an error? 
    - for requests or worse, batch requests we could duplicate grant per each batch item which means a lot could be here
    - If there are 100 batch items and 100 grants, then the number of grants returned would be `(items x grants) + grants`
        - 10100 results which just isn't good for what is supposed to be 
    - nevermind this works as needed

- [x] evaluate spec - how errors are handled with query validation setting.  
    - **Solution** - the same as below???

- [x] query validate in requests and grants???
    - Should we call this something more descriptive?
    - query_error_handling
    - evaluation_errors
    - evaluation_handling
    - eval_error_handling
    - **Solution** - evaluation_handler
        - evaluation
        - error
        - critical

- [x] Add context and remove parent and child
    - [x] update basic example
    - [x] update complex example
    - [x] update reference code
    - [x] update readme
    - [ ] update specification
        - [x] Change response to result
        - [x] context schema, example, and validation
        - [x] identity schema, example, and validation
        - [x] resource schema, example, and validation
        - Must be able to return or raise errors in a consistent fashion for languages without exceptions
    - [x] update SDK docs

- [x] Add to audit the value that the grant evaluated to? 
    - Is audit really enough 
    - What is we want to evaluate against all grants and get their values? 
    - Maybe audit should return all grants????????????!?!?!?!?!?!
    - Then if they are applicable or not
    - including the returned query expression
    - Honestly this make more sense then just the applicable grants - maybe include a flag to only do the applicable? 
    - That is something to figure out at a later time though?
    - also include ability to filter grants - same as list grants filters
        - effect
        - action
    - How to handle this with errors for batch_audit? 
        - Request errors
        - batch request errors
        - errors for each grant, for each batch item, since the grant is the list. 
    - Changing this so that it will have grants as a separate list from results??
    - **Solution** - yee

- [x] Audit - Should audit split results and grants for errors?
    - It sucks but if the query error shows the grant then it potentially will duplicate all grants for an audit request
    - Authorize already includes the grant so it covers any query errors
    - **solution** - separate them 

- [x] How and should you propagate errors up the chain? 
    - Critical errors should be propagated up the chain if that cause the layer above it to fail
    - if audit has a crit, then the request fails then an error should tell why it failed
        - The execution failed for grant[n] and caused a critical error. 
    - Where as a whole batch request does not fail just because a batch item does.  So in that scenario the result for a single item should show the error but not at the batch level. 

- [x] standardize json query function input and output
    - need to have an output schema that helps to identity and pass error messages



- [x] What do you want to actually make in the spec? 
    - Spec should only give core functionality and give enough room to add whatever - SDKs can take more liberty, and the SDK guide is to be more opinionated anyway
    - **SOLUTION** - General Guidance for the spec
        - Input and output data structures can be added to for more functionality where the schemas allow. 
        - Case can be changed to align with language conventions. 
        - this is just the core spec - it is not the most efficient or best way but the most succinct way to describe Authzee functionality
        - Errors and especially critical errors are left up to the implementations to decide how to return - from function, exceptions, etc
        - All that in mind some minimums to consider for SDKs
            - operations request and response should try to stick to super sets of the core schemas
            - Errors should try to stick to the schemas as well


- [x] on the sdk side of things requests are validated once and then run the operation
    - Everything else is separate because they are added separate
    - but a request validation always goes along with the operation
    - should a workflow still be a reference?  since it can combine all errors
    - I would like the base level Schemas to match what the SDK puts out for the most part
        - SDKs can add properties to grants etc but should match besides that
    - If an op puts out a request val error, that wouldn't match in the current setup
    - **Solution** 
        - Include error types in ops for request validation.  
        - No workflows in the specification, only ops with all inputs validated. 
        - Add uuid, name, description to grants in spec
        - Makes all functionality directly usable from the reference imp
- [x] What to include in batch request? 
    - Technically they only thing you need is action to save on listing the grants
    - the downside is a lot of duplication especially for all identities,
    - Context and context type probably too? 
    - Resource def needs to be different
    - Maybe make it optional? 
    - **Solution** - include all but resource at request level and ability to override all but action at the batch item level. 
- [x] if grants are only filtered/partitioned by action
    - then the only fields in a batch request that need to stay the same are:
        - identities
        - actions
    - If we don't filter by resource type and context type in grant
        - Grants can cover many many use cases
        - Actions unique to resource types gives you an inherent resource type filter
        - Could do similar with context mixture of resource type and action specifics. 
    - Really the only plus of having those is more filters/partitions so slightly less compute needed but it sacrifices so much in the way of grant flexibility
    - **Solution** - Grants don't have context or resource type
- [x] Context types in grants? 
    - Do we need this in the grant and wouldn't it make it more flexible to not have it just list resource types? 
    - context type and context would still be passed in the request and validated 
    - Gives one less thing to filter/partition on, but again makes the grants way more flexible which seems more important...
    - **Solution** - no context type in grant

- [x] figure out how to craft request schema and handle validation
    - In order to fit it all in the schema for the multiple action types and context types, we would need to create a schema that will have to be all permutations of resource types and context types
    - In reality it would be better to have 2 steps
    - one to run it through the initial schema
    - then another to confirm that the resources match the resource type schema and the context matches the context type schema
    - DO THIS with all references of large data?
        - ie "verfiy" is separate from validate for schema
        - Actions
        - all types
        - schemas of objects for types
    - Validation will be validating against my schemas
        - Validate that I can work with this data
    - Verification will will against the data that was passed
        - for example: it's a valid context type and the schema matches that type
        - Verify that the given data matches what is expected from the client
    - Original steps:
        - Validate defs
        - generate schemas
        - Validate grants
        - Validate request
        - Run workflow specific steps
    - New steps: - schemas are now static
        - Validate defs
        - Verify defs
        - validate grants
        - verify grants
        - validate request
        - verify request
        - Run workflow specific steps
    - **Solution** - Schemas are only one part of the validation now - makes it easier to add and remove definitions in an active way in the future
- [x] resource_type in grant or no??
    - We should recommend that you namespace the actions by resource type for best scaling and performance
    - Or if you have to share offload the check for resource type to the query
    - This we we can also create a grant for several resource types
    - A grant with permissions that span resource types
    - **Solution** - Only filter by actions, and context type
        - Makes it much more flexible - can create very complex rules now spanning actions and resource types
- [x] Remove need to have all identity and parent/child types present?
    - Having it makes the queries slightly easier, but makes request more complex and possible less scalable if there are a lot of identities or parent/child relationships
    - Can maybe just remove the parent child in favor of the more flexible context?
        - But if there are parent and child relationships that means that the context would have to be different per each resource type and would possible create way more context types
        - don't even know how important parent child will be, just make it only context
        - But in batch operations, we can only use one context, but each resource could have parent, child, sibling resources
        - not true we could require the same context type, but have different context for each
            - Same resource type and context type, but separate actual values. 
    - **Solution** - Have a context types that can be created and are custom with schemas