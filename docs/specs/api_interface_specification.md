# Comprehensive API and Interface Specification for ocode Agent Architecture

## 1. Introduction

This document specifies the Application Programming Interfaces (APIs) and communication protocols governing the interactions between the various components of the ocode agent architecture. As the ocode agent evolves into a sophisticated, self-improving system, clear, robust, and well-defined interfaces are paramount for ensuring modularity, scalability, maintainability, and seamless interoperability between its core pillars: the Explicit Task Planning (ETP) system, the Code Knowledge Graph (CKG), and the Self-Improvement (SI) system (including its sub-components: Performance Monitoring & Analytics (PMA), Feedback & Learning Loop (FLL), Tool Generation & Augmentation (TGA), and Knowledge Base Integration (KBI)).

The goal of this specification is to provide a definitive contract for component developers, enabling independent development and deployment while guaranteeing system-wide coherence and data integrity. It will cover communication patterns, data models, service endpoints, authentication, error handling, and versioning strategies.

## 2. Core Principles of API Design

Our API design will adhere to the following principles to ensure a robust and future-proof architecture:

*   **Modularity & Decoupling:** Components should interact primarily through well-defined APIs, minimizing direct dependencies and allowing for independent evolution and deployment.
*   **Clarity & Consistency:** APIs will follow consistent naming conventions, data structures, and interaction patterns to reduce cognitive load for developers and improve system predictability.
*   **Scalability:** The chosen protocols and design patterns will support high throughput and low latency, accommodating the increasing data volume and computational demands of a continuously learning agent.
*   **Resilience & Error Handling:** APIs will be designed to gracefully handle errors, provide informative feedback, and support retry mechanisms where appropriate.
*   **Security:** All inter-component communication will be secured to protect sensitive data and prevent unauthorized access or manipulation.
*   **Observability:** APIs will expose metrics and logging capabilities to facilitate monitoring, debugging, and performance analysis.
*   **Versioning:** A clear strategy for API versioning will be established to manage changes and ensure backward compatibility, minimizing disruption to integrated components.
*   **Data Integrity:** Data models will enforce strict schemas and validation rules to maintain the consistency and quality of information exchanged across the system.

## 3. Inter-Component Communication Protocols

The ocode agent architecture will employ a hybrid approach to inter-component communication, leveraging different protocols based on the specific interaction patterns and performance requirements.

### 3.1. Synchronous Request/Response (gRPC)

For real-time, high-performance, and strongly-typed communication between core services (e.g., ETP querying CKG for knowledge, TGA requesting code generation from an LLM service), gRPC will be the primary protocol. gRPC offers:

*   **Performance:** Built on HTTP/2, it supports multiplexing, header compression, and server push, leading to lower latency and higher throughput.
*   **Strong Typing:** Uses Protocol Buffers for defining service interfaces and message structures, ensuring strict data contracts and compile-time validation.

*   **Bidirectional Streaming:** Supports streaming RPCs, useful for continuous data flows (e.g., real-time feedback from execution environments).

**Use Cases:**
*   ETP querying CKG for `CodeEntity` or `ProblemType` information.
*   FLL (AEA/SPI) querying CKG for contextual data during analysis.
*   TGA requesting code synthesis from an internal LLM service.
*   Tool Dispatcher invoking internal, generated tools.

### 3.2. Asynchronous Event Streaming (Kafka/Pub-Sub)

For decoupled, scalable, and fault-tolerant communication, especially for telemetry, logging, and notifications, an asynchronous event streaming platform (e.g., Apache Kafka, Google Cloud Pub/Sub) will be utilized. This enables components to publish events without direct knowledge of their consumers, and consumers to process events independently.

*   **Decoupling:** Producers and consumers are independent, improving system resilience and allowing for easier evolution of individual components.
*   **Scalability:** Designed for high-throughput, low-latency data ingestion and distribution.

*   **Durability:** Events are persisted, allowing consumers to catch up on missed events or for historical analysis.
*   **Real-time Processing:** Supports real-time stream processing for immediate reactions to events.

