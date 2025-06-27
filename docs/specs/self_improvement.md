# Self-Improvement System Specification

## 1. Introduction

This document outlines the architecture for the Self-Improvement system, the third and final pillar of the ocode agent's advanced intelligence architecture, complementing the Code Knowledge Graph (CKG) and Explicit Task Planning (ETP) systems. The Self-Improvement system is designed to enable the agent to learn from its operational experience, dynamically adapt its behavior, recover from errors, and extend its own capabilities by generating new tools.

The primary goal is to create a virtuous cycle: the agent executes tasks, observes the outcomes, learns from successes and failures, and uses that knowledge to improve its future performance. This system will transform the ocode agent from a static, tool-executing entity into a dynamic, evolving, and increasingly effective software engineering partner.

## 2. Core Principles

The design and implementation of the Self-Improvement system will be guided by the following principles:

*   **Safety First:** Self-modification, especially tool generation, carries inherent risks. The system will operate with strict safety protocols, including sandboxed execution environments (e.g., Docker containers, isolated Python environments), human-in-the-loop (HITL) verification for critical actions (e.g., new tool deployment, significant plan modifications), and gradual capability rollout. All generated code will undergo static analysis and linting before execution.
*   **Incremental Learning:** The agent's improvement will be gradual and continuous. Learning will be based on a continuous stream of feedback from real-world tasks, rather than periodic, offline training sessions. This implies a streaming data processing architecture for performance metrics and feedback.
*   **Measurable Improvement:** All adaptations and new tools must be evaluated against clear, quantifiable performance metrics. The system will track efficiency (e.g., task completion time, resource consumption), success rates (e.g., pass/fail of test suites, successful deployment), and resource utilization (e.g., CPU, memory, API calls, token usage) to ensure that changes are genuinely beneficial. A/B testing or multi-armed bandit strategies may be employed for evaluating alternative strategies.
*   **Glass Box Architecture:** The agent's learning processes and decision-making must be transparent and interpretable. The system will maintain detailed, queryable logs of its analyses, the hypotheses it generates, and the rationale for its adaptations. This includes provenance tracking for all generated tools and modified plans.

## 3. System Architecture

The Self-Improvement system consists of four major components that operate in a continuous feedback loop, interacting with the ETP and CKG systems.

```mermaid
graph TD
    A[Task Execution] --> B{Performance Monitoring & Analytics};
    B --> C{Feedback & Learning Loop};
    C --> D{Tool Generation & Augmentation};
    C --> E{Plan Refinement & Optimization};
    D --> F[Knowledge Base Integration];
    E --> F;
    F --> G[Updated Agent Capabilities];
    G --> A;
    C -- Queries --> H[Code Knowledge Graph (CKG)];
    C -- Updates --> H;
    E -- Updates --> I[Explicit Task Planning (ETP)];
    D -- Integrates with --> I;
```

### 3.1. Performance Monitoring & Analytics (PMA)

This component is responsible for the comprehensive capture and initial processing of operational telemetry.

*   **Action-Outcome Logging:**
    *   **Data Schema:** Each logged event will adhere to a structured schema, including:
        *   `timestamp`: UTC timestamp of the event.
        *   `task_id`: Unique identifier for the current task.
        *   `agent_id`: Identifier for the agent instance.
        *   `action_type`: (e.g., `tool_call`, `plan_step_execution`, `llm_inference`).
        *   `tool_name` (if `tool_call`): Name of the tool invoked.
        *   `tool_parameters` (if `tool_call`): JSON representation of input parameters.
        *   `tool_output` (if `tool_call`): JSON representation of tool's stdout, stderr, exit code.
        *   `status`: (e.g., `success`, `failure`, `timeout`, `interrupted`).
        *   `error_details` (if `failure`): Structured error message, stack trace, error code.
        *   `resource_metrics`: (e.g., `cpu_usage_percent`, `memory_usage_mb`, `token_count_in`, `token_count_out`, `api_call_latency_ms`).
        *   `context_snapshot`: A lightweight snapshot of relevant environmental context (e.g., current working directory, active files, relevant CKG entities).
    *   **Mechanism:** Events will be streamed to a persistent, queryable data store (e.g., a time-series database, Kafka topic + data lake).
*   **Success/Failure Tracking:**
    *   **Correlation Engine:** A module that correlates sequences of `action_outcome` logs with higher-level task outcomes. Task outcomes are determined by:
        *   **Automated Verification:** Parsing output from test runners (e.g., `pytest`, `npm test`), linters (e.g., `flake8`, `eslint`), type checkers (e.g., `mypy`, `tsc`), or build systems.
        *   **User Feedback:** Explicit signals from the user (e.g., "This task was successful," "This fix didn't work").
    *   **Metrics Calculation:** Aggregation of raw logs into key performance indicators (KPIs) such as:
        *   Task success rate.
        *   Tool-specific success rates.
        *   Average token usage per task/tool.
        *   Common error types and their frequencies.

### 3.2. Feedback & Learning Loop (FLL)

This is the analytical core, transforming raw telemetry into actionable insights and hypotheses.

