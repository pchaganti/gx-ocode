# Self-Improvement: Knowledge Graph Primer

## 1. Introduction to Knowledge Graphs in Self-Improvement

This primer delves into the technical architecture and data model of a Knowledge Graph (KG) specifically designed to underpin the Self-Improvement system of the ocode agent. While the broader Self-Improvement specification outlines *what* the system achieves (learning from experience, error recovery, tool generation), this document focuses on *how* a structured knowledge representation enables these advanced capabilities.

The core idea is to move beyond reactive, heuristic-based responses to errors and opportunities. By representing operational experiences, tool capabilities, environmental contexts, and problem-solution patterns as interconnected entities in a graph, the agent gains the ability to reason, generalize, and proactively adapt its behavior.

## 2. Core Principles of the Self-Improvement Knowledge Graph

*   **Causality & Context:** The KG must explicitly model the causal links between actions, environmental states, and outcomes (especially errors). It captures the full context of an execution attempt, not just the immediate failure.
*   **Generalization & Abstraction:** Individual experiences are generalized into canonical patterns (e.g., `ErrorPattern`, `RecoveryStrategy`) to enable learning across similar situations.
*   **Actionability:** Knowledge stored in the KG must be directly actionable, informing the Explicit Task Planning (ETP) system and guiding tool generation.
*   **Evolvability:** The KG schema and its instances must be capable of evolving as the agent learns new concepts, tools, and strategies.
*   **Transparency & Debuggability:** The graph structure provides a transparent, auditable trail of the agent's learning process, crucial for human oversight and debugging.

## 3. Knowledge Graph Data Model: Entities (Nodes) and Relationships (Edges)

### 3.1. Entities (Nodes)

Nodes represent the fundamental concepts and objects within the Self-Improvement domain. Each node has a unique identifier and a set of properties.

| Node Label | Description | Key Properties (Attributes) |
| :--- | :--- | :--- |
| **`Agent`** | Represents the AI agent instance. | `agent_id: UUID`, `version: string`, `model_name: string`, `capabilities: [string]` (e.g., `['code_generation', 'refactoring']`) |
| **`Tool`** | An external utility (CLI, API, library function) the agent can invoke. | `tool_id: UUID`, `name: string` (e.g., `git`, `curl`, `mypy`), `version: string`, `type: enum` (CLI, API, Library, Internal), `signature: json` (API spec/CLI args), `description: string` |
| **`Task`** | A high-level objective or user request. | `task_id: UUID`, `user_prompt: string`, `status: enum` (Pending, InProgress, Success, Failed, Cancelled), `creation_timestamp: datetime`, `completion_timestamp: datetime` (if applicable) |
| **`ExecutionAttempt`** | A specific invocation of a `Tool` as part of a `Task`. This is the granular unit of observation. | `attempt_id: UUID`, `timestamp: datetime`, `tool_name: string`, `input_parameters: json` (actual values passed), `raw_command: string` (for CLI tools), `outcome: enum` (Success, Failure), `duration_ms: integer`, `token_usage: json` (in/out), `api_cost: float` |
| **`Error`** | A specific, observed error event resulting from a failed `ExecutionAttempt`. | `error_id: UUID`, `error_code: string` (e.g., `128` for git, `404` for HTTP), `error_message: string`, `stdout: string`, `stderr: string`, `is_transient: boolean` (e.g., network glitch vs. syntax error) |
| **`ErrorPattern`** | A generalized, canonical representation of a class of errors. This is where abstraction happens. | `pattern_id: UUID`, `name: string` (e.g., `GitAuthenticationFailure`, `PythonModuleNotFound`), `description: string`, `canonical_regex: string` (regex to match `stderr`/`error_message`), `common_causes: [string]` |
| **`RecoveryStrategy`** | A specific, actionable plan or sequence of steps to resolve an `ErrorPattern`. | `strategy_id: UUID`, `description: string`, `actionable_steps: [json]` (ordered list of tool calls/plan fragments), `confidence_score: float` (0.0-1.0), `success_rate: float` (0.0-1.0), `last_updated: datetime` |
| **`Environment`** | The state of the execution environment. | `env_id: UUID`, `os_type: string`, `os_version: string`, `dependency_versions: json` (e.g., `{'python': '3.9.1', 'node': '16.14.0'}`), `env_variables: [string]` (relevant subset), `network_status: enum` (Online, Offline, Restricted) |
| **`CodeEntity`** | Represents a specific code artifact (file, function, class, variable). This links to the main Code Knowledge Graph. | `entity_id: UUID`, `type: enum` (File, Function, Class, Variable), `path: string`, `name: string`, `language: string`, `checksum: string` |
| **`PlanFragment`** | Reusable, parameterized sequences of actions or sub-plans. | `fragment_id: UUID`, `name: string`, `description: string`, `steps: [json]` (sequence of tool calls/sub-fragments), `parameters: json` (schema for parameters) |