**Use Cases:**
*   PMA publishing `ExecutionAttempt` logs, `Error` events, and `resource_metrics`.
*   FLL publishing `FailureAnalysisReport` and `ProvenStrategy` objects.
*   TGA publishing `ProposedTool` validation results.
*   KBI publishing `PlanModificationProposal` and `ToolReviewRequest` events for HITL.
*   General system-wide logging and audit trails.

### 3.3. RESTful HTTP (for External/Human-facing Interfaces)

For external integrations, human-facing dashboards, and less performance-critical internal interactions, RESTful HTTP APIs will be used. REST offers:

*   **Simplicity & Ubiquity:** Widely understood and supported, making integration with external systems and UIs straightforward.
*   **Statelessness:** Simplifies server design and improves scalability.

*   **Resource-Oriented:** Intuitive for managing resources (e.g., `Task` objects, `User` profiles).

**Use Cases:**
*   User interface (UI) interacting with the agent to submit `Task` requests or review `HITL` queues.
*   External systems submitting `Task` requests or querying agent status.
*   Internal administrative interfaces.

### 3.4. Shared Memory / In-Process (for tightly coupled modules)

For very tightly coupled modules within the same process space (e.g., a sub-component directly calling a utility function within the same service), direct function calls or shared memory mechanisms may be used for maximum performance. These interactions are typically not exposed as formal APIs.

**Use Cases:**
*   Internal utility functions within the ETP or FLL services.
*   Direct access to in-memory caches or data structures.

**Note:** The choice of protocol for each interaction will be explicitly defined in the subsequent sections detailing component-specific APIs. All network communication will be encrypted (e.g., TLS for gRPC and HTTPS for REST).

## 4. Data Models for API Payloads

This section defines the canonical data models for the primary entities exchanged between ocode agent components. These models will be specified using Protocol Buffers (Protobuf) for gRPC-based communication, and their JSON equivalents for RESTful interfaces and event streaming. UUIDs will be used for all primary identifiers to ensure global uniqueness.

### 4.1. `Task` Data Model

Represents a high-level objective or user request submitted to the ocode agent.

```protobuf
message Task {
  string task_id = 1; // Unique identifier for the task (UUID)
  string user_id = 2; // Identifier of the user who initiated the task
  string prompt = 3; // Natural language description of the task
  repeated string context_files = 4; // List of absolute file paths relevant to the task
  map<string, string> metadata = 5; // Arbitrary key-value pairs for additional context
  TaskStatus status = 6; // Current status of the task
  google.protobuf.Timestamp created_at = 7; // Timestamp of task creation
  google.protobuf.Timestamp updated_at = 8; // Last updated timestamp
  google.protobuf.Timestamp completed_at = 9; // Timestamp of task completion (if applicable)
  string assigned_agent_id = 10; // ID of the agent instance currently handling the task
}

enum TaskStatus {
  TASK_STATUS_UNSPECIFIED = 0;
  TASK_STATUS_PENDING = 1;
  TASK_STATUS_IN_PROGRESS = 2;
  TASK_STATUS_COMPLETED_SUCCESS = 3;
  TASK_STATUS_COMPLETED_FAILURE = 4;
  TASK_STATUS_CANCELLED = 5;
  TASK_STATUS_PAUSED = 6;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "user_id": "user-123",
  "prompt": "Refactor the authentication module to use OAuth2",
  "context_files": [
    "/project/src/auth.py",
    "/project/tests/test_auth.py"
  ],
  "metadata": {
    "priority": "high",
    "jira_ticket": "OCD-456"
  },
  "status": "TASK_STATUS_IN_PROGRESS",
  "created_at": "2025-06-26T10:00:00Z",
  "updated_at": "2025-06-26T10:30:00Z",
  "assigned_agent_id": "agent-alpha-1"
}
```

### 4.2. `ExecutionAttempt` Data Model

Represents a single attempt by the agent to execute a tool or a sequence of internal actions as part of a `Task`. This is a key data point for the Performance Monitoring & Analytics (PMA) component.

