# Changelog

Changelog for the Authzee authorization engine SDK standard.
This changelog follows does not follow the versioning from the specification.  Notes will be added where SDK standard changes are made to match specification changes.
In general the SDK standard is not as strict as the specification, but changes that roll down from the spec will be implemented accordingly. 

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- 
## [Unreleased] - YYYY-MM-DD

- This version of the SDK Standard supports up to at least the following version of the Authzee Specification: 
    - ****
- Where there changes in the Authzee Specification that were implemented in this version of the SDK Standard?
    - **Yes or No**
    - If yes, those changes are noted in the changelog notes prefixed by: **SPECIFICATION CHANGE**

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security 
-->


## [0.3.0] - 2026-06-15

- This version of the SDK Standard supports up to at least the following version of the Authzee Specification: 
    - **0.3.0**
- Where there changes in the Authzee Specification that were implemented in this version of the SDK Standard?
    - **Yes**
    - If yes, those changes are noted in the changelog notes prefixed by: **SPECIFICATION CHANGE**

Release 0.3.0 includes many key changes to increase flexibility and scalability, while also balancing usability and maintenance.

### Added

- **SPECIFICATION CHANGE** - Batch Audit and Authorize operations 
- **SPECIFICATION CHANGE** - Context and Context Definitions.  Context is structured data with a schema that is passed with a request now. They are also unique types.
- **SPECIFICATION CHANGE** - SDK standard to register, update, and delete definitions
- **SPECIFICATION CHANGE** - SKD standard to register, update, and delete grants
- Full requests are now handled by the compute module
- JMESPath standard functions
    - LEFT JOIN
    - OUTER JOIN
    - 

### Changed

- **SPECIFICATION CHANGE** - General naming conventions around workflows and separate them into part where the unique part of processing is now called a function. 
- **SPECIFICATION CHANGE** - Context is now structured instead of free form data
- **SPECIFICATION CHANGE** - Error returns so now they do not need to include all error types
- **SPECIFICATION CHANGE** - Identity request property so that it does not need to specify all identity types
- **SPECIFICATION CHANGE** - Audit Function so that is now returns all grants, and metadata about the request being processed against the grant
- **SPECIFICATION CHANGE** - SDK standards around all specification changes

### Removed

- **SPECIFICATION CHANGE** - Parent and Child relationships from resource definitions in favor of more flexible context
- **SPECIFICATION CHANGE** - Grant fields for context
- **SPECIFICATION CHANGE** - Context Errors


## [0.2.0] - 2025-08-16

- This version of the SDK Standard supports up to at least the following version of the Authzee Specification: 
    - **0.2.0**
- Where there changes in the Authzee Specification that were implemented in this version of the SDK Standard?
    - **Yes**
    - If yes, those changes are noted in the changelog notes. 

### Changed
    
- **SPECIFICATION CHANGE** -Authorize workflow now only returns critical errors.  The `errors` field was renamed to `critical_errors` to make this clear
    - This was because authorize should be optimized around a binary decision.  Returning an unmanageable number of errors at a time is not scalable in the worst cases.


## [0.1.1] - 2025-08-14

- This version of the SDK Standard supports up to at least the following version of the Authzee Specification: 
    - **0.1.0**
- Where there changes in the Authzee Specification that were implemented in this version of the SDK Standard?
    - &&Yes**
    - If yes, those changes are noted in the changelog notes. 

### Fixed

- **SPECIFICATION CHANGE** - Clarify how grants that match all actions (no actions specified) are handled.  They will match all current and future actions. - SDK standard updated to reflect this. 


### [0.1.0] - 2025-08-03

- This version of the SDK Standard supports up to at least the following version of the Authzee Specification: 
    - **0.1.0**
- Where there changes in the Authzee Specification that were implemented in this version of the SDK Standard?
    - **Yes**
    - If yes, those changes are noted in the changelog notes. 


- Initial SDK standard version to match spec
