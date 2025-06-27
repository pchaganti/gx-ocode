
# Product & Engineering Spec: Explicit Task Planning

**Status:** Proposed | **Authors:** Gemini Architect | **Version:** 1.0

## 1. Overview

This document specifies the design and implementation of a new **Explicit Task Planning** system. This system will fundamentally upgrade the agent's core reasoning capability, moving it from a reactive, single-step "chain-of-thought" model to a proactive, multi-step planning model. The agent will learn to decompose high-level user goals into a structured graph of dependent tasks, present this plan for approval, and then execute it with high reliability.

This is the foundational step for enabling the agent to handle complex, long-running, and ambiguous software engineering tasks.

## 2. Product Requirements

### 2.1. Vision & Goal

Our users need an agent that can tackle goals like "*add Google OAuth login*" or "*refactor the API to be more RESTful*." These are not single-command tasks. They require foresight, strategy, and the ability to execute a multi-step plan. This feature gives our users a transparent and trustworthy partner for these complex endeavors.

### 2.2. User Stories

*   **As a developer,** when I give the agent a complex goal, I want to see a clear, step-by-step plan of action *before* it starts making changes, so that I can verify its approach and have confidence in the outcome.
*   **As a developer,** I want the agent to be able to execute long-running tasks without getting lost or stuck, so that I can delegate significant work to it.
*   **As a developer,** if a step in a long plan fails, I want the agent to be able to pause, attempt a fix, or ask for help, rather than failing the entire task.

### 2.3. Requirements & Success Criteria

*   **REQ-PLAN-01:** The system MUST be able to take a high-level user query and generate a machine-readable plan, represented as a Directed Acyclic Graph (DAG) of tasks.
*   **REQ-PLAN-02:** The agent MUST present a human-readable summary of the plan to the user for confirmation before execution begins.
*   **REQ-PLAN-03:** The `Orchestrator` MUST be able to execute a task graph, respecting all dependencies.
*   **REQ-PLAN-04:** The system MUST support parallel execution of independent tasks within the graph (e.g., reading two unrelated files can happen at the same time).
*   **Success Criteria:** The agent can successfully generate and execute a plan of at least 5 steps for a novel task (e.g., "create a new API endpoint, its service, and a basic test for it").

## 3. Technical Architecture & Design

This feature introduces one new module (`PlanningModule`) and requires significant modifications to two existing modules (`Engine`, `Orchestrator`).

### 3.1. Data Structure: The `TaskGraph`

This is the central data structure. It will be defined in a new file: `ocode_python/core/task_graph.py`.

```python
# ocode_python/core/task_graph.py
from dataclasses import dataclass, field
from typing import Dict, List, Set

# We will reuse the CommandTask from the Orchestrator
from .orchestrator import CommandTask

@dataclass
class TaskGraph:
    """Represents a DAG of tasks to be executed."""
    tasks: Dict[str, CommandTask] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=dict) # task_id -> set of dependency_ids

    def add_task(self, task: CommandTask, deps: List[str] = None):
        """Adds a task and its dependencies to the graph."""
        self.tasks[task.task_id] = task
        self.dependencies[task.task_id] = set(deps or [])

    def get_ready_tasks(self) -> List[CommandTask]:
        """Returns a list of tasks whose dependencies are all met."""
        # Implementation detail: find tasks whose dependencies are in the
        # set of completed task IDs.
        pass

    def mark_task_complete(self, task_id: str):
        """Marks a task as complete, unlocking its dependents."""
        pass
```

### 3.2. New Module: `PlanningModule`

This module is responsible for generating the `TaskGraph`.

*   **Location:** `ocode_python/core/planning.py`
*   **Class:** `PlanningModule`
*   **Key Method:** `async def generate_plan(self, query: str) -> TaskGraph:`
    1.  **Invoke Planner Persona:** This method will use a new, dedicated system prompt (`prompts/system/planner.md`) designed for planning. The prompt will instruct the LLM to think step-by-step and output a plan in a specific JSON format.
    2.  **LLM Output Format (JSON):** The LLM must be prompted to return a JSON object that can be directly deserialized into our `TaskGraph` structure. This is critical for reliability.

        *Prompt to LLM (conceptual):* `"...Your output MUST be a JSON object with two keys: 'tasks' and 'dependencies'. 'tasks' is a list of objects, each with 'tool_name' and 'arguments'. 'dependencies' is a dictionary mapping a task's 'id' to a list of 'id's it depends on. Use 'id' fields to define dependencies. Example: ..."`

    3.  **Parsing and Validation:** The method will parse the LLM's JSON output and construct a `TaskGraph` object. It must validate the graph to ensure it is a DAG and that all specified tools exist.