```protobuf
message ExecutionAttempt {
  string attempt_id = 1; // Unique identifier for the execution attempt (UUID)
  string task_id = 2; // ID of the parent task
  string agent_id = 3; // ID of the agent instance performing the attempt
  string tool_name = 4; // Name of the tool invoked (e.g., "run_shell_command", "read_file")
  google.protobuf.Struct input_parameters = 5; // JSON representation of input parameters to the tool
  string raw_command = 6; // For shell tools, the raw command string executed
  google.protobuf.Timestamp started_at = 7; // Timestamp when the attempt started
  google.protobuf.Timestamp completed_at = 8; // Timestamp when the attempt completed
  ExecutionOutcome outcome = 9; // Outcome of the attempt
  string stdout = 10; // Standard output from the tool execution
  string stderr = 11; // Standard error from the tool execution
  int32 exit_code = 12; // Exit code of the tool execution
  string error_message = 13; // High-level error message if outcome is FAILURE
  google.protobuf.Struct resource_metrics = 14; // Resource usage metrics (CPU, memory, tokens, API calls)
  string environment_snapshot_id = 15; // Reference to an Environment snapshot (UUID)
}

enum ExecutionOutcome {
  EXECUTION_OUTCOME_UNSPECIFIED = 0;
  EXECUTION_OUTCOME_SUCCESS = 1;
  EXECUTION_OUTCOME_FAILURE = 2;
  EXECUTION_OUTCOME_TIMEOUT = 3;
  EXECUTION_OUTCOME_INTERRUPTED = 4;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "attempt_id": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "agent_id": "agent-alpha-1",
  "tool_name": "run_shell_command",
  "input_parameters": {
    "command": "git status"
  },
  "raw_command": "git status",
  "started_at": "2025-06-26T10:30:00Z",
  "completed_at": "2025-06-26T10:30:01Z",
  "outcome": "EXECUTION_OUTCOME_SUCCESS",
  "stdout": "On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean\n",
  "stderr": "",
  "exit_code": 0,
  "error_message": "",
  "resource_metrics": {
    "cpu_usage_percent": 0.5,
    "memory_usage_mb": 10.2,
    "token_count_in": 5,
    "token_count_out": 50
  },
  "environment_snapshot_id": "c3d4e5f6-a7b8-9012-3456-7890abcdef01"
}
```

### 4.3. `Error` Data Model

Represents a specific, observed error event resulting from a failed `ExecutionAttempt`. This data is crucial for the Automated Error Analysis (AEA) component of the FLL.

```protobuf
message Error {
  string error_id = 1; // Unique identifier for the error instance (UUID)
  string attempt_id = 2; // ID of the ExecutionAttempt that resulted in this error
  string error_code = 3; // Standardized error code (e.g., HTTP status, OS error code, custom code)
  string error_message = 4; // Raw error message from stdout/stderr
  string stack_trace = 5; // Full stack trace if available
  bool is_transient = 6; // True if the error is likely temporary (e.g., network glitch, rate limit)
  google.protobuf.Timestamp occurred_at = 7; // Timestamp when the error was observed
  google.protobuf.Struct context = 8; // Additional context relevant to the error (e.g., file path, line number)
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "error_id": "c3d4e5f6-a7b8-9012-3456-7890abcdef02",
  "attempt_id": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
  "error_code": "128",
  "error_message": "*** Please tell me who you are.\n\nRun\n\n  git config --global user.email \"you@example.com\"\n  git config --global user.name \"Your Name\"\n\nto set your account's default identity.\nOmit --global to set the identity only in this repository.",
  "stack_trace": "",
  "is_transient": false,
  "occurred_at": "2025-06-26T10:30:01Z",
  "context": {
    "tool": "git",
    "subcommand": "commit"
  }
}
```

### 4.4. `ErrorPattern` Data Model

Represents a generalized, canonical class of errors. This is a key entity in the Self-Improvement Knowledge Graph, used by AEA for classification and by APR for strategy lookup.