*   **Automated Error Analysis (AEA):**
    *   **Input:** `task_id`, `failure_event` (from PMA), `action_sequence` (preceding the failure).
    *   **Process:**
        1.  **Pattern Matching:** Identify known error signatures (e.g., `FileNotFoundError`, `ModuleNotFoundError`, `SyntaxError`, specific tool error codes).
        2.  **Contextual Querying (CKG):** For a given error, query the CKG to retrieve relevant code entities (e.g., file dependencies, function definitions, class hierarchies) and their associated metadata (e.g., last modified, author, known issues).
        3.  **Hypothesis Generation (LLM-assisted):** An LLM, guided by a specific prompt and the collected context (error details, action sequence, CKG data), generates a "failure hypothesis." This hypothesis includes:
            *   `root_cause`: (e.g., "missing dependency," "incorrect file path," "API rate limit exceeded").
            *   `culprit_action`: The specific tool call or plan step most likely responsible.
            *   `proposed_remediation_strategy`: (e.g., "add `pip install X` to pre-requisites," "correct path in `config.json`," "implement retry logic with backoff").
            *   `confidence_score`: A numerical score indicating the LLM's confidence in the hypothesis.
    *   **Output:** Structured `FailureAnalysisReport` objects.
*   **Success Pattern Identification (SPI):**
    *   **Input:** `task_id`, `success_event` (from PMA), `action_sequence` (leading to success).
    *   **Process:**
        1.  **Sequence Mining:** Apply algorithms (e.g., PrefixSpan, GSP) to identify frequently occurring, successful sequences of tool calls and plan steps across multiple tasks.
        2.  **Generalization (LLM-assisted):** An LLM generalizes these specific successful sequences into reusable "proven strategies" or "idiomatic patterns." This involves parameterizing the sequence and identifying the conditions under which it is applicable.
        3.  **Efficiency Analysis:** Compare different successful strategies for the same problem class based on resource metrics (time, tokens, etc.) to identify optimal paths.
    *   **Output:** `ProvenStrategy` objects, including `template_plan_fragment`, `applicability_conditions`, `average_performance_metrics`.
*   **Plan Refinement & Optimization (PRO):**
    *   **Input:** `FailureAnalysisReport` (from AEA), `ProvenStrategy` (from SPI).
    *   **Process:**
        1.  **ETP Integration:** Directly interfaces with the ETP system's plan generation module.
        2.  **Failure-driven Refinement:** For each `FailureAnalysisReport`, the PRO module proposes modifications to existing ETP plan templates or generates new error-handling sub-plans. This could involve:
            *   Adding `pre-conditions` to plan steps.
            *   Inserting `retry_mechanisms` or `fallback_strategies`.
            *   Modifying `tool_parameter_generation` logic.
            *   Updating `expected_outputs` for validation.
        3.  **Success-driven Optimization:** Incorporate `ProvenStrategy` objects into the ETP system as preferred plan fragments or alternative execution paths. This aims to:
            *   Replace inefficient sequences with optimized ones.
            *   Introduce new, highly effective patterns into the planning vocabulary.
            *   Prioritize certain tool choices based on empirical success rates.
    *   **Output:** `PlanModificationProposal` objects, which are then submitted to the ETP system for integration (potentially after HITL review).

### 3.3. Tool Generation & Augmentation (TGA)

This component gives the agent the ability to extend its own capabilities by creating new tools.

*   **Opportunity Identification:**
    *   **Heuristics:**
        *   Frequent `run_shell_command` calls with similar patterns (e.g., `grep | awk | sed` pipelines).
        *   Recurring sequences of existing tool calls that could be encapsulated into a single, higher-level abstraction.
        *   Identified gaps in current tool capabilities based on `FailureAnalysisReport` (e.g., "no tool for parsing XML").
    *   **User Request:** Explicit user requests for a new tool.
*   **Tool Scaffolding (LLM-driven Code Generation):**
    *   **Input:** `ToolOpportunity` (from identification), `ToolSpecification` (desired functionality, input/output).
    *   **Process:** An LLM generates the source code for a new tool. This involves:
        1.  **Function Signature Definition:** Based on the `ToolSpecification`, define the tool's name, parameters (with types and descriptions), and return type.
        2.  **Implementation Logic:** Generate Python code (or other suitable language) for the tool's functionality. This might involve:
            *   Wrapping existing shell commands.
            *   Composing multiple existing tools.
            *   Implementing new logic from scratch (e.g., a custom parser).
        3.  **Docstring/Documentation Generation:** Generate comprehensive docstrings and usage examples for the new tool, adhering to project conventions.
        4.  **Test Case Generation:** Generate a suite of unit tests for the new tool, covering edge cases and expected behavior.
    *   **Output:** `ProposedTool` object, containing `source_code`, `test_code`, `documentation`.
