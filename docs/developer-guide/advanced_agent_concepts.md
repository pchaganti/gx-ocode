
# Advanced Agent Concepts: The Path to a Strategic Partner

**Audience:** Core Development & AI Strategy Team

**Purpose:** This document outlines the next horizon of capabilities for `ocode`. The ideas here go beyond simple improvements and represent fundamental architectural shifts to evolve the agent from a tool-executor into a proactive, learning, and strategic software engineering partner. Each concept is a major workstream that will define the future of this project.

---

### 1. From Chain-of-Thought to Explicit Task Planning

**The Vision:** The agent should be able to take a high-level, ambiguous goal (e.g., "Add OAuth2 login") and autonomously generate a detailed, verifiable, and transparent execution plan before writing a single line of code.

**Current State:** The agent uses a reactive, single-step planning process. The LLM's "thought" process is implicit in its choice of the next tool. This is effective for simple commands but brittle for complex, multi-day tasks.

**Advanced Architecture: The Planning & Task Graph Module**

1.  **The Planner Persona:** We will introduce a new, specialized "Planner" persona. When the `Engine` detects a high-level goal, it will first invoke this persona. Its sole job is to decompose the goal into a structured plan.

2.  **The Task Graph:** The output of the Planner will not be prose; it will be a machine-readable **Task Graph**. This is a directed acyclic graph (DAG) where each node is a `CommandTask` (the same object used by the `Orchestrator`) and the edges represent dependencies.

    *   **Example Goal:** `"Refactor the database logic to use a repository pattern."`
    *   **Generated Task Graph (Conceptual):**
        ```
        (A: find_files pattern='*service.py') --> (C: read_file path=...)
                                             |
        (B: find_files pattern='*controller.py') -> (D: read_file path=...)
                                             |
        (C, D) --> (E: write_file path='repository.py' content=...)
                                             |
        (E) --> (F: replace content_in_service.py ...)
                                             |
        (E) --> (G: replace content_in_controller.py ...)
                                             |
        (F, G) --> (H: run_shell_command cmd='pytest')
        ```

3.  **Implementation Steps:**
    *   Create a `PlanningModule` in `ocode_python/core/`. This module will house the logic for invoking the Planner persona and parsing its output into a Task Graph object.
    *   The `Orchestrator` will be enhanced to accept and execute an entire Task Graph, respecting dependencies and leveraging its existing concurrency and retry logic.
    *   **User Interaction:** Before execution, the agent will present the plan to the user for approval. *"I plan to do the following 8 steps... Do you want to proceed?"* This makes the agent's reasoning transparent and keeps the user in control.

**Strategic Impact:** This transforms the agent from a black box into a glass box. It enables it to tackle much larger, more complex tasks reliably and allows for human-in-the-loop validation at the planning stage, not just the execution stage.

---

### 2. From Fixed Tools to a Self-Improving Agent

**The Vision:** The agent should learn from its successes and failures. It should optimize its own workflows and even create new tools for itself to become more efficient over time.

**Current State:** The agent has a fixed set of tools. If a tool fails, the process stops. If it performs a sequence of actions repeatedly, it does so without awareness.

**Advanced Architecture: The Meta-Cognition Loop**

1.  **Automated Error Recovery:**
    *   When the `Orchestrator` encounters a tool failure, it won't just give up. It will pass the `ToolResult` (containing the error) back to the `Engine`.
    *   The `Engine` will enter a "debugging" state, invoking a "Debugger" persona. This LLM call will be given the original goal, the failed command, and the error message.
    *   The Debugger's task is to propose a solution: either correcting the arguments of the failed tool or suggesting an alternative sequence of tools to achieve the same sub-goal.
    *   **Impact:** This makes the agent dramatically more resilient and capable of navigating the imperfections of real-world development environments.

2.  **Automated Tool Generation:**
    *   **The Vision:** This is the holy grail of agentic systems. If the agent frequently chains `find -> grep -> replace` to perform a specific type of refactoring, it should recognize this pattern.
    *   **Implementation:**
        1.  **Log Command History:** The `Orchestrator` will maintain a persistent log of successfully executed command sequences associated with high-level user goals.
        2.  **Pattern Recognition:** A background process will analyze this history to find frequently recurring, multi-step command patterns.
        3.  **The "Toolsmith" Persona:** When a common pattern is identified, the `Engine` will invoke a "Toolsmith" persona. This LLM call will be given the command sequence and asked to synthesize it into a single, reusable Python function (a new tool), including its `ToolDefinition` and argument schema.
        4.  **Dynamic Tool Loading:** The generated tool code will be saved to a `ocode_python/tools/generated/` directory. The `ToolRegistry` will be modified to dynamically discover and load tools from this directory at startup.
        5.  **User Confirmation:** The agent would propose this action to the user: *"I've noticed a pattern in my work. May I create a new `refactor_variable` tool to make this faster in the future?"*

**Strategic Impact:** This closes the loop on agent learning. The agent doesn't just act; it reflects, abstracts, and improves its own capabilities. This is the key to exponential growth in its effectiveness.

---

### 3. From File Content to a Code Knowledge Graph

**The Vision:** The agent's understanding of a codebase should be as deep as an experienced developer's, not just based on keyword matching. It should understand the semantic relationships between different parts of the code.

**Current State:** The `ContextManager` reads file contents and performs some basic symbol extraction. This is a flat, unstructured view of the project.

**Advanced Architecture: The Code Knowledge Graph**

1.  **AST-Based Parsing:** We will create a persistent background process. Whenever a file changes, this process will read the file and parse it into an Abstract Syntax Tree (AST). Python's `ast` module is perfect for this.

2.  **Graph Construction:** From the AST, we will extract entities and their relationships:
    *   **Nodes:** `Module`, `Class`, `Function`, `Variable`, `Decorator`.
    *   **Edges:** `IMPORTS`, `CALLS`, `INHERITS_FROM`, `HAS_PARAMETER`, `RETURNS`, `IS_INSTANCE_OF`.

3.  **Storage:** This graph will be stored persistently. We can start with a file-based solution (`networkx` library) and graduate to a dedicated graph database (like Neo4j) as the complexity grows.

4.  **Integration with Context Building:**
    *   When the `Engine` prepares context for an LLM call, it will no longer just provide raw file content.
    *   It will query the Code Knowledge Graph to find the most relevant sub-graph related to the user's query. For a query like "where is authentication handled?", it can perform a graph traversal starting from nodes named "auth" to find all connected functions, classes, and modules.
    *   The context passed to the LLM will be a serialized, human-readable representation of this sub-graph, providing deep, semantic context.

**Strategic Impact:** This is the single most important step to elevate the quality of the agent's code generation and analysis. It allows the agent to reason about code structure and architecture, not just text. It will dramatically reduce hallucinations and improve the relevance and accuracy of its outputs.