### 3.3. Modifications to `Engine`

*   The `process` method in `engine.py` will be the entry point.
*   It will contain new logic to decide if a query requires planning.
    *   **Heuristic:** A simple heuristic (e.g., query length, presence of keywords like "implement," "refactor," "create a new") will trigger planning mode.
    *   **Flow:**
        1.  High-level query detected.
        2.  Instantiate `PlanningModule`.
        3.  Call `planning_module.generate_plan(query)` to get the `TaskGraph`.
        4.  **Present Plan to User:** Convert the `TaskGraph` into a human-readable list and ask for confirmation.
        5.  If confirmed, pass the `TaskGraph` to the `Orchestrator` for execution.

### 3.4. Modifications to `Orchestrator`

*   The `Orchestrator` is currently designed around a single queue. It will be upgraded to handle graph-based execution.
*   **New Method:** `async def execute_graph(self, graph: TaskGraph):`
    1.  Initialize a set of `completed_task_ids`.
    2.  Enter a loop that continues as long as there are incomplete tasks.
    3.  Inside the loop, call `graph.get_ready_tasks()` to find all tasks whose dependencies are in `completed_task_ids`.
    4.  Use the existing `ConcurrentToolExecutor` to execute all ready tasks in parallel.
    5.  As tasks complete, add their IDs to `completed_task_ids` and log the result.
    6.  If a task fails, the loop will pause, and the `Orchestrator` will report the failure back to the `Engine` (enabling future error-recovery logic).

## 4. Implementation Plan (For Agent Execution)

This project will be implemented in four distinct phases.

*   **Phase 1: Foundational Data Structures**
    1.  Create the new file `ocode_python/core/task_graph.py`.
    2.  Implement the `TaskGraph` class as specified in section 3.1.
    3.  Write comprehensive unit tests for `TaskGraph` (`tests/unit/test_task_graph.py`), ensuring that dependency tracking and the `get_ready_tasks` method work correctly.

*   **Phase 2: The Planning Module**
    1.  Create the new file `ocode_python/core/planning.py`.
    2.  Create the `prompts/system/planner.md` file. This prompt is critical and must be carefully engineered to produce reliable JSON.
    3.  Implement the `PlanningModule` class and its `generate_plan` method. Focus on the interaction with the LLM and the robust parsing/validation of its output.
    4.  Write integration tests for the `PlanningModule` that provide a sample query and assert that a valid `TaskGraph` is produced.

*   **Phase 3: Orchestrator Upgrade**
    1.  Modify `ocode_python/core/orchestrator.py`.
    2.  Implement the new `execute_graph` method as specified in section 3.4.
    3.  Refactor the existing `_worker_loop` to be compatible with or replaced by this new graph execution logic.
    4.  Write integration tests that create a sample `TaskGraph` and pass it to the `Orchestrator`, verifying that it executes tasks in the correct order.

*   **Phase 4: Engine Integration**
    1.  Modify the `process` method in `ocode_python/core/engine.py`.
    2.  Implement the logic to detect planning-level queries.
    3.  Integrate the full flow: `Engine` -> `PlanningModule` -> User Confirmation -> `Orchestrator`.
    4.  Perform end-to-end testing with a real user query.

## 5. Testing Strategy

*   **Unit Tests:** Each new class (`TaskGraph`, `PlanningModule`) will have dedicated unit tests.
*   **Integration Tests:**
    *   Test the `PlanningModule`'s ability to generate a valid graph from a query.
    *   Test the `Orchestrator`'s ability to execute a pre-defined graph correctly.
*   **End-to-End (E2E) Tests:** A full test case in `tests/integration/` will simulate a user providing a high-level goal and verify that the plan is generated, confirmed, and executed successfully.