```protobuf
message ErrorPattern {
  string pattern_id = 1; // Unique identifier for the error pattern (UUID)
  string name = 2; // Human-readable name (e.g., "GitAuthenticationFailure", "PythonModuleNotFound")
  string description = 3; // Detailed description of the error pattern
  repeated string canonical_regex = 4; // List of regex patterns to match against error messages/stderr
  repeated string common_causes = 5; // List of common underlying causes for this pattern
  repeated string suggested_remediations = 6; // High-level suggested fixes
  google.protobuf.Timestamp created_at = 7;
  google.protobuf.Timestamp updated_at = 8;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "pattern_id": "d4e5f6a7-b8c9-0123-4567-890abcdef03",
  "name": "GitAuthenticationFailure",
  "description": "Occurs when Git operations fail due to missing or incorrect user identity configuration.",
  "canonical_regex": [
    ".*Please tell me who you are.*",
    ".*Authentication failed for.*"
  ],
  "common_causes": [
    "user.email or user.name not configured",
    "SSH key not added to agent",
    "Incorrect personal access token"
  ],
  "suggested_remediations": [
    "Configure git user.email and user.name",
    "Add SSH key to ssh-agent",
    "Generate new personal access token"
  ],
  "created_at": "2025-06-01T00:00:00Z",
  "updated_at": "2025-06-15T12:00:00Z"
}
```

### 4.5. `FailureAnalysisReport` Data Model

Represents a structured report generated by the Automated Error Analysis (AEA) component, detailing the diagnosis of a failed `ExecutionAttempt`.

```protobuf
message FailureAnalysisReport {
  string report_id = 1; // Unique identifier for the report (UUID)
  string task_id = 2; // ID of the parent task
  string failed_attempt_id = 3; // ID of the ExecutionAttempt that failed
  string error_id = 4; // ID of the specific Error instance
  string error_pattern_id = 5; // ID of the matched ErrorPattern (if any)
  string inferred_root_cause = 6; // Inferred root cause of the failure
  string culprit_action_id = 7; // ID of the specific action/tool call identified as the culprit
  string proposed_remediation_strategy_description = 8; // High-level description of proposed fix
  float confidence_score = 9; // Confidence in the analysis (0.0-1.0)
  google.protobuf.Timestamp analysis_timestamp = 10; // Timestamp of the analysis
  repeated string relevant_ckg_entities = 11; // List of CKG entity IDs relevant to the analysis
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "report_id": "e5f6a7b8-c9d0-1234-5678-90abcdef04",
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "failed_attempt_id": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
  "error_id": "c3d4e5f6-a7b8-9012-3456-7890abcdef02",
  "error_pattern_id": "d4e5f6a7-b8c9-0123-4567-890abcdef03",
  "inferred_root_cause": "Git user identity not configured globally.",
  "culprit_action_id": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
  "proposed_remediation_strategy_description": "Configure git global user.email and user.name before committing.",
  "confidence_score": 0.95,
  "analysis_timestamp": "2025-06-26T10:30:05Z",
  "relevant_ckg_entities": [
    "ckg-entity-git-config",
    "ckg-entity-user-identity"
  ]
}
```

### 4.6. `ProvenStrategy` Data Model

Represents a generalized, empirically validated sequence of actions or plan fragment that has consistently led to successful outcomes for a specific problem type. Generated by the Success Pattern Identification (SPI) component.

```protobuf
message ProvenStrategy {
  string strategy_id = 1; // Unique identifier for the proven strategy (UUID)
  string name = 2; // Human-readable name for the strategy
  string description = 3; // Detailed description of what the strategy achieves
  google.protobuf.Struct template_plan_fragment = 4; // Parameterized representation of the action sequence
  google.protobuf.Struct applicability_conditions = 5; // Rules/conditions for when this strategy is applicable
  google.protobuf.Struct average_performance_metrics = 6; // Avg. duration, token usage, etc.
  float success_rate = 7; // Historical success rate (0.0-1.0)
  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp updated_at = 9;
  repeated string related_problem_types = 10; // List of ProblemType IDs this strategy addresses
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "strategy_id": "f6a7b8c9-d0e1-2345-6789-0abcdef05",
  "name": "GitGlobalConfigSetup",
  "description": "Sets up global Git user.email and user.name for authentication.",
  "template_plan_fragment": {
    "steps": [
      {
        "tool": "run_shell_command",
        "parameters": {
          "command": "git config --global user.email \"${user_email}\""
        }
      },
      {
        "tool": "run_shell_command",
        "parameters": {
          "command": "git config --global user.name \"${user_name}\""
        }
      }
    ]
  },
  "applicability_conditions": {
    "environment": {
      "git_identity_configured": false
    },
    "problem_type": "GitAuthenticationFailure"
  },
  "average_performance_metrics": {
    "avg_duration_ms": 500,
    "avg_token_usage": 20
  },
  "success_rate": 0.98,
  "created_at": "2025-06-20T09:00:00Z",
  "updated_at": "2025-06-26T10:40:00Z",
  "related_problem_types": [
    "d4e5f6a7-b8c9-0123-4567-890abcdef03"
  ]
}
```

