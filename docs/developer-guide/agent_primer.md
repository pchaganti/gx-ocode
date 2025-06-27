
# Onboarding Guide for AI Developers

**Welcome to the `ocode` project!** This document is a comprehensive primer designed to bring a new AI developer up to speed on our architecture, conventions, and strategic goals. We'll approach this from three perspectives: the Project Manager, the Lead Developer, and the AI Architect.

---

### 1. The Project Manager's View: Vision & Priorities

**Hello, I'm the Project Manager.** My job is to ensure we're building the right product.

**Our Vision:** `ocode` is not just a chatbot that writes code. It is a proactive, autonomous software engineering partner. It should feel like pairing with a senior developer who can independently analyze problems, form strategies, execute complex tasks, and learn from the experience. Reliability, safety, and efficiency are our core product pillars.

**Strategic Priorities:**

1.  **Enhance Reliability (P0):** Our users must trust the agent to perform complex, multi-step tasks without failure. The `AdvancedOrchestrator` was a major step forward. Now, we must refine it to handle even more complex scenarios and recover gracefully from errors.
2.  **Improve Extensibility (P1):** The system must be easy to extend with new tools and new "specialist" agents. The Model Context Protocol (MCP) is the key to this, but it's not fully realized. A robust MCP will allow us to build a team of agents (e.g., a "Database Specialist", a "Frontend Expert") that can collaborate.
3.  **Optimize Performance & Cost (P2):** Every LLM call costs time and money. We need to be smarter about when and how we use the LLM. The "pre-flight check" to decide on tool use is a great example of this, but it can be better.
4.  **Deepen Contextual Understanding (P2):** The agent's ability to understand the user's project is critical. We need to move beyond simple file analysis to a deeper, semantic understanding of the codebase.

Your primary focus will be on these four areas. We value quality and thoughtful design over rushing out features.

---

### 2. The Lead Developer's View: Architecture & Conventions

**Hey, I'm the Lead Dev.** I care about clean, maintainable, and scalable code. Here’s how the project is structured and why.

**Core Architecture:**

*   **`ocode_python/core`**: This is the brain.
    *   `engine.py`: The central hub. It takes a user query and drives the entire process. It's responsible for the main loop, context building, and orchestrating the other components.
    *   `orchestrator.py`: The "hands." This is a crucial component that separates *planning* from *doing*. The engine decides *what* to do, and the orchestrator figures out *how* to do it safely and efficiently (with retries, concurrency, etc.). **Treat this as a critical, safety-oriented subsystem.**
    *   `context_manager.py`: The "eyes and ears." It reads files and understands the project structure.
*   **`ocode_python/tools`**: The toolbox. Each tool is a capability the agent can use. They are designed to be modular and independent.
*   **`ocode_python/mcp`**: The "phone." This is our **Model Context Protocol**. It's a JSON-RPC protocol that allows different processes (potentially on different machines) to communicate. The vision is to have specialized agents running as MCP servers, which the main engine can then "call" for expert help. This is our key to scaling beyond a single agent.

**Key Conventions:**

1.  **Separation of Concerns:** The `Engine` should not know the implementation details of a tool. It just knows the tool's name and arguments. The `Orchestrator` handles the execution. This is critical.
2.  **Immutability and Side Effects:** The `Orchestrator` and `SideEffectBroker` are designed to manage the messy reality of side effects (like writing files). When adding new tools, think carefully about the side effects and how they can be tracked and potentially rolled back.
3.  **Configuration-Driven:** Notice the `architecture` section in the config. We should be able to enable or disable major features (like semantic context or the advanced orchestrator) via configuration. This is essential for testing and stability.
4.  **Testing is Non-Negotiable:** Every new tool and feature must have corresponding unit and/or integration tests. The extensive `tests/` directory is a testament to this.

---

### 3. The AI Architect's View: Implementation Deep Dive

**I'm the AI Architect.** My focus is on the interface between the code and the Large Language Model. This is where the magic and the complexity live. Here are the detailed implementation plans for the priorities outlined by the PM.

#### Suggestion 1: Modularize the System Prompt (Priority: P2)

*   **Problem:** The `_build_system_prompt` function in `engine.py` is a massive, monolithic string. This is hard to read, hard to maintain, and sends a huge number of tokens with every single API call, which is inefficient.
*   **Implementation Plan:**
    1.  Create a new directory: `ocode_python/prompts/`.
    2.  Inside this directory, create subdirectories for different prompt components, e.g., `system/`, `analysis/`.
    3.  Break down the main system prompt into logical, reusable parts and save them as markdown files. For example:
        *   `prompts/system/role.md`: `<role>You are an expert AI coding assistant...</role>`
        *   `prompts/system/core_capabilities.md`: `<core_capabilities>...</core_capabilities>`
        *   `prompts/system/workflow_patterns.md`: `<workflow_patterns>...</workflow_patterns>`
        *   `prompts/analysis/tool_usage_criteria.md`: `<decision_criteria>...</decision_criteria>`
    4.  Modify `_build_system_prompt` to be a "prompt composer." It should read these smaller template files and assemble them into the final prompt. This allows for more dynamic prompt construction. For example, if a query doesn't require complex workflows, you could omit the `workflow_patterns.md` section to save tokens.
    5.  **Advanced Step:** Implement a simple caching mechanism. If the prompt components haven't changed, you can use a cached version of the composed prompt.

