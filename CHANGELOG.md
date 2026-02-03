# Changelog

Changelog for the Authzee authorization engine specification.
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- 
## [Unreleased] - YYYY-MM-DD

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security 
-->


## [0.3.0] - YYYY-MM-DD

Release 0.3.0 includes many key changes to increase flexibility and scalability, while also balancing usability and maintenance.

### Added

- Batch Audit and Authorize operations 
    - Now send several requests for the same resource actions at once to optimize storage and compute. 
- Context and Context Definitions.  Context is structured data with a schema that is passed with a request now. They are also unique types.
- SDK standard to put, and delete defs
- SKD standard to register, and delete grants

### Changed

- General naming conventions around workflows and separate them into part where the unique part of processing is now called an operation. 
- Workflow was generally changed to focus less on condensing everything down to a rigid schema and having a more robust and flexible way to manage definitions on the fly.  Having a set schema for everything and then adding additional validation logic as needed. 
- Context is now structured data handled at the request level instead of the grant level
- Errors do not need to include all error types
- Identity request property so that it does not need to specify all identity types
- Audit Function so that is now returns all grants, and metadata about the request being processed against the grant
- SDK standards around all specification changes
- Result property `is_complete` changed to `has_failed` since it makes it more clear that the flag is to mark failures of the requests


### Removed

- Parent and Child relationships from resource definitions in favor of more flexible context
- Grant fields for context
- Context Errors - context is now handled in request validation


## [0.2.0] - 2025-08-16

### Changed
    - Authorize workflow now only returns critical errors.  The `errors` field was renamed to `critical_errors` to make this clear
        - This was because authorize should be optimized around a binary decision.  Returning an unmanageable number of errors at a time is not scalable in the worst cases.


## [0.1.1] - 2025-08-14

### Fixed

- Clarify how grants that match all actions (no actions specified) are handled.  They will match all current and future actions. 


### [0.1.0] - 2025-08-03

- Initial Specification and Reference Implementation 