### 4.7. `ProposedTool` Data Model

Represents a tool generated by the Tool Generation & Augmentation (TGA) component, awaiting validation and integration into the agent's toolset.

```protobuf
message ProposedTool {
  string tool_id = 1; // Unique identifier for the proposed tool (UUID)
  string name = 2; // Proposed name of the tool
  string description = 3; // Proposed description of the tool's functionality
  google.protobuf.Struct signature = 4; // Protobuf representation of the tool's function signature (parameters, return type)
  string source_code = 5; // The generated source code for the tool
  string test_code = 6; // The generated test code for the tool
  string documentation = 7; // Generated documentation for the tool
  string language = 8; // Programming language of the tool (e.g., "python", "typescript", "shell")
  repeated string dependencies = 9; // List of external dependencies required by the tool
  ToolValidationStatus validation_status = 10; // Current validation status
  google.protobuf.Struct validation_results = 11; // Detailed results from static analysis, tests, benchmarks
  google.protobuf.Timestamp created_at = 12;
  google.protobuf.Timestamp updated_at = 13;
  string generated_by_agent_id = 14; // ID of the agent instance that generated this tool
}

enum ToolValidationStatus {
  TOOL_VALIDATION_STATUS_UNSPECIFIED = 0;
  TOOL_VALIDATION_STATUS_PENDING = 1;
  TOOL_VALIDATION_STATUS_IN_PROGRESS = 2;
  TOOL_VALIDATION_STATUS_PASSED = 3;
  TOOL_VALIDATION_STATUS_FAILED = 4;
  TOOL_VALIDATION_STATUS_HUMAN_REVIEW_REQUIRED = 5;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "tool_id": "g7h8i9j0-k1l2-3456-7890-abcdef012345",
  "name": "InstallPythonPackage",
  "description": "Installs a specified Python package using pip.",
  "signature": {
    "parameters": [
      {
        "name": "package_name",
        "type": "string",
        "description": "Name of the Python package to install"
      },
      {
        "name": "version",
        "type": "string",
        "description": "Optional: Specific version of the package",
        "optional": true
      }
    ],
    "returns": {
      "type": "boolean",
      "description": "True if installation was successful, false otherwise"
    }
  },
  "source_code": "def install_python_package(package_name, version=None):\n    cmd = f\"pip install {package_name}\"\n    if version: cmd += f\"=={version}\"\n    import subprocess\n    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)\n    return result.returncode == 0",
  "test_code": "import unittest\nfrom your_module import install_python_package\nclass TestInstallPythonPackage(unittest.TestCase):\n    def test_install_requests(self):\n        self.assertTrue(install_python_package(\"requests\"))\n",
  "documentation": "# Install Python Package\n\nThis tool installs a Python package.\n\n## Usage\n\n`InstallPythonPackage(package_name=\"requests\", version=\"2.28.1\")`\n",
  "language": "python",
  "dependencies": [
    "pip"
  ],
  "validation_status": "TOOL_VALIDATION_STATUS_PENDING",
  "validation_results": {},
  "created_at": "2025-06-26T11:00:00Z",
  "generated_by_agent_id": "agent-alpha-1"
}
```

### 4.8. `PlanModificationProposal` Data Model

Represents a proposed change to the Explicit Task Planning (ETP) system's strategies or templates, generated by the Adaptive Plan Refinement (APR) component, and potentially requiring Human-in-the-Loop (HITL) review.

```protobuf
message PlanModificationProposal {
  string proposal_id = 1; // Unique identifier for the proposal (UUID)
  string task_id = 2; // ID of the task that triggered this proposal (if applicable)
  ProposalType type = 3; // Type of modification proposed
  string target_entity_id = 4; // ID of the ETP plan template, strategy, or tool to modify
  google.protobuf.Struct modifications = 5; // Detailed description of changes (e.g., diff, new plan fragment)
  string rationale = 6; // Explanation of why this change is proposed
  string source_report_id = 7; // ID of the FailureAnalysisReport or ProvenStrategy that led to this proposal
  ProposalStatus status = 8; // Current status of the proposal
  string proposed_by_agent_id = 9; // ID of the agent instance that generated this proposal
  google.protobuf.Timestamp created_at = 10;
  google.protobuf.Timestamp updated_at = 11;
  string human_reviewer_id = 12; // ID of the human reviewer (if assigned/reviewed)
  google.protobuf.Timestamp review_timestamp = 13; // Timestamp of human review
}

