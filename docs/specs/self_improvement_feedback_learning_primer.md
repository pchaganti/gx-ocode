# Self-Improvement: Feedback & Learning Loop Primer

## 1. Introduction: The Engine of Self-Improvement

This primer provides a detailed technical exposition of the **Feedback & Learning Loop (FLL)**, the analytical and cognitive core of the ocode agent's Self-Improvement system. While the Performance Monitoring & Analytics (PMA) component gathers raw operational data and the Tool Generation & Augmentation (TGA) component extends capabilities, it is the FLL that transforms raw experience into actionable intelligence, enabling the agent to truly learn and adapt.

The FLL is responsible for:

*   **Diagnosing Failures:** Understanding *why* an action or plan failed, moving beyond superficial error messages to identify root causes.
*   **Identifying Successes:** Recognizing and generalizing efficient and effective patterns of behavior that lead to successful task completion.
*   **Refining Strategies:** Translating learned insights into concrete modifications for the Explicit Task Planning (ETP) system and informing the TGA component.
*   **Continuous Adaptation:** Ensuring the agent's performance continuously improves over time by integrating new knowledge into its operational models.

## 2. Components of the Feedback & Learning Loop

The FLL operates through the synergistic interaction of three primary sub-components:

*   **Automated Error Analysis (AEA):** Focuses on diagnosing failures and inferring root causes.
*   **Success Pattern Identification (SPI):** Identifies and generalizes effective sequences of actions.
*   **Adaptive Plan Refinement (APR):** Integrates insights from AEA and SPI to modify and optimize the agent's planning strategies.

## 3.1. Automated Error Analysis (AEA)

AEA is activated when an `ExecutionAttempt` results in a `Failure` outcome. Its primary goal is to move beyond superficial error messages to identify the underlying `root_cause` and generate a structured `FailureAnalysisReport`.

### 3.1.1. Input Data & Preprocessing

AEA consumes the following data from the PMA component:

*   **`ExecutionAttempt` Log:** The full log of the failed attempt, including `tool_name`, `input_parameters`, `raw_command`, `stdout`, `stderr`, `error_details` (e.g., stack trace, exit code), and `context_snapshot`.
*   **Preceding `ActionSequence`:** The sequence of `ExecutionAttempt`s that led up to the failure, providing temporal context.
*   **`Environment` Snapshot:** Detailed state of the environment (`os_type`, `dependency_versions`, `env_variables`) at the time of failure.

Preprocessing involves parsing `stderr` and `error_details` to extract key phrases, error codes, and stack trace information. This often includes normalizing error messages to canonical forms.

### 3.1.2. Error Pattern Matching & Classification

*   **Rule-Based Pattern Matching:** A library of known `ErrorPattern`s (stored in the Self-Improvement KG) is used to perform initial classification. Each `ErrorPattern` has associated `canonical_regex` patterns that match against preprocessed error messages. This provides a fast, deterministic classification for common errors (e.g., `FileNotFoundError`, `PermissionDenied`, `ModuleNotFoundError`).
*   **Machine Learning Classification:** For more complex or novel errors, a supervised machine learning model (e.g., a text classifier trained on historical `Error` data and their human-labeled `ErrorPattern`s) can classify the error into a known category or flag it as `UNKNOWN`.

### 3.1.3. Contextual Querying (Leveraging the Code Knowledge Graph)

Once an `ErrorPattern` is identified (or a novel error is being analyzed), AEA queries the CKG to enrich the context:

*   **Code Entity Lookup:** If the error message references specific files, functions, or variables, AEA retrieves the corresponding `CodeEntity` nodes from the CKG. This provides metadata like file paths, language, dependencies, and historical changes.
*   **Dependency Analysis:** For `ModuleNotFoundError` or similar dependency-related errors, AEA queries the CKG to understand the project's declared dependencies versus the `Environment`'s installed dependencies.
*   **Historical Context:** AEA can query the CKG for past `Error` nodes linked to the same `CodeEntity` or `Tool` to identify recurring issues or recent changes that might have introduced the error.

### 3.1.4. Hypothesis Generation (LLM-Assisted Reasoning)

This is the most critical step, where AEA synthesizes a `FailureAnalysisReport`:

*   **Prompt Construction:** An LLM is prompted with a comprehensive context, including:
    *   The raw `Error` details (`stderr`, stack trace).
    *   The classified `ErrorPattern` (if matched).
    *   The `ExecutionAttempt` details (tool, parameters, command).
    *   The `ActionSequence` leading to the failure.
    *   Relevant `CodeEntity` and `Environment` data from the CKG.
    *   A clear instruction to identify the `root_cause`, `culprit_action`, and propose a `remediation_strategy`.
*   **Root Cause Inference:** The LLM analyzes the provided context to infer the most probable `root_cause` (e.g., "incorrect path configuration," "missing build step," "API rate limit"). It leverages its vast training data to reason about common programming errors and system behaviors.
*   **Remediation Proposal:** Based on the inferred root cause, the LLM proposes a `remediation_strategy`. This strategy is a high-level description of how to fix the problem, which will later be translated into concrete `actionable_steps` by APR.
*   **Confidence Scoring:** The LLM provides a `confidence_score` for its hypothesis, indicating its certainty. This score can be used by downstream components (like APR or HITL) to prioritize interventions.

### 3.1.5. Output: `FailureAnalysisReport`

The output of AEA is a structured `FailureAnalysisReport` object, which is then stored in the Self-Improvement KG and passed to the APR component. Key fields include:

*   `report_id: UUID`
*   `task_id: UUID`
*   `failed_attempt_id: UUID`
*   `error_pattern_id: UUID` (if matched, else `null`)
*   `inferred_root_cause: string`
*   `culprit_action_id: UUID`
*   `proposed_remediation_strategy_description: string`
*   `confidence_score: float`
*   `analysis_timestamp: datetime`
*   `relevant_ckg_entities: [UUID]`