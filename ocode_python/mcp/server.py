"""
MCP Server implementation for OCode.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.context_manager import ContextManager
from ..tools.base import ToolRegistry
from .protocol import MCPPrompt, MCPResource, MCPServer, MCPTool


class OCodeMCPServer(MCPServer):
    """
    OCode MCP Server that exposes OCode functionality via MCP protocol.
    """

    def __init__(self, project_root: Optional[Path] = None):
        super().__init__("ocode-mcp-server", "0.1.0")

        self.project_root = project_root or Path.cwd()
        self.context_manager = ContextManager(self.project_root)
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_core_tools()

        # Register OCode resources, tools, and prompts
        self._register_ocode_resources()
        self._register_ocode_tools()
        self._register_ocode_prompts()

    def _register_ocode_resources(self):
        """Register OCode-specific resources."""
        # Project files as resources
        try:
            for file_path in self.project_root.rglob("*"):
                if file_path.is_file() and not self._should_ignore_file(file_path):
                    # Convert to URI
                    uri = f"file://{file_path.absolute()}"

                    # Detect MIME type
                    mime_type = self._get_mime_type(file_path)

                    resource = MCPResource(
                        uri=uri,
                        name=str(file_path.relative_to(self.project_root)),
                        description=f"Project file: {file_path.name}",
                        mime_type=mime_type,
                    )

                    self.register_resource(resource)
        except Exception as e:
            print(f"Warning: Failed to register project files: {e}", file=sys.stderr)

        # Special resources
        special_resources = [
            MCPResource(
                uri="ocode://project/structure",
                name="Project Structure",
                description="Complete project directory structure",
                mime_type="application/json",
            ),
            MCPResource(
                uri="ocode://project/dependencies",
                name="Project Dependencies",
                description="Project dependency graph",
                mime_type="application/json",
            ),
            MCPResource(
                uri="ocode://project/symbols",
                name="Symbol Index",
                description="Index of all symbols in the project",
                mime_type="application/json",
            ),
            MCPResource(
                uri="ocode://git/status",
                name="Git Status",
                description="Current git repository status",
                mime_type="application/json",
            ),
        ]

        for resource in special_resources:
            self.register_resource(resource)

    def _register_ocode_tools(self):
        """Register OCode tools as MCP tools."""
        for tool in self.tool_registry.get_all_tools():
            definition = tool.definition

            # Convert OCode tool definition to MCP format
            input_schema: Dict[str, Any] = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            for param in definition.parameters:
                input_schema["properties"][param.name] = {
                    "type": param.type,
                    "description": param.description,
                }

                if param.default is not None:
                    input_schema["properties"][param.name]["default"] = param.default

                if param.required:
                    input_schema["required"].append(param.name)

            mcp_tool = MCPTool(
                name=definition.name,
                description=definition.description,
                input_schema=input_schema,
            )

            self.register_tool(mcp_tool)

    def _register_ocode_prompts(self):
        """Register OCode prompt templates."""
        prompts = [
            MCPPrompt(
                name="code_review",
                description="Review code for quality, bugs, and improvements",
                arguments=[
                    {
                        "name": "file_path",
                        "description": "Path to file to review",
                        "required": True,
                    },
                    {
                        "name": "focus",
                        "description": "Specific areas to focus on",
                        "required": False,
                    },
                ],
            ),
            MCPPrompt(
                name="refactor_code",
                description="Refactor code to improve quality and maintainability",
                arguments=[
                    {
                        "name": "file_path",
                        "description": "Path to file to refactor",
                        "required": True,
                    },
                    {
                        "name": "goal",
                        "description": "Refactoring goal",
                        "required": True,
                    },
                ],
            ),
            MCPPrompt(
                name="generate_tests",
                description="Generate unit tests for code",
                arguments=[
                    {
                        "name": "file_path",
                        "description": "Path to file to test",
                        "required": True,
                    },
                    {
                        "name": "test_framework",
                        "description": "Testing framework to use",
                        "required": False,
                    },
                ],
            ),
            MCPPrompt(
                name="explain_code",
                description="Explain how code works",
                arguments=[
                    {
                        "name": "file_path",
                        "description": "Path to file to explain",
                        "required": True,
                    },
                    {
                        "name": "detail_level",
                        "description": "Level of detail (basic/detailed/expert)",
                        "required": False,
                    },
                ],
            ),
            MCPPrompt(
                name="debug_issue",
                description="Help debug a code issue",
                arguments=[
                    {
                        "name": "error_message",
                        "description": "Error message or description",
                        "required": True,
                    },
                    {
                        "name": "context_files",
                        "description": "Relevant file paths",
                        "required": False,
                    },
                ],
            ),
        ]

        for prompt in prompts:
            self.register_prompt(prompt)

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored as a resource."""
        ignore_patterns = {
            ".git",
            ".ocode",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            ".env",
            ".DS_Store",
            ".idea",
            ".vscode",
        }

        # Check if any part of path matches ignore patterns
        for part in file_path.parts:
            if part in ignore_patterns:
                return True

        # Check file extensions
        if file_path.suffix in {".pyc", ".pyo", ".log", ".tmp"}:
            return True

        # Check file size (ignore very large files)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return True
        except OSError:
            return True

        return False

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file."""
        suffix = file_path.suffix.lower()

        mime_types = {
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".ts": "text/typescript",
            ".jsx": "text/jsx",
            ".tsx": "text/tsx",
            ".html": "text/html",
            ".css": "text/css",
            ".scss": "text/scss",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".toml": "text/toml",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".xml": "text/xml",
            ".sql": "text/sql",
            ".sh": "text/x-shellscript",
            ".go": "text/x-go",
            ".rs": "text/x-rust",
            ".java": "text/x-java",
            ".c": "text/x-c",
            ".cpp": "text/x-c++",
            ".h": "text/x-c",
            ".hpp": "text/x-c++",
        }

        return mime_types.get(suffix, "text/plain")

    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource read requests."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("uri parameter is required")

        # Handle special OCode resources
        if uri.startswith("ocode://"):
            return await self._read_ocode_resource(uri)

        # Handle file resources
        if uri.startswith("file://"):
            return await self._read_file_resource(uri)

        raise ValueError(f"Unsupported resource URI: {uri}")

    async def _read_ocode_resource(self, uri: str) -> Dict[str, Any]:
        """Read OCode-specific resources."""
        if uri == "ocode://project/structure":
            # Generate project structure
            structure = await self._generate_project_structure()
            return {
                "contents": [
                    {"uri": uri, "mimeType": "application/json", "text": structure}
                ]
            }

        elif uri == "ocode://project/dependencies":
            # Generate dependency graph
            context = await self.context_manager.build_context("", max_files=100)
            dependencies = {
                str(file_path): [str(dep) for dep in deps]
                for file_path, deps in context.dependencies.items()
            }

            import json

            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(dependencies, indent=2),
                    }
                ]
            }

        elif uri == "ocode://project/symbols":
            # Generate symbol index
            context = await self.context_manager.build_context("", max_files=100)
            symbols = {
                symbol: [str(file_path) for file_path in files]
                for symbol, files in context.symbols.items()
            }

            import json

            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(symbols, indent=2),
                    }
                ]
            }

        elif uri == "ocode://git/status":
            # Get git status
            try:
                from git import Repo

                repo = Repo(self.project_root, search_parent_directories=True)

                status = {
                    "branch": repo.active_branch.name,
                    "commit": repo.head.commit.hexsha,
                    "modified_files": [item.a_path for item in repo.index.diff(None)],
                    "staged_files": [item.a_path for item in repo.index.diff("HEAD")],
                    "untracked_files": repo.untracked_files,
                }

                import json

                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(status, indent=2),
                        }
                    ]
                }
            except Exception as e:
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": f'{{"error": "Not a git repository: {str(e)}"}}',
                        }
                    ]
                }

        else:
            raise ValueError(f"Unknown OCode resource: {uri}")

    async def _read_file_resource(self, uri: str) -> Dict[str, Any]:
        """Read file resources."""
        # Extract file path from URI
        file_path = Path(uri.replace("file://", ""))

        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            mime_type = self._get_mime_type(file_path)

            return {"contents": [{"uri": uri, "mimeType": mime_type, "text": content}]}
        except UnicodeDecodeError:
            # Handle binary files
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/octet-stream",
                        "blob": f"<binary file: {file_path.name}>",
                    }
                ]
            }

    async def _generate_project_structure(self) -> str:
        """Generate project structure as JSON."""
        import json

        def build_tree(
            path: Path, max_depth: int = 5, current_depth: int = 0
        ) -> Dict[str, Any]:
            if current_depth >= max_depth:
                return {"name": path.name, "type": "truncated"}

            if path.is_file():
                return {
                    "name": path.name,
                    "type": "file",
                    "size": path.stat().st_size,
                    "mime_type": self._get_mime_type(path),
                }
            elif path.is_dir() and not self._should_ignore_file(path):
                children = []
                try:
                    for child in sorted(path.iterdir()):
                        if not self._should_ignore_file(child):
                            children.append(
                                build_tree(child, max_depth, current_depth + 1)
                            )
                except PermissionError:
                    pass

                return {"name": path.name, "type": "directory", "children": children}
            else:
                return {"name": path.name, "type": "ignored"}

        structure = build_tree(self.project_root)
        return json.dumps(structure, indent=2)

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call requests."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("name parameter is required")

        # Execute OCode tool
        result = await self.tool_registry.execute_tool(name, **arguments)

        if result.success:
            return {
                "content": [{"type": "text", "text": result.output}],
                "isError": False,
            }
        else:
            return {
                "content": [
                    {"type": "text", "text": result.error or "Tool execution failed"}
                ],
                "isError": True,
            }

    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompt get requests."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("name parameter is required")

        prompt = self.prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        # Generate prompt based on name and arguments
        if name == "code_review":
            file_path = arguments.get("file_path", "")
            focus = arguments.get("focus", "general code quality")

            prompt_text = f"""Please review the code in {file_path} with focus on {focus}.  # noqa: E501