enum ProposalType {
  PROPOSAL_TYPE_UNSPECIFIED = 0;
  PROPOSAL_TYPE_ADD_PRECONDITION = 1;
  PROPOSAL_TYPE_MODIFY_ERROR_HANDLING = 2;
  PROPOSAL_TYPE_REPLACE_PLAN_FRAGMENT = 3;
  PROPOSAL_TYPE_ADJUST_PRIORITY = 4;
  PROPOSAL_TYPE_ADD_NEW_STRATEGY = 5;
  PROPOSAL_TYPE_DEPRECATE_STRATEGY = 6;
}

enum ProposalStatus {
  PROPOSAL_STATUS_UNSPECIFIED = 0;
  PROPOSAL_STATUS_PENDING_REVIEW = 1;
  PROPOSAL_STATUS_APPROVED = 2;
  PROPOSAL_STATUS_REJECTED = 3;
  PROPOSAL_STATUS_APPLIED = 4;
  PROPOSAL_STATUS_WITHDRAWN = 5;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "proposal_id": "h8i9j0k1-l2m3-4567-8901-abcdef012346",
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "type": "PROPOSAL_TYPE_ADD_PRECONDITION",
  "target_entity_id": "etp-plan-template-refactor-auth",
  "modifications": {
    "add_step_before": "plan_step_id_123",
    "new_step": {
      "tool": "check_dependency",
      "parameters": {
        "dependency_name": "oauth2_lib"
      },
      "on_failure": "install_dependency"
    }
  },
  "rationale": "Adding a precondition to ensure OAuth2 library is present before refactoring, based on FailureAnalysisReport e5f6a7b8-c9d0-1234-5678-90abcdef04.",
  "source_report_id": "e5f6a7b8-c9d0-1234-5678-90abcdef04",
  "status": "PROPOSAL_STATUS_PENDING_REVIEW",
  "proposed_by_agent_id": "agent-alpha-1",
  "created_at": "2025-06-26T11:15:00Z"
}
```

### 4.9. `Environment` Data Model

Represents a snapshot of the execution environment at a given point in time. Crucial for reproducing errors and understanding context.

```protobuf
message Environment {
  string env_id = 1; // Unique identifier for the environment snapshot (UUID)
  string os_type = 2; // Operating system type (e.g., "Linux", "macOS", "Windows")
  string os_version = 3; // Operating system version
  map<string, string> dependency_versions = 4; // Key-value pairs of installed dependency versions (e.g., {"python": "3.9.1", "node": "16.14.0"})
  repeated string env_variables = 5; // Relevant environment variables (e.g., PATH, PYTHONPATH)
  string current_working_directory = 6; // Absolute path of the CWD
  google.protobuf.Timestamp captured_at = 7; // Timestamp when the snapshot was taken
  string agent_id = 8; // ID of the agent instance that captured this environment
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "env_id": "i9j0k1l2-m3n4-5678-9012-abcdef012347",
  "os_type": "macOS",
  "os_version": "14.4.1",
  "dependency_versions": {
    "python": "3.10.12",
    "git": "2.39.2"
  },
  "env_variables": [
    "PATH=/usr/local/bin:/usr/bin",
    "HOME=/Users/agent"
  ],
  "current_working_directory": "/Users/agent/projects/my_project",
  "captured_at": "2025-06-26T10:30:00Z",
  "agent_id": "agent-alpha-1"
}
```

### 4.10. `CodeEntity` Data Model

Represents a specific code artifact (file, function, class, variable) within the codebase. This model is primarily managed by the Code Knowledge Graph (CKG) but is referenced by other components.

```protobuf
message CodeEntity {
  string entity_id = 1; // Unique identifier for the code entity (UUID)
  string project_id = 2; // ID of the project this entity belongs to
  CodeEntityType type = 3; // Type of the code entity
  string path = 4; // Absolute path to the file containing the entity
  string name = 5; // Name of the entity (e.g., function name, class name, file name)
  string language = 6; // Programming language (e.g., "python", "typescript")
  string checksum = 7; // Checksum of the file content at the time of indexing
  google.protobuf.Timestamp last_modified = 8; // Last modified timestamp of the file
  google.protobuf.Struct metadata = 9; // Additional metadata (e.g., function signature, class members, docstrings)
}

