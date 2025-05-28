"""
Testing and code quality tools.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ConfigDict

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class ExecutionTool(Tool):
    """Tool for running tests in the project."""

    def __init__(self):
        self._definition = ToolDefinition(
            name="test_runner",
            description="Run tests in the project",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to test directory or file",
                    required=False,
                ),
                ToolParameter(
                    name="framework",
                    type="string",
                    description="Test framework to use (pytest, unittest)",
                    required=False,
                ),
                ToolParameter(
                    name="verbose",
                    type="boolean",
                    description="Enable verbose output",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Test execution timeout in seconds",
                    required=False,
                    default=300,
                ),
            ],
        )
        super().__init__()

    @property
    def definition(self):
        return self._definition

    def _detect_test_framework(self, path: str) -> str:
        """Auto-detect the appropriate test framework."""
        test_path = Path(path)

        # Check for specific test files and configs
        if (test_path / "pytest.ini").exists() or (
            test_path / "pyproject.toml"
        ).exists():
            return "pytest"

        if (test_path / "package.json").exists():
            try:
                with open(test_path / "package.json") as f:
                    package_data = json.load(f)
                    if "jest" in package_data.get("devDependencies", {}):
                        return "jest"
            except Exception:
                pass

        if (test_path / "go.mod").exists():
            return "go"

        # Check for Python test files
        for file_path in test_path.rglob("test_*.py"):
            return "pytest"

        for file_path in test_path.rglob("*_test.py"):
            return "pytest"

        # Check for JavaScript test files
        for file_path in test_path.rglob("*.test.js"):
            return "jest"

        for file_path in test_path.rglob("*.spec.js"):
            return "jest"

        # Check for Go test files
        for file_path in test_path.rglob("*_test.go"):
            return "go"

        return "pytest"  # Default fallback

    async def _run_pytest(
        self, path: str, pattern: Optional[str], verbose: bool, timeout: int
    ) -> ToolResult:
        """Run pytest tests."""
        cmd_parts = ["python", "-m", "pytest"]

        if verbose:
            cmd_parts.append("-v")

        if pattern:
            cmd_parts.extend(["-k", pattern])

        cmd_parts.append(path)

        command = " ".join(cmd_parts)

        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8") if stdout else ""
            error = stderr.decode("utf-8") if stderr else ""

            # Parse pytest output for summary
            lines = output.split("\n")
            summary_line = ""
            for line in lines:
                if "passed" in line or "failed" in line or "error" in line:
                    summary_line = line.strip()

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output,
                error=error if not success else None,
                metadata={
                    "framework": "pytest",
                    "return_code": process.returncode,
                    "summary": summary_line,
                },
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Tests timed out after {timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to run pytest: {str(e)}"
            )

    async def _run_jest(
        self, path: str, pattern: Optional[str], verbose: bool, timeout: int
    ) -> ToolResult:
        """Run Jest tests."""
        cmd_parts = ["npm", "test"]

        if pattern:
            cmd_parts.extend(["--", "--testNamePattern", pattern])

        if verbose:
            cmd_parts.append("--verbose")

        command = " ".join(cmd_parts)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8") if stdout else ""
            error = stderr.decode("utf-8") if stderr else ""

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output,
                error=error if not success else None,
                metadata={"framework": "jest", "return_code": process.returncode},
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Tests timed out after {timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to run Jest: {str(e)}"
            )

    async def _run_go_test(
        self, path: str, pattern: Optional[str], verbose: bool, timeout: int
    ) -> ToolResult:
        """Run Go tests."""
        cmd_parts = ["go", "test"]

        if verbose:
            cmd_parts.append("-v")

        if pattern:
            cmd_parts.extend(["-run", pattern])

        cmd_parts.append("./...")

        command = " ".join(cmd_parts)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8") if stdout else ""
            error = stderr.decode("utf-8") if stderr else ""

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output,
                error=error if not success else None,
                metadata={"framework": "go", "return_code": process.returncode},
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Tests timed out after {timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to run Go tests: {str(e)}"
            )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run tests using specified framework."""
        path = kwargs.get("path", ".")
        framework = kwargs.get("framework", "auto")
        pattern = kwargs.get("pattern")
        verbose = kwargs.get("verbose", False)
        timeout = kwargs.get("timeout", 300)

        # Auto-detect framework if needed
        if framework == "auto":
            framework = self._detect_test_framework(path)

        # Run tests based on framework
        if framework == "pytest":
            return await self._run_pytest(path, pattern, verbose, timeout)
        elif framework == "jest":
            return await self._run_jest(path, pattern, verbose, timeout)
        elif framework == "go":
            return await self._run_go_test(path, pattern, verbose, timeout)
        elif framework == "unittest":
            # Python unittest
            command = f"python -m unittest discover {path}"
            if verbose:
                command += " -v"

            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                output = stdout.decode("utf-8") if stdout else ""
                error = stderr.decode("utf-8") if stderr else ""

                return ToolResult(
                    success=process.returncode == 0,
                    output=output,
                    error=error if process.returncode != 0 else None,
                    metadata={
                        "framework": "unittest",
                        "return_code": process.returncode,
                    },
                )

            except Exception as e:
                return ToolResult(
                    success=False, output="", error=f"Failed to run unittest: {str(e)}"
                )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unsupported test framework: {framework}",
            )


