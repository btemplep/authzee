Separation between what is passed to the authorize and the request data
- What you pass to the request should be "normalized"
- The only addition should be adding the current grant, under grant
- Then you can distill it down however you want. 
- other levels of abstraction can change it however you want

Why Authzee?
- Allows you to actually run a query on the request to find specific identities, parents, children, and context data
- Easily extensible through jmespath
- Out of the box high level, scalable implementations for compute and storage engines OOTB


- [ ] resource actions for a grant can be empty to match all types
- [ ] different error schemas for different errors to make it more clear what resources are effected? 
- [ ] finalize workflow in clear and concise steps/sub 
    - 2 functions called authorize_workflow and grant_matches_workflow to show the full workflows
- [ ] make sure no duplicated in actions, id types, resource types, etc
- [x] what to name:
    - equality in grant
        - **Solution** - expected
    - match_grants
        - evaluate?
        - evaluate_grants
        - **Solution** - Evaluate grants on a request. Grants that can be applied to the request are applicable. 
- [x] pass jmespath search function in to authorize
- [x] one function to generate all schemas
- [x] Change name of "Authz" objects to "Definition"
- [x] Reason for if it's allowed or denied
    - What policy allows or denies it. 
    - Allowed because it matches Allow policy with UUID:
    - Denied because it matches Deny Policy with UUID:
    - Denied because it does not match any policies

- [x] context should be passed as part of the request data
- [x] change grant context to data
- [x] rename grant "equality" field - not sure what else to call this
- [x] Grants should be able to have several resource types and resource actions
    - **SOLUTION** - Grants have several actions - no resource types must check with query
        - recommend not sharing actions to resources for performance reasons.
- [x] Ability to strictly check or not check the schema of inputs
    - Just allow any resource types, actions, identities etc or different levels of checking
    - Maybe a flag for this when creating the app to verify
    - another flag on a per request basis. 
    - **SOLUTION** - Ability to just pass request schema


- [x] Take a step back and think about this from a general programming perspective. 
    - JSON inputs
    - JSON normalized
    - JSON Grants
    - What makes sense to have in all of those ^^^