### 3.2. Relationships (Edges)

Edges define the connections and semantic relationships between nodes, forming the graph structure that enables reasoning.

| Edge Label | Start Node | End Node | Description | Key Properties (Attributes) |
| :--- | :--- | :--- | :--- | :--- |
| **`PERFORMS`** | `Agent` | `Task` | An agent is assigned or initiates a task. | `timestamp: datetime` |
| **`REQUIRES`** | `Task` | `Tool` | A task necessitates the use of a specific tool. | `reason: string` |
| **`INITIATES`** | `Agent` | `ExecutionAttempt` | The agent makes a concrete attempt to execute a tool. | `timestamp: datetime` |
| **`PART_OF`** | `ExecutionAttempt` | `Task` | Links a specific attempt back to the overall task goal. | `order: integer` |
| **`USES`** | `ExecutionAttempt` | `Tool` | Specifies which tool was invoked in this attempt. | `version_used: string` |
| **`OCCURRED_IN`** | `ExecutionAttempt` | `Environment` | Captures the system state during execution. | `snapshot_time: datetime` |
| **`RESULTED_IN`** | `ExecutionAttempt` | `Error` | Connects a failed attempt to the specific error it produced. | `severity: enum` (Low, Medium, High, Critical) |
| **`IS_INSTANCE_OF`** | `Error` | `ErrorPattern` | Generalizes a specific error to a known class of problems. | `match_confidence: float` |
| **`MITIGATED_BY`** | `ErrorPattern` | `RecoveryStrategy` | This strategy is known to resolve this error pattern. | `effectiveness: float` (historical success rate) |
| **`APPLIES_TO`** | `RecoveryStrategy` | `Tool` | Narrows the applicability of a strategy to a specific tool or type. | `condition: string` (e.g., `tool.name == 'git'`) |
| **`LEARNED_FROM`** | `Agent` | `RecoveryStrategy` | The agent incorporates a new or refined strategy into its knowledge. | `learning_event_id: UUID`, `timestamp: datetime` |
| **`SUCCEEDED_WITH`** | `RecoveryStrategy` | `ExecutionAttempt` | Records that applying this strategy led to a successful outcome. | `timestamp: datetime` |
| **`FAILED_WITH`** | `RecoveryStrategy` | `ExecutionAttempt` | Records that a strategy did *not* work. Crucial for negative learning. | `timestamp: datetime` |
| **`MODIFIES`** | `RecoveryStrategy` | `Environment` | A strategy might change the environment (e.g., installing a dependency). | `change_description: string` |
| **`REFERENCES`** | `Error` / `RecoveryStrategy` / `ExecutionAttempt` | `CodeEntity` | Links operational data to specific parts of the codebase. | `context: string` (e.g., `stack_trace_line`, `relevant_function`) |
| **`COMPOSED_OF`** | `PlanFragment` | `Tool` / `PlanFragment` | Defines the hierarchical structure of plans. | `order: integer`, `parameters_mapping: json` |
| **`GENERATED`** | `Agent` | `Tool` / `PlanFragment` | Tracks the provenance of new capabilities. | `timestamp: datetime`, `method: string` (e.g., `LLM_synthesis`, `human_guided`) |

## 4. Knowledge Graph Operations for Self-Improvement

The KG is not merely a static data store; it's a dynamic, queryable system that supports the core functions of self-improvement:

### 4.1. Error Diagnosis and Root Cause Analysis