enum CodeEntityType {
  CODE_ENTITY_TYPE_UNSPECIFIED = 0;
  CODE_ENTITY_TYPE_FILE = 1;
  CODE_ENTITY_TYPE_FUNCTION = 2;
  CODE_ENTITY_TYPE_CLASS = 3;
  CODE_ENTITY_TYPE_VARIABLE = 4;
  CODE_ENTITY_TYPE_METHOD = 5;
}
```

**JSON Example (for REST/Kafka):**

```json
{
  "entity_id": "j0k1l2m3-n4o5-6789-0123-abcdef012348",
  "project_id": "my_project_id",
  "type": "CODE_ENTITY_TYPE_FUNCTION",
  "path": "/Users/agent/projects/my_project/src/auth.py",
  "name": "authenticate_user",
  "language": "python",
  "checksum": "a1b2c3d4e5f67890abcdef1234567890",
  "last_modified": "2025-06-25T15:00:00Z",
  "metadata": {
    "signature": "def authenticate_user(username: str, password: str) -> bool",
    "docstring": "Authenticates a user against the database."
  }
}
```

## 5. Service Endpoints and Methods

This section details the specific API endpoints and methods exposed by each core component. All gRPC services will be defined using Protocol Buffers, and REST endpoints will follow standard HTTP methods.

### 5.1. Explicit Task Planning (ETP) Service

**Purpose:** Manages the lifecycle of tasks, generates and refines execution plans, and orchestrates the overall agent workflow.

**Protocol:** Primarily gRPC for internal communication, REST for external task submission.

```protobuf
service ExplicitTaskPlanningService {
  // Submits a new task to the ETP system.
  rpc SubmitTask (SubmitTaskRequest) returns (SubmitTaskResponse);

  // Retrieves the current status and details of a task.
  rpc GetTaskStatus (GetTaskStatusRequest) returns (GetTaskStatusResponse);

  // Cancels an ongoing task.
  rpc CancelTask (CancelTaskRequest) returns (CancelTaskResponse);

  // Streams real-time updates for a given task.
  rpc StreamTaskUpdates (StreamTaskUpdatesRequest) returns (stream TaskUpdate);

  // Proposes a plan modification to the ETP system (from FLL/APR).
  rpc ProposePlanModification (ProposePlanModificationRequest) returns (ProposePlanModificationResponse);

  // Retrieves a specific plan template or strategy.
  rpc GetPlanTemplate (GetPlanTemplateRequest) returns (GetPlanTemplateResponse);

  // Updates a plan template or strategy (after HITL approval).
  rpc UpdatePlanTemplate (UpdatePlanTemplateRequest) returns (UpdatePlanTemplateResponse);
}

message SubmitTaskRequest {
  Task task = 1;
}

