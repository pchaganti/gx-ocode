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

## 3.2. Success Pattern Identification (SPI)

SPI continuously monitors successful `Task` completions and `ExecutionAttempt` sequences to identify efficient, robust, and generalizable patterns of behavior. The goal is to extract `ProvenStrategy` objects that can be reused and optimized by the ETP system.

### 3.2.1. Input Data & Preprocessing

SPI consumes successful `ExecutionAttempt` logs and `Task` completion events from the PMA component. For each successful task, the full `ActionSequence` (ordered list of `ExecutionAttempt`s) is extracted.

Preprocessing involves:

*   **Parameterization:** Replacing specific values in `input_parameters` and `raw_command` with generic placeholders (e.g., file paths, variable names) to enable generalization.
*   **Normalization:** Standardizing tool names and command formats.
*   **Contextual Tagging:** Associating each `ExecutionAttempt` with relevant `CodeEntity` and `ProblemType` nodes from the CKG, providing semantic context.

### 3.2.2. Sequence Mining & Pattern Extraction

*   **Frequent Sequence Mining:** Algorithms like PrefixSpan, GSP (Generalized Sequential Pattern), or SPADE are applied to the preprocessed `ActionSequence` data. These algorithms identify frequently occurring sub-sequences of tool calls and plan steps across a large corpus of successful tasks.
*   **Graph-Based Pattern Matching:** The Self-Improvement KG can be traversed to identify recurring subgraphs of `Tool` and `ExecutionAttempt` nodes that lead to successful outcomes for specific `ProblemType`s.
*   **Performance-Aware Filtering:** Sequences are filtered and ranked based on their associated `resource_metrics` (e.g., lower `duration_ms`, lower `token_usage`, higher `success_rate`) to prioritize efficient patterns.

### 3.2.3. Generalization & Abstraction (LLM-Assisted)

Raw frequent sequences are often too specific. An LLM is used to generalize them into reusable `ProvenStrategy` objects:

*   **Prompt Construction:** The LLM is provided with:
    *   A frequent, high-performing `ActionSequence`.
    *   The `Task` context and `ProblemType` it solved.
    *   Relevant `CodeEntity` and `Environment` data.
    *   Instructions to abstract the sequence into a parameterized `template_plan_fragment`, define its `applicability_conditions`, and provide a concise `description`.
*   **Parameterization:** The LLM identifies variables within the sequence (e.g., file names, directory paths, specific values) and replaces them with generic parameters, defining their types and constraints.
*   **Applicability Conditions:** The LLM infers the conditions under which the `ProvenStrategy` is likely to be successful (e.g., "applicable when a Python virtual environment needs to be activated," "for refactoring a specific type of class"). These conditions are crucial for the ETP system to select the right strategy.
*   **Naming & Description:** The LLM generates a human-readable name and description for the `ProvenStrategy`.

### 3.2.4. Output: `ProvenStrategy`

The output of SPI is a structured `ProvenStrategy` object, which is then stored in the Self-Improvement KG and passed to the APR component. Key fields include:

*   `strategy_id: UUID`
*   `name: string`
*   `description: string`
*   `template_plan_fragment: json` (parameterized sequence of actions/tool calls)
*   `applicability_conditions: json` (rules for when to use this strategy)
*   `average_performance_metrics: json` (e.g., `avg_duration_ms`, `avg_token_usage`)
*   `success_rate: float` (dynamically updated)
*   `last_updated: datetime`
*   `related_problem_types: [UUID]`

## 3.3. Adaptive Plan Refinement (APR)

APR is the component responsible for translating the insights from AEA and SPI into concrete, actionable improvements for the Explicit Task Planning (ETP) system. It ensures that the agent's planning capabilities evolve based on its operational experience.

### 3.3.1. Input Data

APR receives two primary types of input:

*   **`FailureAnalysisReport` (from AEA):** Contains the inferred `root_cause` and `proposed_remediation_strategy_description` for a failed task.
*   **`ProvenStrategy` (from SPI):** Contains generalized, high-performing `template_plan_fragment`s and their `applicability_conditions`.

### 3.3.2. Failure-Driven Plan Modification

When a `FailureAnalysisReport` is received, APR focuses on preventing recurrence:

*   **Pre-condition Injection:** For a `root_cause` like "missing dependency," APR proposes adding a `pre-condition` step to relevant ETP plan templates. This pre-condition would involve checking for the dependency's presence and installing it if missing, *before* attempting the action that previously failed.
*   **Error-Handling Sub-plan Generation:** For common `ErrorPattern`s, APR can generate or modify existing ETP sub-plans to include specific `retry_mechanisms` (e.g., exponential backoff for API rate limits), `fallback_strategies` (e.g., using a different tool if the primary one fails), or `diagnostic_steps` (e.g., running `ping` or `ls` to gather more information before retrying).
*   **Tool Parameter Adjustment:** If the `root_cause` indicates incorrect tool parameter usage, APR can propose modifications to the ETP's logic for generating `tool_parameters` for specific `Tool` invocations.
*   **Negative Examples for LLM Planning:** Failed `ActionSequence`s, especially those with clear `root_cause`s, are fed back to the ETP's LLM-based planning component as negative examples, teaching it to avoid similar pitfalls.

### 3.3.3. Success-Driven Plan Optimization

When a `ProvenStrategy` is received, APR focuses on improving efficiency and effectiveness:

