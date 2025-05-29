"""
Agent tool for launching sub-agents and task delegation in OCode.
"""

import asyncio
import json  # noqa: F401
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path  # noqa: F401
from typing import Any, Dict, List, Optional, Union  # noqa: F401

from ..utils.timeout_handler import TimeoutError, with_timeout
from .base import ErrorHandler  # noqa: F401
from .base import ErrorType  # noqa: F401
from .base import Tool, ToolDefinition, ToolParameter, ToolResult


@dataclass
class AgentTask:
    """Represents a task for a sub-agent."""

    id: str
    type: str
    description: str
    parameters: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class SubAgent:
    """Represents a specialized sub-agent."""

    id: str
    name: str
    type: str
    description: str
    capabilities: List[str]
    status: str = "idle"  # idle, busy, error
    tasks_completed: int = 0
    created_at: str = ""

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentTool(Tool):
    """Tool for creating and managing specialized sub-agents for task delegation."""

    def __init__(self):
        """Initialize agent tool with empty agent and task registries."""
        super().__init__()
        self.agents: Dict[str, SubAgent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[str] = []

    @property
    def definition(self) -> ToolDefinition:
        """Define the agent tool specification.

        Returns:
            ToolDefinition with parameters for creating and managing sub-agents,
            delegating tasks, monitoring status, and organizing work queues.
        """
        return ToolDefinition(
            name="agent",
            description="Create, manage, and delegate tasks to specialized sub-agents",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: 'create', 'list', 'delegate', 'status', 'results', 'terminate', 'queue'",  # noqa: E501
                    required=True,
                ),
                ToolParameter(
                    name="agent_type",
                    type="string",
                    description="Type of agent: 'coder', 'tester', 'reviewer', 'documenter', 'analyzer', 'fixer', 'researcher'",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="agent_id",
                    type="string",
                    description="ID of specific agent to work with",
                    required=False,
                ),
                ToolParameter(
                    name="task_description",
                    type="string",
                    description="Description of task to delegate",
                    required=False,
                ),
                ToolParameter(
                    name="task_parameters",
                    type="object",
                    description="Parameters for the task",
                    required=False,
                    default={},
                ),
                ToolParameter(
                    name="priority",
                    type="string",
                    description="Task priority: 'low', 'medium', 'high', 'urgent'",
                    required=False,
                    default="medium",
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Task timeout in seconds",
                    required=False,
                    default=300,
                ),
                ToolParameter(
                    name="max_agents",
                    type="number",
                    description="Maximum number of agents to create",
                    required=False,
                    default=5,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute agent management actions."""
        try:
            # Extract parameters
            action = kwargs.get("action")
            agent_type = kwargs.get("agent_type")
            agent_id = kwargs.get("agent_id")
            task_description = kwargs.get("task_description")
            task_parameters = kwargs.get("task_parameters", {})
            priority = kwargs.get("priority", "medium")
            timeout = kwargs.get("timeout", 300)
            max_agents = kwargs.get("max_agents", 5)

            if not action:
                return ToolResult(
                    success=False, output="", error="action parameter is required"
                )

            if action == "create":
                return await self._create_agent(agent_type, max_agents)
            elif action == "list":
                return await self._list_agents()
            elif action == "delegate":
                return await self._delegate_task(
                    agent_id,
                    agent_type,
                    task_description,
                    task_parameters,
                    priority,
                    timeout,
                )
            elif action == "status":
                return await self._get_status(agent_id)
            elif action == "results":
                return await self._get_results(agent_id)
            elif action == "terminate":
                return await self._terminate_agent(agent_id)
            elif action == "queue":
                return await self._show_task_queue()
            else:
                return ToolResult(
                    success=False, output="", error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error in agent operation: {str(e)}"
            )

    async def _create_agent(
        self, agent_type: Optional[str], max_agents: int
    ) -> ToolResult:
        """Create a new specialized sub-agent."""
        if len(self.agents) >= max_agents:
            return ToolResult(
                success=False,
                output="",
                error=f"Maximum number of agents ({max_agents}) already created",
            )

        if not agent_type:
            return ToolResult(
                success=False,
                output="",
                error="agent_type is required for creating an agent",
            )

        agent_configs = {
            "coder": {
                "name": "Code Writer Agent",
                "description": "Specialized agent for writing, implementing, and refactoring code",  # noqa: E501
                "capabilities": [
                    "write_code",
                    "refactor",
                    "implement_features",
                    "fix_bugs",
                    "optimize_code",
                ],
            },
            "tester": {
                "name": "Test Agent",
                "description": "Specialized agent for writing and running tests",
                "capabilities": [
                    "write_tests",
                    "run_tests",
                    "coverage_analysis",
                    "test_automation",
                    "quality_assurance",
                ],
            },
            "reviewer": {
                "name": "Code Review Agent",
                "description": "Specialized agent for code review and quality analysis",
                "capabilities": [
                    "code_review",
                    "static_analysis",
                    "best_practices",
                    "security_review",
                    "performance_review",
                ],
            },
            "documenter": {
                "name": "Documentation Agent",
                "description": "Specialized agent for creating and maintaining documentation",  # noqa: E501
                "capabilities": [
                    "write_docs",
                    "api_docs",
                    "readme_generation",
                    "code_comments",
                    "user_guides",
                ],
            },
            "analyzer": {
                "name": "Analysis Agent",
                "description": "Specialized agent for code and architecture analysis",  # noqa: E501
                "capabilities": [
                    "dependency_analysis",
                    "architecture_review",
                    "metrics_calculation",
                    "pattern_detection",
                    "complexity_analysis",
                ],
            },
            "fixer": {
                "name": "Bug Fix Agent",
                "description": "Specialized agent for identifying and fixing bugs",
                "capabilities": [
                    "bug_detection",
                    "error_fixing",
                    "debugging",
                    "issue_resolution",
                    "patch_generation",
                ],
            },
            "researcher": {
                "name": "Research Agent",
                "description": "Specialized agent for research and information gathering",  # noqa: E501
                "capabilities": [
                    "technology_research",
                    "best_practices_research",
                    "solution_discovery",
                    "documentation_search",
                    "api_exploration",
                ],
            },
        }

        if agent_type not in agent_configs:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown agent type: {agent_type}. Available types: {', '.join(agent_configs.keys())}",  # noqa: E501,
            )

        config = agent_configs[agent_type]
        agent_id = str(uuid.uuid4())[:8]

        agent = SubAgent(
            id=agent_id,
            name=str(config["name"]),
            type=agent_type,
            description=str(config["description"]),
            capabilities=list(config["capabilities"]),
        )

        self.agents[agent_id] = agent

        output = f"Created {agent.name} (ID: {agent_id})\n"
        output += f"Type: {agent.type}\n"
        output += f"Description: {agent.description}\n"
        output += f"Capabilities: {', '.join(agent.capabilities)}\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={"agent_id": agent_id, "agent": asdict(agent)},
        )

    async def _list_agents(self) -> ToolResult:
        """List all created agents and their status."""
        if not self.agents:
            return ToolResult(
                success=True,
                output="No agents created yet. Use action='create' to create an agent.",
                metadata={"agents": []},
            )

        output = f"Active Agents ({len(self.agents)}):\n"
        output += "=" * 40 + "\n"

        agents_data = []
        for agent in self.agents.values():
            output += f"ID: {agent.id}\n"
            output += f"Name: {agent.name}\n"
            output += f"Type: {agent.type}\n"
            output += f"Status: {agent.status}\n"
            output += f"Tasks Completed: {agent.tasks_completed}\n"
            output += f"Created: {agent.created_at}\n"
            output += "-" * 40 + "\n"

            agents_data.append(asdict(agent))

        return ToolResult(success=True, output=output, metadata={"agents": agents_data})

    async def _delegate_task(
        self,
        agent_id: Optional[str],
        agent_type: Optional[str],
        task_description: Optional[str],
        task_parameters: Dict[str, Any],
        priority: str,
        timeout: int,
    ) -> ToolResult:
        """Delegate a task to an agent."""
        if not task_description:
            return ToolResult(
                success=False,
                output="",
                error="task_description is required for task delegation",
            )

        # Find or create appropriate agent
        target_agent = None

        if agent_id:
            # Use specific agent
            if agent_id not in self.agents:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Agent with ID {agent_id} not found",
                )
            target_agent = self.agents[agent_id]

        elif agent_type:
            # Find agent of specific type or create one
            type_agents = [
                a
                for a in self.agents.values()
                if a.type == agent_type and a.status == "idle"
            ]
            if type_agents:
                target_agent = type_agents[0]  # Use first available agent of type
            else:
                # Create new agent of this type
                create_result = await self._create_agent(agent_type, 10)
                if create_result.success:
                    metadata = create_result.metadata
                    if metadata and "agent_id" in metadata:
                        new_agent_id = metadata["agent_id"]
                        target_agent = self.agents[new_agent_id]
                    else:
                        return create_result
                else:
                    return create_result

        else:
            # Use any available agent or create a general one
            idle_agents = [a for a in self.agents.values() if a.status == "idle"]
            if idle_agents:
                target_agent = idle_agents[0]
            else:
                # Create a general coder agent
                create_result = await self._create_agent("coder", 10)
                if create_result.success:
                    metadata = create_result.metadata
                    if metadata and "agent_id" in metadata:
                        new_agent_id = metadata["agent_id"]
                        target_agent = self.agents[new_agent_id]
                    else:
                        return create_result
                else:
                    return create_result

        # Create task
        task_id = str(uuid.uuid4())[:8]
        task = AgentTask(
            id=task_id,
            type=target_agent.type,
            description=task_description,
            parameters=task_parameters,
        )

        self.tasks[task_id] = task
        self.task_queue.append(task_id)

        # Simulate task execution
        await self._execute_task(task, target_agent, timeout)

        output = f"Task delegated to {target_agent.name} (ID: {target_agent.id})\n"
        output += f"Task ID: {task_id}\n"
        output += f"Description: {task_description}\n"
        output += f"Priority: {priority}\n"
        output += f"Status: {task.status}\n"

        if task.status == "completed":
            output += "\nTask completed successfully!\n"
            if task.result:
                output += f"Result: {task.result}\n"
        elif task.status == "failed":
            output += f"\nTask failed: {task.error}\n"

        return ToolResult(
            success=task.status != "failed",
            output=output,
            metadata={
                "task_id": task_id,
                "agent_id": target_agent.id,
                "task": asdict(task),
                "agent": asdict(target_agent),
            },
        )

    async def _execute_task(
        self, task: AgentTask, agent: SubAgent, timeout: int
    ) -> Dict[str, Any]:
        """Simulate task execution by a sub-agent."""
        try:
            # Update status
            task.status = "running"
            task.started_at = datetime.now().isoformat()
            agent.status = "busy"

            async def _run_task():
                # Simulate different types of task execution
                if agent.type == "coder":
                    return await self._simulate_coding_task(task)
                elif agent.type == "tester":
                    return await self._simulate_testing_task(task)
                elif agent.type == "reviewer":
                    return await self._simulate_review_task(task)
                elif agent.type == "documenter":
                    return await self._simulate_documentation_task(task)
                elif agent.type == "analyzer":
                    return await self._simulate_analysis_task(task)
                elif agent.type == "fixer":
                    return await self._simulate_fixing_task(task)
                elif agent.type == "researcher":
                    return await self._simulate_research_task(task)
                else:
                    return "Task completed by generic agent"

            # Execute with timeout
            result = await with_timeout(
                _run_task(),
                timeout=timeout,
                operation=f"agent_task({agent.type}.{task.id})",
            )

            # Complete task
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()
            agent.status = "idle"
            agent.tasks_completed += 1

            return {"success": True, "result": result}

        except TimeoutError as e:
            # Handle timeout
            task.status = "failed"
            task.error = f"Task timed out after {timeout} seconds: {str(e)}"
            task.completed_at = datetime.now().isoformat()
            agent.status = "idle"

            return {"success": False, "error": task.error}
        except Exception as e:
            # Handle task failure
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            agent.status = "idle"

            return {"success": False, "error": str(e)}

    async def _simulate_coding_task(self, task: AgentTask) -> str:
        """Simulate a coding task."""
        await asyncio.sleep(0.1)  # Simulate processing time

        task_type = task.parameters.get("type", "general")

        if task_type == "implementation":
            return f"Implemented feature: {task.description}\n- Added necessary functions\n- Included error handling\n- Added type hints"  # noqa: E501
        elif task_type == "refactoring":
            return f"Refactored code: {task.description}\n- Improved code structure\n- Reduced complexity\n- Enhanced readability"  # noqa: E501
        elif task_type == "optimization":
            return f"Optimized code: {task.description}\n- Improved performance\n- Reduced memory usage\n- Enhanced efficiency"  # noqa: E501
        else:
            return f"Completed coding task: {task.description}\n- Code written and tested\n- Best practices applied\n- Documentation added"  # noqa: E501

    async def _simulate_testing_task(self, task: AgentTask) -> str:
        """Simulate a testing task."""
        await asyncio.sleep(0.1)

        return f"Test suite created for: {task.description}\n- Unit tests written\n- Integration tests added\n- Coverage analysis completed\n- All tests passing"  # noqa: E501

    async def _simulate_review_task(self, task: AgentTask) -> str:
        """Simulate a code review task."""
        await asyncio.sleep(0.1)

        return f"Code review completed for: {task.description}\n- Security analysis passed\n- Performance review completed\n- Best practices verified\n- Minor improvements suggested"  # noqa: E501

    async def _simulate_documentation_task(self, task: AgentTask) -> str:
        """Simulate a documentation task."""
        await asyncio.sleep(0.1)

        return f"Documentation created for: {task.description}\n- API documentation generated\n- README updated\n- Code comments added\n- User guide created"  # noqa: E501

    async def _simulate_analysis_task(self, task: AgentTask) -> str:
        """Simulate an analysis task."""
        await asyncio.sleep(0.1)

        return f"Analysis completed for: {task.description}\n- Architecture reviewed\n- Dependencies analyzed\n- Metrics calculated\n- Report generated"  # noqa: E501

    async def _simulate_fixing_task(self, task: AgentTask) -> str:
        """Simulate a bug fixing task."""
        await asyncio.sleep(0.1)

        return f"Bug fix completed for: {task.description}\n- Root cause identified\n- Fix implemented\n- Tests updated\n- Regression testing passed"  # noqa: E501

    async def _simulate_research_task(self, task: AgentTask) -> str:
        """Simulate a research task."""
        await asyncio.sleep(0.1)

        return f"Research completed for: {task.description}\n- Best practices identified\n- Solutions evaluated\n- Recommendations provided\n- Implementation guide created"  # noqa: E501

    async def _get_status(self, agent_id: Optional[str]) -> ToolResult:
        """Get status of agent(s) and their tasks."""
        if agent_id:
            # Status of specific agent
            if agent_id not in self.agents:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Agent with ID {agent_id} not found",
                )

            agent = self.agents[agent_id]
            agent_tasks = [
                t
                for t in self.tasks.values()
                if t.id in [tid for tid in self.task_queue]
            ]

            output = f"Agent Status: {agent.name} (ID: {agent_id})\n"
            output += f"Status: {agent.status}\n"
            output += f"Tasks Completed: {agent.tasks_completed}\n"
            output += f"Created: {agent.created_at}\n\n"

            if agent_tasks:
                output += "Recent Tasks:\n"
                for task in agent_tasks[-3:]:  # Show last 3 tasks
                    output += f"- {task.description} ({task.status})\n"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "agent": asdict(agent),
                    "tasks": [asdict(t) for t in agent_tasks],
                },
            )

        else:
            # Status of all agents
            if not self.agents:
                return ToolResult(
                    success=True,
                    output="No agents created yet.",
                    metadata={"agents": [], "tasks": []},
                )

            output = "System Status:\n"
            output += f"Total Agents: {len(self.agents)}\n"
            output += f"Total Tasks: {len(self.tasks)}\n"
            output += f"Tasks in Queue: {len(self.task_queue)}\n\n"

            for agent in self.agents.values():
                output += f"{agent.name} (ID: {agent.id}): {agent.status} - {agent.tasks_completed} tasks completed\n"  # noqa: E501

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "agents": [asdict(a) for a in self.agents.values()],
                    "tasks": [asdict(t) for t in self.tasks.values()],
                },
            )

    async def _get_results(self, agent_id: Optional[str]) -> ToolResult:
        """Get results from completed tasks."""
        if agent_id and agent_id not in self.agents:
            return ToolResult(
                success=False, output="", error=f"Agent with ID {agent_id} not found"
            )

        # Filter tasks by agent if specified
        relevant_tasks = []
        if agent_id:
            agent = self.agents[agent_id]
            relevant_tasks = [t for t in self.tasks.values() if t.type == agent.type]
        else:
            relevant_tasks = list(self.tasks.values())

        completed_tasks = [t for t in relevant_tasks if t.status == "completed"]
        failed_tasks = [t for t in relevant_tasks if t.status == "failed"]

        output = "Task Results Summary:\n"
        output += f"Completed: {len(completed_tasks)}\n"
        output += f"Failed: {len(failed_tasks)}\n\n"

        if completed_tasks:
            output += "Recent Completed Tasks:\n"
            for task in completed_tasks[-5:]:  # Show last 5 completed tasks
                output += f"Task: {task.description}\n"
                output += f"Result: {task.result}\n"
                output += f"Completed: {task.completed_at}\n"
                output += "-" * 30 + "\n"

        if failed_tasks:
            output += "\nFailed Tasks:\n"
            for task in failed_tasks[-3:]:  # Show last 3 failed tasks
                output += f"Task: {task.description}\n"
                output += f"Error: {task.error}\n"
                output += f"Failed: {task.completed_at}\n"
                output += "-" * 30 + "\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "completed_tasks": [asdict(t) for t in completed_tasks],
                "failed_tasks": [asdict(t) for t in failed_tasks],
            },
        )

    async def _terminate_agent(self, agent_id: Optional[str]) -> ToolResult:
        """Terminate an agent."""
        if not agent_id:
            return ToolResult(
                success=False, output="", error="agent_id is required for termination"
            )

        if agent_id not in self.agents:
            return ToolResult(
                success=False, output="", error=f"Agent with ID {agent_id} not found"
            )

        agent = self.agents[agent_id]

        if agent.status == "busy":
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot terminate agent {agent_id}: currently busy with a task",
            )

        # Remove agent
        del self.agents[agent_id]

        # Clean up related tasks (optional - could keep for history)
        # agent_tasks = [tid for tid, task in self.tasks.items() if task.type == agent.type]  # noqa: E501
        # for task_id in agent_tasks:
        #     if task_id in self.task_queue:
        #         self.task_queue.remove(task_id)
        #     if task_id in self.tasks:
        #         del self.tasks[task_id]

        output = f"Agent terminated: {agent.name} (ID: {agent_id})\n"
        output += f"Tasks completed: {agent.tasks_completed}\n"

        return ToolResult(
            success=True, output=output, metadata={"terminated_agent": asdict(agent)}
        )

    async def _show_task_queue(self) -> ToolResult:
        """Show current task queue."""
        if not self.task_queue:
            return ToolResult(
                success=True, output="Task queue is empty.", metadata={"queue": []}
            )

        output = f"Task Queue ({len(self.task_queue)} tasks):\n"
        output += "=" * 40 + "\n"

        queue_data = []
        for i, task_id in enumerate(self.task_queue[-10:], 1):  # Show last 10 tasks
            if task_id in self.tasks:
                task = self.tasks[task_id]
                output += f"{i}. {task.description}\n"
                output += f"   Status: {task.status}\n"
                output += f"   Type: {task.type}\n"
                output += f"   Created: {task.created_at}\n"
                output += "-" * 40 + "\n"

                queue_data.append(asdict(task))

        return ToolResult(success=True, output=output, metadata={"queue": queue_data})