message SubmitTaskResponse {
  string task_id = 1;
  bool success = 2;
  string message = 3;
}

message GetTaskStatusRequest {
  string task_id = 1;
}

message GetTaskStatusResponse {
  Task task = 1;
}

message CancelTaskRequest {
  string task_id = 1;
}

message CancelTaskResponse {
  string task_id = 1;
  bool success = 2;
  string message = 3;
}

message TaskUpdate {
  string task_id = 1;
  TaskStatus new_status = 2;
  string message = 3;
  google.protobuf.Timestamp timestamp = 4;
  google.protobuf.Struct details = 5; // Additional details about the update
}

message ProposePlanModificationRequest {
  PlanModificationProposal proposal = 1;
}

message ProposePlanModificationResponse {
  string proposal_id = 1;
  bool success = 2;
  string message = 3;
}

message GetPlanTemplateRequest {
  string template_id = 1; // ID of the plan template or strategy
}

message GetPlanTemplateResponse {
  google.protobuf.Struct template_data = 1; // The plan template or strategy data
}

message UpdatePlanTemplateRequest {
  string template_id = 1;
  google.protobuf.Struct updated_template_data = 2;
}

message UpdatePlanTemplateResponse {
  string template_id = 1;
  bool success = 2;
  string message = 3;
}
```

**REST Endpoints (Example for external interaction):**

*   `POST /api/v1/tasks`
    *   **Request Body:** `Task` (JSON)
    *   **Response:** `SubmitTaskResponse` (JSON)
*   `GET /api/v1/tasks/{task_id}`
    *   **Response:** `Task` (JSON)
*   `POST /api/v1/tasks/{task_id}/cancel`
    *   **Response:** `CancelTaskResponse` (JSON)

### 5.2. Code Knowledge Graph (CKG) Service

**Purpose:** Provides a structured, queryable representation of the codebase, including code entities, their relationships, and associated metadata. Serves as the central source of truth for code-related knowledge.

**Protocol:** Primarily gRPC for internal communication.

```protobuf
service CodeKnowledgeGraphService {
  // Indexes new code entities or updates existing ones.
  rpc IndexCodeEntities (IndexCodeEntitiesRequest) returns (IndexCodeEntitiesResponse);

  // Retrieves details of specific code entities.
  rpc GetCodeEntity (GetCodeEntityRequest) returns (GetCodeEntityResponse);

  // Queries the CKG using a graph query language (e.g., Cypher, Gremlin).
  rpc QueryGraph (QueryGraphRequest) returns (QueryGraphResponse);

  // Retrieves related code entities based on defined relationships.
  rpc GetRelatedEntities (GetRelatedEntitiesRequest) returns (GetRelatedEntitiesResponse);

  // Updates metadata for a specific code entity.
  rpc UpdateCodeEntityMetadata (UpdateCodeEntityMetadataRequest) returns (UpdateCodeEntityMetadataResponse);
}

message IndexCodeEntitiesRequest {
  repeated CodeEntity entities = 1;
}

message IndexCodeEntitiesResponse {
  bool success = 1;
  string message = 2;
  repeated string indexed_entity_ids = 3;
}

message GetCodeEntityRequest {
  string entity_id = 1;
}

message GetCodeEntityResponse {
  CodeEntity entity = 1;
}

message QueryGraphRequest {
  string query_language = 1; // e.g., "cypher", "gremlin"
  string query_string = 2;
}

message QueryGraphResponse {
  google.protobuf.Struct results = 1; // JSON representation of query results
}

message GetRelatedEntitiesRequest {
  string entity_id = 1;
  string relationship_type = 2; // e.g., "CALLS", "DEFINES", "DEPENDS_ON"
  int32 depth = 3; // Depth of traversal
}

message GetRelatedEntitiesResponse {
  repeated CodeEntity related_entities = 1;
}

message UpdateCodeEntityMetadataRequest {
  string entity_id = 1;
  google.protobuf.Struct metadata_updates = 2; // Partial metadata updates
}

message UpdateCodeEntityMetadataResponse {
  bool success = 1;
  string message = 2;
}
```