*   **Integration of Proven Strategies:** APR integrates `ProvenStrategy` objects into the ETP system's library of reusable plan fragments. This means:
    *   **Direct Substitution:** If a `ProvenStrategy` is a more efficient alternative to an existing plan fragment, APR proposes replacing the old fragment with the new one.
    *   **New Plan Fragments:** If the `ProvenStrategy` represents a novel, effective way to solve a `ProblemType`, it is added as a new option for the ETP planner.
*   **Prioritization Adjustment:** The `success_rate` and `average_performance_metrics` of `ProvenStrategy` objects are used to adjust the ETP planner's internal scoring or weighting mechanisms. This biases the planner towards selecting empirically validated, high-performing strategies.
*   **Contextual Plan Generation:** The `applicability_conditions` of `ProvenStrategy` objects are crucial. APR ensures the ETP planner understands these conditions, allowing it to select the most appropriate strategy based on the current `Task` and `Environment` context.

### 3.3.4. Output: `PlanModificationProposal`

The output of APR is a `PlanModificationProposal` object, which is then submitted to the Knowledge Base Integration (KBI) component for storage and potential HITL review. Key fields include:

*   `proposal_id: UUID`
*   `type: enum` (AddPrecondition, ModifyErrorHandling, ReplaceFragment, AdjustPriority)
*   `target_plan_template_id: UUID`
*   `modifications: json` (detailed description of changes to the plan structure)
*   `rationale: string` (explaining why this change is proposed, linking to `FailureAnalysisReport` or `ProvenStrategy`)
*   `source_report_id: UUID` (link to AEA report or SPI strategy)
*   `proposed_by_agent_id: UUID`
*   `timestamp: datetime`

## 4. Reinforcement Learning Signals

Beyond explicit error reports and success patterns, the FLL can leverage Reinforcement Learning (RL) principles to provide continuous, fine-grained feedback to the agent's decision-making policies. This is particularly relevant for optimizing sequences of actions where immediate success/failure signals are sparse, but long-term performance is critical.

### 4.1. Defining States, Actions, and Rewards

*   **States (S):** The current context of the agent, encompassing elements from the CKG (e.g., current code state, project structure, dependencies), the `Environment` snapshot, and the current `Task` progress. States are typically high-dimensional and require careful representation (e.g., embeddings, structured features).
*   **Actions (A):** The discrete set of choices the agent can make at any given state. This includes selecting a `Tool` to invoke, choosing a `PlanFragment` to execute, or deciding on a `RecoveryStrategy`.
*   **Rewards (R):** Numerical signals that guide the agent's learning. Rewards can be:
    *   **Sparse Rewards:** A large positive reward upon successful `Task` completion, and a large negative reward upon `Task` failure.
    *   **Dense Rewards:** Smaller, intermediate rewards for progress towards a goal (e.g., passing a test, fixing a linter warning, reducing token usage, decreasing execution time). Penalties for inefficient actions or resource overconsumption.

### 4.2. RL Algorithms for Policy Optimization

*   **Policy Gradient Methods (e.g., PPO, A2C):** These algorithms directly optimize the agent's policy (the mapping from states to actions) to maximize expected cumulative rewards. They are well-suited for complex, high-dimensional state and action spaces.
*   **Q-Learning / Deep Q-Networks (DQN):** For scenarios with more discrete state and action spaces, Q-learning can be used to learn an optimal Q-function, which estimates the maximum expected future rewards for taking a given action in a given state.
*   **Inverse Reinforcement Learning (IRL):** If human demonstrations of optimal behavior are available, IRL can be used to infer the underlying reward function that explains those demonstrations. This can help bootstrap the agent's learning process.

### 4.3. Integration with Explicit Task Planning (ETP)

RL signals primarily influence the ETP system's decision-making process:

*   **Policy-Guided Planning:** The ETP's planning module can be augmented with an RL-trained policy. Instead of relying solely on heuristic-based plan generation or LLM-generated plans, the RL policy can suggest the next best action or `PlanFragment` given the current state.
*   **Adaptive Exploration vs. Exploitation:** RL naturally balances exploration (trying new actions/strategies to discover better ones) and exploitation (using known good strategies). This allows the agent to continuously discover more optimal ways to solve problems.
*   **Dynamic Prioritization:** The learned value function from RL can be used to dynamically adjust the prioritization of `ProvenStrategy` objects or `PlanModificationProposal`s, favoring those that have historically led to higher rewards.

### 4.4. Challenges and Considerations

*   **Reward Engineering:** Designing effective reward functions that accurately reflect desired behavior and avoid unintended consequences is challenging.
*   **State Representation:** Creating a meaningful and compact state representation from the rich, heterogeneous data in the CKG and PMA is crucial for RL algorithm performance.
*   **Exploration Efficiency:** In complex software engineering environments, efficient exploration of the action space is vital to avoid getting stuck in local optima.
*   **Off-Policy Learning:** Leveraging past experiences (even those not generated by the current policy) is important for data efficiency.

## 5. Conclusion

The Feedback & Learning Loop is the intellectual powerhouse of the ocode agent's Self-Improvement system. Through the synergistic operation of Automated Error Analysis, Success Pattern Identification, and Adaptive Plan Refinement, augmented by Reinforcement Learning signals, the FLL enables the agent to continuously learn from its experiences. This deep analytical capability allows the agent to not only recover from failures but to proactively optimize its strategies, leading to increasingly efficient, robust, and autonomous software engineering operations. The FLL transforms raw operational data into a dynamic, evolving intelligence that drives the agent's continuous growth and effectiveness.