#### Suggestion 2: Refine the Tool-Use Decision Logic (Priority: P1)

*   **Problem:** The `_llm_should_use_tools` function makes a full LLM call just to classify the user's intent. This adds significant latency to every single turn.
*   **Implementation Plan:**
    1.  **Heuristic First:** Before calling the LLM, implement a fast, heuristic-based check. Create a function `_heuristic_tool_check(query: str) -> Optional[bool]`.
        *   This function will use regex or simple string matching to look for keywords.
        *   **Knowledge keywords (return `False`):** `what is`, `explain`, `how does`, `compare`, `difference between`.
        *   **Tool keywords (return `True`):** `list files`, `read`, `write`, `find`, `git status`, `run`.
        *   If a keyword is found, return the corresponding boolean. If not, return `None`.
    2.  **Modify the Flow:** In `engine.py`, call the heuristic function first. If it returns a boolean, use that result directly. If it returns `None`, *then* proceed with the existing `_llm_should_use_tools` call as a fallback.
    3.  **Logging:** Add verbose logging to track when the heuristic is used versus the LLM fallback. This will give us data on how effective the heuristic is.
    4.  **Future Vision:** This hybrid approach gives us the best of both worlds: speed for simple cases, and accuracy for complex ones. Down the line, we can use the logs we're gathering to fine-tune a small, dedicated classification model to replace the heuristic *and* the expensive LLM call.

#### Suggestion 3: Enhance Tool Definitions (Priority: P0)

*   **Problem:** The `AdvancedOrchestrator`'s ability to run tools in parallel is limited by its heuristic-based understanding of which tools conflict. This is fragile. For example, it might not know that `git_commit` and `git_push` both modify the git repository and should not be run concurrently.
*   **Implementation Plan:**
    1.  **Modify `ToolDefinition`:** Open `ocode_python/tools/base.py`. Add new fields to the `ToolDefinition` dataclass:
        ```python
        from enum import Enum

        class ResourceLock(Enum):
            FILESYSTEM_WRITE = "filesystem_write"
            GIT = "git"
            MEMORY = "memory"
            # Add more as needed

        @dataclass
        class ToolDefinition:
            name: str
            description: str
            # ... existing fields ...
            # New field:
            resource_locks: List[ResourceLock] = field(default_factory=list)
        ```
    2.  **Update Tool Definitions:** Go through every tool in `ocode_python/tools/` and update its definition to declare the resources it locks.
        *   `file_write_tool`: `resource_locks=[ResourceLock.FILESYSTEM_WRITE]`
        *   `git_tools`: `resource_locks=[ResourceLock.GIT]`
        *   `memory_tools`: `resource_locks=[ResourceLock.MEMORY]`
        *   Read-only tools like `file_read` or `ls` would have an empty list.
    3.  **Refactor the Orchestrator:** In `ocode_python/core/orchestrator.py`, modify the `_group_independent_tasks` function in `ConcurrentToolExecutor`. Instead of using heuristics to guess resource conflicts, it should now read the `resource_locks` from each task's tool definition. Tasks can run in parallel if and only if their sets of `resource_locks` are disjoint. This will be far more reliable.

#### Suggestion 4: Document and Complete the MCP (Priority: P1)

*   **Problem:** The Model Context Protocol is a powerful concept but is undocumented and incomplete (`TODO`s exist). A new developer would have no idea what it's for or how to use it.
*   **Implementation Plan:**
    1.  **Create Documentation:** Create a new file: `docs/developer-guide/mcp_protocol.md`.
        *   In this file, explain the **vision**: The MCP allows us to run specialized AI agents as standalone servers. The main `ocode` engine can then discover and delegate tasks to these specialists.
        *   Provide a **tutorial**: Write a step-by-step guide on how to create a new specialist agent. This would involve:
            1.  Creating a new Python file.
            2.  Importing `MCPServer` from `ocode_python.mcp.protocol`.
            3.  Creating instances of `MCPTool` or `MCPResource` to define the agent's capabilities.
            4.  Registering them with the server instance.
            5.  Starting the server.
    2.  **Complete the `TODO`s:** Work through `ocode_python/mcp/protocol.py` and implement the missing pieces. This likely involves the actual logic for reading resource content and executing tools, which are currently placeholders.
    3.  **Add Security:** This is critical. When the engine calls an MCP server, it's asking it to execute code. We need a basic security model.
        *   Implement a simple token-based authentication. The main engine and the MCP server can share a secret token.
        *   The `initialize` request in the MCP should include this token. The server should reject any connection that doesn't provide the correct token. This prevents unauthorized processes from connecting to your specialist agents.

### Your First Tasks

Here is a prioritized list of what to work on first.

1.  **Task 1 (P0): Implement Suggestion #3 (Enhance Tool Definitions).** This is a top priority because it directly impacts the reliability and safety of the core agent. Start by modifying the `ToolDefinition`, then update the tools, and finally refactor the orchestrator. Write tests to prove that the new locking mechanism works.
2.  **Task 2 (P1): Implement Suggestion #2 (Refine Tool-Use Decision Logic).** This is a high-impact performance improvement. Implement the heuristic-first approach.
3.  **Task 3 (P1): Begin work on Suggestion #4 (Document and Complete the MCP).** Start by writing the documentation. This will force you to deeply understand the protocol. Then, move on to implementing the `TODO`s.

Welcome to the team. We're excited to see what you build.