*   **Tool Integration & Validation:**
    *   **Sandboxed Execution Environment:** New tools are deployed and executed within an isolated, secure environment (e.g., a dedicated Docker container or a `chroot` jail). This prevents malicious or buggy code from affecting the main agent or host system.
    *   **Automated Testing:** The generated `test_code` is executed against the `source_code` within the sandbox.
    *   **Static Analysis & Linting:** The generated `source_code` is subjected to static analysis (e.g., `mypy`, `pylint`, `bandit`) to check for type errors, style violations, and potential security vulnerabilities.
    *   **Performance Benchmarking:** Basic benchmarks are run to assess the tool's performance characteristics (e.g., execution time, resource consumption).
    *   **HITL Review:** For critical tools or those with low confidence scores from automated validation, a `ToolReviewRequest` is generated for human approval. This includes the tool's code, tests, and a summary of its functionality and validation results.
    *   **Deployment:** Upon successful validation and approval, the tool is formally added to the agent's available toolset, registered with the tool dispatcher, and its metadata is updated in the CKG.

### 3.4. Knowledge Base Integration (KBI)

The insights and capabilities generated by the Self-Improvement system must be persisted and integrated into the agent's long-term memory.

*   **Updating the Code Knowledge Graph (CKG):**
    *   **Learned Relationships:** `FailureAnalysisReport` and `ProvenStrategy` objects are transformed into new nodes and edges within the CKG. Examples:
        *   `ErrorNode` linked to `CodeEntityNode` with `CAUSES_FAILURE` edge.
        *   `ToolSequenceNode` linked to `ProblemTypeNode` with `SOLVES_EFFICIENTLY` edge.
        *   `PreconditionNode` linked to `PlanStepNode` with `REQUIRED_FOR` edge.
    *   **Tool Metadata:** Newly generated tools are added to the CKG as `ToolNode` entities, including their `signature`, `description`, `usage_examples`, `performance_metrics`, and `provenance` (e.g., "generated by Self-Improvement system on YYYY-MM-DD").
*   **Human-in-the-Loop (HITL) Review Queue:**
    *   **Mechanism:** A dedicated UI or notification system presents `PlanModificationProposal` and `ToolReviewRequest` objects to a human operator.
    *   **Content:** Each review item includes:
        *   A clear description of the proposed change.
        *   The rationale (e.g., "This plan modification addresses frequent `FileNotFoundError` when compiling module X").
        *   Diffs of code or plan changes.
        *   Validation results (for tools).
        *   Option to `Approve`, `Reject`, or `Request Clarification`.
    *   **Feedback Loop:** Human decisions are logged and fed back into the FLL to refine the agent's proposal generation logic.

## 4. Synergy with Existing Systems

*   **Explicit Task Planning (ETP):** The Self-Improvement system acts as the continuous improvement engine for the ETP. It provides empirical data (from PMA) and refined strategies (from FLL) to optimize plan generation, error handling, and tool selection within the ETP. The TGA component directly expands the ETP's available action space.
*   **Code Knowledge Graph (CKG):** The CKG serves as the foundational context for the FLL's analytical capabilities (e.g., AEA's ability to diagnose errors based on code structure). In turn, the Self-Improvement system enriches the CKG with dynamic, experiential knowledge (e.g., observed failure modes, empirically validated successful patterns) that cannot be derived from static code analysis alone. This creates a living, evolving knowledge base.

## 5. High-Level Implementation Roadmap

1.  **Phase 1 (Q3 2025): Foundational Telemetry & Basic Error Analysis:**
    *   Implement the `Action-Outcome Logging` and `Success/Failure Tracking` within PMA.
    *   Develop initial `Automated Error Analysis` module for common, easily identifiable errors (e.g., `ModuleNotFoundError`, `FileNotFoundError`) using rule-based pattern matching.
    *   Establish the data persistence layer for telemetry.
2.  **Phase 2 (Q4 2025): LLM-assisted Hypothesis Generation & Basic Plan Refinement:**
    *   Integrate LLMs into AEA for more sophisticated `Failure Hypothesis Generation`.
    *   Implement `Plan Refinement & Optimization` for simple `pre-condition` additions and `retry_mechanisms` based on AEA outputs.
    *   Introduce the `HITL Review Queue` for plan modification proposals.
3.  **Phase 3 (Q1 2026): Sandboxed Tool Generation & Validation:**
    *   Develop the `Tool Scaffolding` module (LLM-driven code generation).
    *   Implement the `Sandboxed Execution Environment` for new tools.
    *   Integrate `Automated Testing`, `Static Analysis`, and `Performance Benchmarking` for tool validation.
    *   Introduce the `HITL Review Queue` for new tool proposals.
4.  **Phase 4 (Q2 2026): Advanced Learning & Full Integration:**
    *   Implement `Success Pattern Identification` using sequence mining and LLM generalization.
    *   Deepen the integration of `ProvenStrategy` objects into ETP.
    *   Enhance CKG integration for dynamic knowledge updates.
    *   Explore A/B testing for plan and tool evaluation.
    *   Gradually increase agent autonomy for low-risk changes based on accumulated confidence and HITL feedback.

## 6. Conclusion

The Self-Improvement system represents a paradigm shift in the capabilities of the ocode agent. By enabling the agent to learn from experience, it introduces a powerful feedback loop that will drive continuous and accelerating improvement in performance, efficiency, and autonomy. This system, in conjunction with the Code Knowledge Graph and Explicit Task Planning, will cement ocode's position as a leader in the field of AI-powered software engineering.