When an `ExecutionAttempt` `RESULTED_IN` an `Error`:
1.  **Pattern Matching:** The system attempts to match the `Error` (`error_message`, `stderr`, `error_code`) against existing `ErrorPattern` nodes using `canonical_regex` and other properties. This creates an `IS_INSTANCE_OF` edge.
2.  **Contextual Query:** Traverse from the `Error` node through `OCCURRED_IN` to `Environment` and `REFERENCES` to `CodeEntity` nodes to gather all relevant context. This helps disambiguate similar error messages.
3.  **Hypothesis Generation:** If a direct `ErrorPattern` match is found, retrieve its `common_causes`. If not, an LLM is prompted with the `Error` details, `ExecutionAttempt` context, and `Environment` snapshot to infer a `root_cause` and propose a new `ErrorPattern`.

### 4.2. Strategy Retrieval and Selection

Once an `ErrorPattern` is identified:
1.  **Candidate Retrieval:** Query the KG for `RecoveryStrategy` nodes `MITIGATED_BY` the `ErrorPattern`.
2.  **Contextual Filtering:** Filter candidate strategies based on the current `Environment` and the `Tool` involved (using `APPLIES_TO` edges and their `condition` properties).
3.  **Prioritization:** Rank remaining strategies by `confidence_score` and `success_rate` (properties on the `RecoveryStrategy` node, dynamically updated).
4.  **Execution:** The selected `RecoveryStrategy`'s `actionable_steps` (which are `PlanFragment`s or direct `Tool` invocations) are passed to the ETP system for execution.

### 4.3. Learning from Success and Failure

After a `RecoveryStrategy` is applied and the subsequent `ExecutionAttempt` completes:
1.  **Feedback Loop:** If the attempt succeeds, a `SUCCEEDED_WITH` edge is created from the `RecoveryStrategy` to the `ExecutionAttempt`. If it fails, a `FAILED_WITH` edge is created.
2.  **Metric Update:** The `confidence_score` and `success_rate` properties of the `RecoveryStrategy` node are updated using a learning algorithm (e.g., Bayesian updating, simple moving average). Strategies with consistently low success rates can be flagged for deprecation or re-evaluation.
3.  **Novel Strategy Induction:** If a novel solution is found (e.g., through human intervention or LLM-driven problem-solving without a pre-existing `RecoveryStrategy`), a new `RecoveryStrategy` node is created, linked to the relevant `ErrorPattern`, and its `actionable_steps` are populated.

### 4.4. Tool Generation and Integration

When an opportunity for a new tool is identified (e.g., recurring `run_shell_command` patterns):
1.  **Pattern Extraction:** Analyze sequences of `ExecutionAttempt` nodes to identify frequently co-occurring `Tool` invocations or `raw_command` patterns.
2.  **Tool Specification Generation:** An LLM, guided by the extracted pattern, generates a formal `ToolSpecification` (name, parameters, description, expected output).
3.  **Code Generation:** The LLM generates `source_code` and `test_code` for the new `Tool` based on the `ToolSpecification`.
4.  **Validation & Integration:** After sandboxed testing and human review, a new `Tool` node is created in the KG, linked via a `GENERATED` edge from the `Agent`. Its `signature` and `description` are added, making it discoverable by the ETP system.

## 5. Synergy with Code Knowledge Graph (CKG)

The Self-Improvement KG is deeply intertwined with the main Code Knowledge Graph (CKG):

*   **Contextual Enrichment:** The Self-Improvement KG `REFERENCES` `CodeEntity` nodes in the CKG. This allows error analysis to directly pinpoint problematic code sections, and for tool generation to understand the context of code modifications.
*   **Schema Extension:** The CKG can be extended to include meta-knowledge about code quality, common anti-patterns, or areas prone to errors, which can then be referenced by `ErrorPattern` nodes in the Self-Improvement KG.
*   **Tool Discovery:** The ETP system, informed by the Self-Improvement KG's `ProvenStrategy` and newly `GENERATED` `Tool` nodes, can make more intelligent decisions about which tools to use and how to compose them.

## 6. Conclusion

The Self-Improvement Knowledge Graph is the central nervous system of the ocode agent's learning capabilities. By providing a structured, interconnected representation of operational experiences, errors, solutions, and tool capabilities, it transforms raw data into actionable intelligence. This enables the agent to not only recover from failures but to proactively improve its planning, generate new tools, and continuously evolve its understanding of the software engineering domain. This sophisticated knowledge representation is critical for achieving true self-improvement and autonomy in complex software development tasks.
