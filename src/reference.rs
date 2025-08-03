
//! A reference implementation for the core functionality of Authzee.
//! 
//! Core workflow:
//! 
//! 1. A user creates identity and resource definitions
//! 2. Validate definitions with `validate_definitions()`. If any errors are returned, return with those errors immediately.
//! 3. Generate JSON Schemas based on definitions with `generate_schemas()`. If any errors are returned, return with those errors immediately.
//! 4. User can customize the schemas at this point
//!     - Should only really update request schema and can add additional controls like minimum number of a specific identity
//! 5. User Create grants to allow or deny actions on resources
//! 6. Validate grants with `validate_grants()`. If any errors are returned, return with those errors immediately.
//! 7. User creates a request.
//! 8. Validate request with `validate_request()`. If any errors are returned, return with those errors immediately.
//! 9. Run authorize() or audit() with the the previously validated grants and request.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value as JsonValue};
use std::collections::{HashMap, HashSet};
use jsonschema::{Draft, JSONSchema};
use jmespath::{compile, JmesPathError};
use regex::Regex;

pub type AnyJSON = JsonValue;
pub type JMESPathSearchFn = dyn Fn(&str, &JsonValue) -> Result<JsonValue, JmesPathError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Effect {
    Allow,
    Deny,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QueryValidation {
    Grant,
    Validate,
    Error,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContextValidation {
    Grant,
    None,
    Validate,
    Error,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DefinitionType {
    Identity,
    Resource,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityDefinition {
    pub identity_type: String,
    pub schema: JsonValue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceDefinition {
    pub resource_type: String,
    pub actions: Vec<String>,
    pub schema: JsonValue,
    pub parent_types: Vec<String>,
    pub child_types: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Grant {
    pub effect: Effect,
    pub actions: Vec<String>,
    pub query: String,
    pub query_validation: QueryValidation,
    pub equality: JsonValue,
    pub data: JsonValue,
    pub context_schema: JsonValue,
    pub context_validation: ContextValidation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    pub identities: HashMap<String, Vec<JsonValue>>,
    pub resource_type: String,
    pub action: String,
    pub resource: JsonValue,
    pub parents: HashMap<String, Vec<JsonValue>>,
    pub children: HashMap<String, Vec<JsonValue>>,
    pub query_validation: QueryValidation,
    pub context: HashMap<String, JsonValue>,
    pub context_validation: ContextValidation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextError {
    pub message: String,
    pub critical: bool,
    pub grant: Grant,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DefinitionError {
    pub message: String,
    pub critical: bool,
    pub definition_type: DefinitionType,
    pub definition: JsonValue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrantError {
    pub message: String,
    pub critical: bool,
    pub grant: JsonValue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JMESPathError {
    pub message: String,
    pub critical: bool,
    pub grant: Grant,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestError {
    pub message: String,
    pub critical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Errors {
    pub context: Vec<ContextError>,
    pub definition: Vec<DefinitionError>,
    pub grant: Vec<GrantError>,
    pub jmespath: Vec<JMESPathError>,
    pub request: Vec<RequestError>,
}

impl Default for Errors {
    fn default() -> Self {
        Self {
            context: Vec::new(),
            definition: Vec::new(),
            grant: Vec::new(),
            jmespath: Vec::new(),
            request: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub errors: Vec<DefinitionError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrantValidationResult {
    pub valid: bool,
    pub errors: Vec<GrantError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestValidationResult {
    pub valid: bool,
    pub errors: Vec<RequestError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluateOneResult {
    pub critical: bool,
    pub applicable: bool,
    pub errors: Errors,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditResponse {
    pub completed: bool,
    pub grants: Vec<Grant>,
    pub errors: Errors,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorizeResponse {
    pub authorized: bool,
    pub completed: bool,
    pub grant: Option<Grant>,
    pub message: String,
    pub errors: Errors,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Schemas {
    pub grant: JsonValue,
    pub errors: JsonValue,
    pub request: JsonValue,
    pub audit: JsonValue,
    pub authorize: JsonValue,
}

pub fn get_identity_definition_schema() -> JsonValue {
    json!({
        "title": "Identity Definition",
        "description": "An identity definition. Defines a type of identity to use with Authzee.",
        "type": "object",
        "additionalProperties": false,
        "required": ["identity_type", "schema"],
        "properties": {
            "identity_type": {
                "title": "Authzee Type",
                "description": "A unique name to identity this type.",
                "type": "string",
                "pattern": "^[A-Za-z0-9_]*$",
                "minLength": 1,
                "maxLength": 256
            },
            "schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema"
            }
        }
    })
}

pub fn get_resource_definition_schema() -> JsonValue {
    json!({
        "title": "Resource Definition",
        "description": "A resource definition. Defines a type of resource to use with Authzee.",
        "type": "object",
        "additionalProperties": false,
        "required": ["resource_type", "actions", "schema", "parent_types", "child_types"],
        "properties": {
            "resource_type": {
                "title": "Authzee Type",
                "description": "A unique name to identity this type.",
                "type": "string",
                "pattern": "^[A-Za-z0-9_]*$",
                "minLength": 1,
                "maxLength": 256
            },
            "actions": {
                "type": "array",
                "uniqueItems": true,
                "items": {
                    "title": "Resource Action",
                    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common.",
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_.:-]*$",
                    "minLength": 1,
                    "maxLength": 512
                }
            },
            "schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema"
            },
            "parent_types": {
                "type": "array",
                "uniqueItems": true,
                "items": {"type": "string"},
                "description": "Types that are a parent of this resource. When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
            },
            "child_types": {
                "type": "array",
                "uniqueItems": true,
                "items": {"type": "string"},
                "description": "Types that are a child of this resource. When instances of these types are passed to the request they will be checked against their schemas and against the hierarchy."
            }
        }
    })
}

pub fn validate_definitions(
    identity_defs: &[IdentityDefinition],
    resource_defs: &[ResourceDefinition],
) -> ValidationResult {
    let mut errors = Vec::new();
    let mut id_types = HashSet::new();
    
    let identity_schema = get_identity_definition_schema();
    let identity_validator = JSONSchema::compile(&identity_schema).unwrap();
    
    for id_def in identity_defs {
        let id_def_value = serde_json::to_value(id_def).unwrap();
        
        if let Err(validation_errors) = identity_validator.validate(&id_def_value) {
            let error_messages: Vec<String> = validation_errors
                .map(|e| e.to_string())
                .collect();
            errors.push(DefinitionError {
                message: format!("Identity definition schema was not valid. Schema Error: {}", error_messages.join(", ")),
                critical: true,
                definition_type: DefinitionType::Identity,
                definition: id_def_value,
            });
        } else {
            if !id_types.insert(&id_def.identity_type) {
                errors.push(DefinitionError {
                    message: format!("Identity types must be unique. '{}' is present more than once.", id_def.identity_type),
                    critical: true,
                    definition_type: DefinitionType::Identity,
                    definition: id_def_value,
                });
            }
        }
    }
    
    let mut r_types = HashSet::new();
    let resource_schema = get_resource_definition_schema();
    let resource_validator = JSONSchema::compile(&resource_schema).unwrap();
    
    for r_def in resource_defs {
        let r_def_value = serde_json::to_value(r_def).unwrap();
        
        if let Err(validation_errors) = resource_validator.validate(&r_def_value) {
            let error_messages: Vec<String> = validation_errors
                .map(|e| e.to_string())
                .collect();
            errors.push(DefinitionError {
                message: format!("Resource definition was not valid. Schema Error: {}", error_messages.join(", ")),
                critical: true,
                definition_type: DefinitionType::Resource,
                definition: r_def_value,
            });
        } else {
            if !r_types.insert(&r_def.resource_type) {
                errors.push(DefinitionError {
                    message: format!("Resource types must be unique. '{}' is present more than once.", r_def.resource_type),
                    critical: true,
                    definition_type: DefinitionType::Resource,
                    definition: r_def_value,
                });
            }
        }
    }
    
    // Validate parent and child type references
    for r_def in resource_defs {
        let r_def_value = serde_json::to_value(r_def).unwrap();
        
        for p_type in &r_def.parent_types {
            if !r_types.contains(p_type) {
                errors.push(DefinitionError {
                    message: format!("Parent type '{}' does not have a corresponding resource definition.", p_type),
                    critical: true,
                    definition_type: DefinitionType::Resource,
                    definition: r_def_value.clone(),
                });
            }
        }
        
        for c_type in &r_def.child_types {
            if !r_types.contains(c_type) {
                errors.push(DefinitionError {
                    message: format!("Child type '{}' does not have a corresponding resource definition.", c_type),
                    critical: true,
                    definition_type: DefinitionType::Resource,
                    definition: r_def_value.clone(),
                });
            }
        }
    }
    
    ValidationResult {
        valid: errors.is_empty(),
        errors,
    }
}

pub fn generate_schemas(
    identity_defs: &[IdentityDefinition],
    resource_defs: &[ResourceDefinition],
) -> Schemas {
    let mut actions = HashSet::new();
    for r_def in resource_defs {
        for action in &r_def.actions {
            actions.insert(action.clone());
        }
    }
    
    let grant_schema = json!({
        "title": "Grant",
        "description": "A grant is an object representing a enacted authorization rule.",
        "type": "object",
        "additionalProperties": false,
        "required": ["effect", "actions", "query", "query_validation", "equality", "data", "context_schema", "context_validation"],
        "properties": {
            "effect": {
                "type": "string",
                "enum": ["allow", "deny"],
                "description": "Any applicable deny grant will always cause the request to be not authorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and not authorized."
            },
            "actions": {
                "type": "array",
                "uniqueItems": true,
                "items": {
                    "type": "string",
                    "enum": actions.iter().collect::<Vec<_>>()
                },
                "description": "List of actions this grant applies to or null to match any resource action."
            },
            "query": {
                "type": "string",
                "description": "JMESPath query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
            },
            "query_validation": {
                "type": "string",
                "title": "Grant-Level Query Validation Setting",
                "description": "Grant-level query validation setting. Set how the query errors are treated. 'validate' - Query errors cause the grant to be inapplicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                "enum": ["validate", "error", "critical"]
            },
            "equality": {
                "description": "Expected value for they query to return. If the query result matches this value the grant is a considered applicable to the request."
            },
            "data": {
                "type": "object",
                "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
            },
            "context_schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema"
            },
            "context_validation": {
                "type": "string",
                "title": "Grant-Level Context Validation",
                "description": "Grant-level context validation setting. Set how the request context is validated against the grant context schema. 'none' - there is no validation. 'validate' - Context is validated and if the context is invalid, the grant is not applicable to the request. 'error' - Includes the 'validate' setting checks, and also adds errors to the result. 'critical' Includes the 'error' setting checks, and will flag the error as critical, thus exiting the workflow early.",
                "enum": ["none", "validate", "error", "critical"]
            }
        }
    });
    
    let errors_schema = json!({
        "title": "Workflow Errors",
        "description": "Errors returned from Authzee workflows.",
        "type": "object",
        "additionalProperties": false,
        "required": ["context", "definition", "grant", "jmespath", "request"],
        "properties": {
            "context": {"type": "array"},
            "definition": {"type": "array"},
            "grant": {"type": "array"},
            "jmespath": {"type": "array"},
            "request": {"type": "array"}
        }
    });
    
    // Build request schema
    let mut request_schema = json!({
        "title": "Workflow Request",
        "description": "Request for an Authzee workflow.",
        "anyOf": [],
        "$defs": {
            "identities": {
                "type": "object",
                "additionalProperties": false,
                "required": [],
                "properties": {}
            },
            "query_validation": {
                "type": "string",
                "enum": ["grant", "validate", "error", "critical"]
            },
            "context": {
                "type": "object",
                "patternProperties": {
                    "^[a-zA-Z0-9_]{1,256}$": {}
                }
            },
            "context_validation": {
                "type": "string",
                "enum": ["grant", "none", "validate", "error", "critical"]
            }
        }
    });
    
    // Add identity definitions to request schema
    for id_def in identity_defs {
        request_schema["$defs"]["identities"]["required"]
            .as_array_mut()
            .unwrap()
            .push(json!(id_def.identity_type));
        request_schema["$defs"]["identities"]["properties"][&id_def.identity_type] = json!({
            "type": "array",
            "items": id_def.schema
        });
    }
    
    // Add resource definitions to request schema
    let type_to_def: HashMap<&String, &ResourceDefinition> = resource_defs
        .iter()
        .map(|d| (&d.resource_type, d))
        .collect();
    
    for (r_type, r_def) in type_to_def {
        let rt_request_schema = json!({
            "title": format!("'{}' Resource Type Workflow Request", r_type),
            "description": format!("'{}' resource type request for an Authzee workflow.", r_type),
            "type": "object",
            "additionalProperties": false,
            "required": ["identities", "resource_type", "action", "resource", "parents", "children", "query_validation", "context", "context_validation"],
            "properties": {
                "identities": {"$ref": "#/$defs/identities"},
                "action": {
                    "type": "string",
                    "enum": r_def.actions
                },
                "resource_type": {"const": r_type},
                "resource": {"$ref": format!("#/$defs/{}", r_type)},
                "parents": {
                    "type": "object",
                    "additionalProperties": false,
                    "required": r_def.parent_types.clone(),
                    "properties": r_def.parent_types.iter().map(|p_type| {
                        (p_type.clone(), json!({
                            "type": "array",
                            "items": {"$ref": format!("#/$defs/{}", p_type)}
                        }))
                    }).collect::<serde_json::Map<String, JsonValue>>()
                },
                "children": {
                    "type": "object",
                    "additionalProperties": false,
                    "required": r_def.child_types.clone(),
                    "properties": r_def.child_types.iter().map(|c_type| {
                        (c_type.clone(), json!({
                            "type": "array",
                            "items": {"$ref": format!("#/$defs/{}", c_type)}
                        }))
                    }).collect::<serde_json::Map<String, JsonValue>>()
                },
                "query_validation": {"$ref": "#/$defs/query_validation"},
                "context": {"$ref": "#/$defs/context"},
                "context_validation": {"$ref": "#/$defs/context_validation"}
            }
        });
        
        request_schema["$defs"][r_type] = r_def.schema.clone();
        request_schema["anyOf"].as_array_mut().unwrap().push(rt_request_schema);
    }
    
    let audit_schema = json!({
        "title": "Audit Response",
        "description": "Response for the audit workflow.",
        "type": "object",
        "additionalProperties": false,
        "required": ["grants", "errors"],
        "properties": {
            "completed": {
                "type": "boolean",
                "description": "The workflow completed."
            },
            "grants": {
                "type": "array",
                "items": grant_schema.clone(),
                "description": "List of grants that are applicable to the request."
            },
            "errors": errors_schema.clone()
        }
    });
    
    let authorize_schema = json!({
        "title": "Authorize Response",
        "description": "Response for the authorize workflow.",
        "type": "object",
        "additionalProperties": false,
        "required": ["authorized", "completed", "grant", "message", "errors"],
        "properties": {
            "authorized": {
                "type": "boolean",
                "description": "true if the request is authorized. false if it is not authorized."
            },
            "completed": {
                "type": "boolean",
                "description": "The workflow completed."
            },
            "grant": {
                "description": "Grant that was responsible for the authorization decision, if applicable.",
                "anyOf": [grant_schema.clone(), {"type": "null"}]
            },
            "message": {
                "type": "string",
                "description": "Details about why the request was authorized or not."
            },
            "errors": errors_schema.clone()
        }
    });
    
    Schemas {
        grant: grant_schema,
        errors: errors_schema,
        request: request_schema,
        audit: audit_schema,
        authorize: authorize_schema,
    }
}

pub fn validate_grants(grants: &[Grant], schema: &JsonValue) -> GrantValidationResult {
    let mut errors = Vec::new();
    let validator = JSONSchema::compile(schema).unwrap();
    
    for grant in grants {
        let grant_value = serde_json::to_value(grant).unwrap();
        if let Err(validation_errors) = validator.validate(&grant_value) {
            let error_messages: Vec<String> = validation_errors
                .map(|e| e.to_string())
                .collect();
            errors.push(GrantError {
                message: format!("The grant is not valid. Schema Error: {}", error_messages.join(", ")),
                critical: true,
                grant: grant_value,
            });
        }
    }
    
    GrantValidationResult {
        valid: errors.is_empty(),
        errors,
    }
}

pub fn validate_request(request: &Request, schema: &JsonValue) -> RequestValidationResult {
    let validator = JSONSchema::compile(schema).unwrap();
    let request_value = serde_json::to_value(request).unwrap();
    
    if let Err(validation_errors) = validator.validate(&request_value) {
        let error_messages: Vec<String> = validation_errors
            .map(|e| e.to_string())
            .collect();
        RequestValidationResult {
            valid: false,
            errors: vec![RequestError {
                message: format!("The request is not valid for the request schema: {}", error_messages.join(", ")),
                critical: true,
            }],
        }
    } else {
        RequestValidationResult {
            valid: true,
            errors: Vec::new(),
        }
    }
}

pub fn evaluate_one<F>(request: &Request, grant: &Grant, search: F) -> EvaluateOneResult
where
    F: Fn(&str, &JsonValue) -> Result<JsonValue, jmespath::JmesPathError>,
{
    let mut result = EvaluateOneResult {
        critical: false,
        applicable: false,
        errors: Errors::default(),
    };
    
    // Check if action matches
    if !grant.actions.is_empty() && !grant.actions.contains(&request.action) {
        return result;
    }
    
    // Context validation
    let c_val = match request.context_validation {
        ContextValidation::Grant => &grant.context_validation,
        _ => &request.context_validation,
    };
    
    if !matches!(c_val, ContextValidation::None) {
        let context_validator = JSONSchema::compile(&grant.context_schema).unwrap();
        let context_value = serde_json::to_value(&request.context).unwrap();
        
        if let Err(validation_errors) = context_validator.validate(&context_value) {
            let is_critical = matches!(c_val, ContextValidation::Critical);
            let error_messages: Vec<String> = validation_errors
                .map(|e| e.to_string())
                .collect();
            
            if matches!(c_val, ContextValidation::Error) || is_critical {
                result.errors.context.push(ContextError {
                    message: error_messages.join(", "),
                    critical: is_critical,
                    grant: grant.clone(),
                });
                if is_critical {
                    result.critical = true;
                }
            }
            return result;
        }
    }
    
    // Query evaluation
    let query_data = json!({
        "request": serde_json::to_value(request).unwrap(),
        "grant": serde_json::to_value(grant).unwrap()
    });
    
    match search(&grant.query, &query_data) {
        Ok(query_result) => {
            if query_result == grant.equality {
                result.applicable = true;
            }
        }
        Err(jmespath_error) => {
            let q_val = match request.query_validation {
                QueryValidation::Grant => &grant.query_validation,
                _ => &request.query_validation,
            };
            
            let is_critical = matches!(q_val, QueryValidation::Critical);
            
            if matches!(q_val, QueryValidation::Error) || is_critical {
                result.errors.jmespath.push(JMESPathError {
                    message: jmespath_error.to_string(),
                    critical: is_critical,
                    grant: grant.clone(),
                });
                if is_critical {
                    result.critical = true;
                }
            }
        }
    }
    
    result
}

pub fn audit<F>(request: &Request, grants: &[Grant], search: F) -> AuditResponse
where
    F: Fn(&str, &JsonValue) -> Result<JsonValue, jmespath::JmesPathError>,
{
    let mut result = AuditResponse {
        completed: true,
        grants: Vec::new(),
        errors: Errors::default(),
    };
    
    for grant in grants {
        let grant_eval = evaluate_one(request, grant, &search);
        
        result.errors.context.extend(grant_eval.errors.context);
        result.errors.jmespath.extend(grant_eval.errors.jmespath);
        
        if grant_eval.critical {
            result.completed = false;
            return result;
        }
        
        if grant_eval.applicable {
            result.grants.push(grant.clone());
        }
    }
    
    result
}

pub fn authorize<F>(request: &Request, grants: &[Grant], search: F) -> AuthorizeResponse
where
    F: Fn(&str, &JsonValue) -> Result<JsonValue, jmespath::JmesPathError>,
{
    let mut errors = Errors::default();
    let mut allow_grants = Vec::new();
    let mut deny_grants = Vec::new();
    
    for grant in grants {
        if grant.actions.contains(&request.action) || grant.actions.is_empty() {
            match grant.effect {
                Effect::Allow => allow_grants.push(grant),
                Effect::Deny => deny_grants.push(grant),
            }
        }
    }
    
    // Check deny grants first
    for grant in deny_grants {
        let grant_eval = evaluate_one(request, grant, &search);
        errors.context.extend(grant_eval.errors.context);
        errors.jmespath.extend(grant_eval.errors.jmespath);
        
        if grant_eval.critical {
            return AuthorizeResponse {
                authorized: false,
                completed: false,
                grant: Some(grant.clone()),
                message: "A critical error has occurred. Therefore, the request is not authorized.".to_string(),
                errors,
            };
        }
        
        if grant_eval.applicable {
            return AuthorizeResponse {
                authorized: false,
                completed: true,
                grant: Some(grant.clone()),
                message: "A deny grant is applicable to the request. Therefore, the request is not authorized.".to_string(),
                errors,
            };
        }
    }
    
    // Check allow grants
    for grant in allow_grants {
        let grant_eval = evaluate_one(request, grant, &search);
        errors.context.extend(grant_eval.errors.context);
        errors.jmespath.extend(grant_eval.errors.jmespath);
        
        if grant_eval.critical {
            return AuthorizeResponse {
                authorized: false,
                completed: false,
                grant: Some(grant.clone()),
                message: "A critical error has occurred. Therefore, the request is not authorized.".to_string(),
                errors,
            };
        }
        
        if grant_eval.applicable {
            return AuthorizeResponse {
                authorized: true,
                completed: true,
                grant: Some(grant.clone()),
                message: "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.".to_string(),
                errors,
            };
        }
    }
    
    AuthorizeResponse {
        authorized: false,
        completed: true,
        grant: None,
        message: "No allow or deny grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.".to_string(),
        errors,
    }
}

pub fn audit_workflow<F>(
    identity_defs: &[IdentityDefinition],
    resource_defs: &[ResourceDefinition],
    grants: &[Grant],
    request: &Request,
    search: F,
) -> AuditResponse
where
    F: Fn(&str, &JsonValue) -> Result<JsonValue, jmespath::JmesPathError>,
{
    let mut errors = Errors::default();
    
    // Validate definitions
    let def_val = validate_definitions(identity_defs, resource_defs);
    errors.definition = def_val.errors;
    if !def_val.valid {
        return AuditResponse {
            completed: false,
            grants: Vec::new(),
            errors,
        };
    }
    
    // Generate schemas
    let schemas = generate_schemas(identity_defs, resource_defs);
    
    // Validate grants
    let grant_val = validate_grants(grants, &schemas.grant);
    errors.grant = grant_val.errors;
    if !grant_val.valid {
        return AuditResponse {
            completed: false,
            grants: Vec::new(),
            errors,
        };
    }
    
    // Validate request
    let request_val = validate_request(request, &schemas.request);
    errors.request = request_val.errors;
    if !request_val.valid {
        return AuditResponse {
            completed: false,
            grants: Vec::new(),
            errors,
        };
    }
    
    audit(request, grants, search)
}

pub fn authorize_workflow<F>(
    identity_defs: &[IdentityDefinition],
    resource_defs: &[ResourceDefinition],
    grants: &[Grant],
    request: &Request,
    search: F,
) -> AuthorizeResponse
where
    F: Fn(&str, &JsonValue) -> Result<JsonValue, jmespath::JmesPathError>,
{
    let mut errors = Errors::default();
    
    // Validate definitions
    let def_val = validate_definitions(identity_defs, resource_defs);
    errors.definition = def_val.errors;
    if !def_val.valid {
        return AuthorizeResponse {
            authorized: false,
            grant: None,
            message: "One or more identity and/or resource definitions are not valid. Therefore, the request is not authorized.".to_string(),
            completed: false,
            errors,
        };
    }
    
    // Generate schemas
    let schemas = generate_schemas(identity_defs, resource_defs);
    
    // Validate grants
    let grant_val = validate_grants(grants, &schemas.grant);
    errors.grant = grant_val.errors;
    if !grant_val.valid {
        return AuthorizeResponse {
            authorized: false,
            grant: None,
            message: "One or more grants are not valid. Therefore, the request is not authorized.".to_string(),
            completed: false,
            errors,
        };
    }
    
    // Validate request
    let request_val = validate_request(request, &schemas.request);
    errors.request = request_val.errors;
    if !request_val.valid {
        return AuthorizeResponse {
            authorized: false,
            grant: None,
            message: "The request is not valid. Therefore the request is not authorized.".to_string(),
            completed: false,
            errors,
        };
    }
    
    authorize(request, grants, search)
}

#[cfg(test)]
mod tests {
    use super::*;
    use jmespath::compile;

    fn jmespath_search(query: &str, data: &JsonValue) -> Result<JsonValue, jmespath::JmesPathError> {
        let expr = compile(query)?;
        Ok(expr.search(data)?)
    }

    #[test]
    fn test_basic_workflow() {
        let identity_defs = vec![
            IdentityDefinition {
                identity_type: "user".to_string(),
                schema: json!({"type": "object", "properties": {"id": {"type": "string"}}}),
            }
        ];

        let resource_defs = vec![
            ResourceDefinition {
                resource_type: "document".to_string(),
                actions: vec!["read".to_string(), "write".to_string()],
                schema: json!({"type": "object", "properties": {"id": {"type": "string"}}}),
                parent_types: vec![],
                child_types: vec![],
            }
        ];

        let grants = vec![
            Grant {
                effect: Effect::Allow,
                actions: vec!["read".to_string()],
                query: "request.resource.id".to_string(),
                query_validation: QueryValidation::Validate,
                equality: json!("doc1"),
                data: json!({}),
                context_schema: json!({"type": "object"}),
                context_validation: ContextValidation::None,
            }
        ];

        let request = Request {
            identities: {
                let mut map = HashMap::new();
                map.insert("user".to_string(), vec![json!({"id": "user1"})]);
                map
            },
            resource_type: "document".to_string(),
            action: "read".to_string(),
            resource: json!({"id": "doc1"}),
            parents: HashMap::new(),
            children: HashMap::new(),
            query_validation: QueryValidation::Grant,
            context: HashMap::new(),
            context_validation: ContextValidation::Grant,
        };

        let result = authorize_workflow(&identity_defs, &resource_defs, &grants, &request, jmespath_search);
        assert!(result.authorized);
        assert!(result.completed);
    }
}
// ```

// You'll also need to add these dependencies to your `Cargo.toml`:

// ```toml
// [dependencies]
// serde = { version = "1.0", features = ["derive"] }
// serde_json = "1.0"
// jsonschema = "0.17"
// jmespath = "0.3"
// regex = "1.0"
// ```

// This Rust implementation maintains the same structure and functionality as the Python version while leveraging Rust's type system for better safety and performance. The main differences include:

// 1. **Strong typing**: All structs are properly typed with serde serialization/deserialization
// 2. **Error handling**: Uses Result types for proper error propagation
// 3. **Memory safety**: No need for manual memory management
// 4. **Generic functions**: Uses generic parameters for the search function to allow different JMESPath implementations
// 5. **Borrowing**: Uses references where possible to avoid unnecessary cloning

// The API remains very similar to the Python version, making it easy to migrate existing code that uses the Python implementation.