class LintTool(Tool):
    """Tool for running code linters and formatters."""

    def __init__(self):
        self._definition = ToolDefinition(
            name="lint",
            description="Run code linters and formatters",
            parameters=[
                ToolParameter(
                    name="tool",
                    type="string",
                    description="Linting tool: 'flake8', 'black', 'eslint', 'prettier', 'auto'",
                    required=False,
                    default="auto",
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to code files or directory",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="fix",
                    type="boolean",
                    description="Automatically fix issues when possible",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="config",
                    type="string",
                    description="Config file path",
                    required=False,
                ),
            ],
        )
        super().__init__()

    @property
    def definition(self):
        return self._definition

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run linting tool."""

        tools_to_run = []
        if kwargs.get("tool") == "auto":
            tools_to_run = self._detect_lint_tool(kwargs.get("path", "."))
        else:
            tools_to_run = [kwargs.get("tool")]

        results = []

        for lint_tool in tools_to_run:
            try:
                if lint_tool == "flake8":
                    cmd = ["flake8", kwargs.get("path", ".")]
                    if kwargs.get("config"):
                        cmd.extend(["--config", kwargs.get("config")])

                elif lint_tool == "black":
                    cmd = ["black", kwargs.get("path", ".")]
                    if not kwargs.get("fix"):
                        cmd.append("--check")
                    if kwargs.get("config"):
                        cmd.extend(["--config", kwargs.get("config")])

                elif lint_tool == "eslint":
                    cmd = ["eslint", kwargs.get("path", ".")]
                    if kwargs.get("fix"):
                        cmd.append("--fix")
                    if kwargs.get("config"):
                        cmd.extend(["--config", kwargs.get("config")])

                elif lint_tool == "prettier":
                    cmd = ["prettier", kwargs.get("path", ".")]
                    if kwargs.get("fix"):
                        cmd.append("--write")
                    else:
                        cmd.append("--check")
                    if kwargs.get("config"):
                        cmd.extend(["--config", kwargs.get("config")])

                else:
                    results.append(f"Unsupported linting tool: {lint_tool}")
                    continue

                # Execute command
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()
                output = stdout.decode("utf-8") if stdout else ""
                error = stderr.decode("utf-8") if stderr else ""

                if process.returncode == 0:
                    results.append(f"{lint_tool}: ✓ No issues found")
                else:
                    results.append(f"{lint_tool}: Issues found\n{output}\n{error}")

            except FileNotFoundError:
                results.append(f"{lint_tool}: Tool not found. Please install it first.")
            except Exception as e:
                results.append(f"{lint_tool}: Error - {str(e)}")

        return ToolResult(
            success=True,
            output="\n\n".join(results),
            metadata={
                "tools_run": tools_to_run,
                "path": kwargs.get("path", "."),
                "fix_mode": kwargs.get("fix"),
                "config": kwargs.get("config"),
            },
        )


class CoverageTool(Tool):
    """Tool for measuring test coverage."""

    def __init__(self):
        self._definition = ToolDefinition(
            name="coverage",
            description="Measure and report test coverage",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to source code",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Report format: 'text', 'html', 'xml'",
                    required=False,
                    default="text",
                ),
                ToolParameter(
                    name="min_coverage",
                    type="number",
                    description="Minimum coverage percentage required",
                    required=False,
                    default=80,
                ),
            ],
        )
        super().__init__()

    @property
    def definition(self):
        return self._definition

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Measure test coverage."""
        try:
            # Run coverage with pytest
            cmd = [
                "python",
                "-m",
                "coverage",
                "run",
                "-m",
                "pytest",
                kwargs.get("path", "."),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            # Generate coverage report
            if kwargs.get("format") == "html":
                report_cmd = ["python", "-m", "coverage", "html"]
            elif kwargs.get("format") == "xml":
                report_cmd = ["python", "-m", "coverage", "xml"]
            else:
                report_cmd = ["python", "-m", "coverage", "report"]

            process = await asyncio.create_subprocess_exec(
                *report_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""
            error = stderr.decode("utf-8") if stderr else ""

            # Extract coverage percentage
            coverage_percent = 0
            for line in output.split("\n"):
                if "TOTAL" in line and "%" in line:
                    try:
                        coverage_percent = int(line.split()[-1].replace("%", ""))
                    except Exception:
                        pass

            success = coverage_percent >= kwargs.get("min_coverage", 80)

            return ToolResult(
                success=success,
                output=output,
                error=error if error else None,
                metadata={
                    "coverage_percent": coverage_percent,
                    "min_coverage": kwargs.get("min_coverage", 80),
                    "format": kwargs.get("format", "text"),
                },
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="Coverage tool not found. Install with: pip install coverage",
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Coverage measurement failed: {str(e)}"
            )