Consider the following aspects:
- Code quality and readability
- Potential bugs or issues
- Performance considerations
- Best practices adherence
- Security implications
- Maintainability

Provide specific, actionable feedback with code examples where appropriate."""

        elif name == "refactor_code":
            file_path = arguments.get("file_path", "")
            goal = arguments.get("goal", "improve code quality")

            prompt_text = f"""Please refactor the code in {file_path} to {goal}.

Guidelines:
- Maintain existing functionality
- Improve code structure and readability
- Follow language best practices
- Add appropriate comments/documentation
- Consider performance implications
- Ensure backwards compatibility where possible

Provide the refactored code with explanations of changes made."""

        elif name == "generate_tests":
            file_path = arguments.get("file_path", "")
            framework = arguments.get("test_framework", "auto-detect")

            prompt_text = f"""Please generate comprehensive unit tests for the code in {file_path}.  # noqa: E501

Requirements:
- Use {framework} testing framework (or auto-detect appropriate framework)
- Test all public methods/functions
- Include edge cases and error conditions
- Test both positive and negative scenarios
- Follow testing best practices
- Include setup/teardown if needed
- Add descriptive test names and comments

Provide complete, runnable test code."""

        elif name == "explain_code":
            file_path = arguments.get("file_path", "")
            detail_level = arguments.get("detail_level", "detailed")

            prompt_text = f"""Please explain how the code in {file_path} works at a {detail_level} level.  # noqa: E501

Include:
- Overall purpose and functionality
- Key algorithms or logic
- Data structures used
- Dependencies and relationships
- Input/output behavior
- Any notable design patterns
- Potential areas for improvement

Tailor the explanation to the specified detail level."""

        elif name == "debug_issue":
            error_message = arguments.get("error_message", "")
            context_files = arguments.get("context_files", [])

            prompt_text = f"""Please help debug this issue: {error_message}

Context files to examine: {', '.join(context_files) if context_files else 'auto-detect relevant files'}  # noqa: E501

Please:
- Analyze the error message and potential causes
- Examine relevant code files
- Identify the root cause
- Suggest specific fixes
- Provide step-by-step debugging approach
- Recommend prevention strategies

Be thorough and provide actionable solutions."""

        else:
            prompt_text = f"Execute {name} with arguments: {arguments}"

        return {
            "description": prompt.description,
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }


async def main():
    """Start OCode MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="OCode MCP Server")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    server = OCodeMCPServer(args.project_root)

    print(
        f"Starting OCode MCP Server for project: {args.project_root}", file=sys.stderr
    )
    print(f"Registered {len(server.resources)} resources", file=sys.stderr)
    print(f"Registered {len(server.tools)} tools", file=sys.stderr)
    print(f"Registered {len(server.prompts)} prompts", file=sys.stderr)

    await server.start_stdio()


if __name__ == "__main__":
    asyncio.run(main())
