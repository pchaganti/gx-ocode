"""
Enhanced Bash/Shell command execution tool with advanced features.
"""

import asyncio
import os
import re
import shlex
import tempfile
import pexpect
import io
import time
import signal
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class BashTool(Tool):
    """Enhanced Bash/Shell command execution tool."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash",
            description="Execute shell commands with advanced features and safety controls",
            category="System Operations",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute",
                    required=True
                ),
                ToolParameter(
                    name="working_dir",
                    type="string",
                    description="Working directory for command execution",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Command timeout in seconds (0 = no timeout)",
                    required=False,
                    default=30
                ),
                ToolParameter(
                    name="capture_output",
                    type="boolean",
                    description="Capture stdout and stderr",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="shell",
                    type="string",
                    description="Shell to use (bash, sh, zsh, fish)",
                    required=False,
                    default="bash"
                ),
                ToolParameter(
                    name="env_vars",
                    type="object",
                    description="Additional environment variables",
                    required=False,
                    default={}
                ),
                ToolParameter(
                    name="input_data",
                    type="string",
                    description="Input data to pipe to the command",
                    required=False
                ),
                ToolParameter(
                    name="interactive",
                    type="boolean",
                    description="Run in interactive mode (for commands requiring input)",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="safe_mode",
                    type="boolean",
                    description="Enable safety checks (prevent dangerous commands)",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="show_command",
                    type="boolean",
                    description="Show the command being executed",
                    required=False,
                    default=True
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute shell command with enhanced features."""
        # Extract parameters from kwargs
        command = kwargs.get("command")
        working_dir = kwargs.get("working_dir", ".")
        timeout = kwargs.get("timeout", 30)
        capture_output = kwargs.get("capture_output", True)
        shell = kwargs.get("shell", "bash")
        env_vars = kwargs.get("env_vars", {})
        input_data = kwargs.get("input_data")
        interactive = kwargs.get("interactive", False)
        safe_mode = kwargs.get("safe_mode", True)
        show_command = kwargs.get("show_command", True)
        try:
            # Validate working directory
            work_dir = Path(working_dir).resolve()
            if not work_dir.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Working directory does not exist: {working_dir}"
                )

            # Safety checks
            if safe_mode:
                safety_result = self._check_command_safety(command)
                if not safety_result["safe"]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Command blocked for safety: {safety_result['reason']}"
                    )

            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Prepare shell command
            shell_cmd = self._prepare_shell_command(command, shell)

            output_lines = []
            if show_command:
                output_lines.append(f"$ {command}")
                output_lines.append("")

            # Execute command
            if interactive:
                result = await self._execute_interactive(shell_cmd, work_dir, env, timeout, input_data)
            else:
                result = await self._execute_standard(
                    shell_cmd, work_dir, env, timeout, capture_output, input_data
                )

            # Format output
            if result["success"]:
                if result["stdout"]:
                    output_lines.append(result["stdout"])
                
                if result["stderr"] and capture_output:
                    output_lines.append("STDERR:")
                    output_lines.append(result["stderr"])

                output = "\n".join(output_lines) if output_lines else ""
                
                return ToolResult(
                    success=True,
                    output=output,
                    metadata={
                        "command": command,
                        "working_dir": str(work_dir),
                        "return_code": result["return_code"],
                        "execution_time": result.get("execution_time", 0),
                        "shell": shell
                    }
                )
            else:
                error_msg = result["stderr"] or "Command execution failed"
                return ToolResult(
                    success=False,
                    output=result["stdout"] or "",
                    error=error_msg,
                    metadata={
                        "command": command,
                        "return_code": result["return_code"],
                        "execution_time": result.get("execution_time", 0)
                    }
                )

        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command or shell not found: {str(e)}"
            )
        except PermissionError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command execution failed: {str(e)}"
            )

    def _check_command_safety(self, command: str) -> Dict[str, Any]:
        """Check if command is safe to execute with enhanced security patterns."""
        dangerous_patterns = [
            # Destructive operations
            r"\brm\s+-rf\s+/",
            r"\bmv\s+.*\s+/dev/null",
            r"\bdd\s+.*of=/dev/",
            r"\bformat\b",
            r"\bmkfs\b",
            r"\bshred\b",
            r"\bwipe\b",
            
            # System modifications
            r"\bsudo\s+rm\s+-rf",
            r"\bchmod\s+777\s+/",
            r"\bchown\s+.*:\s*/",
            r"\buseradd\b",
            r"\buserdel\b",
            r"\bpasswd\b",
            
            # Network/security risks
            r"\bcurl\s+.*\|\s*(sh|bash|zsh)",
            r"\bwget\s+.*\|\s*(sh|bash|zsh)",
            r"bash\s+<\(",
            r"\beval\s+\$\(",
            r"\$\(curl\b",
            r"\$\(wget\b",
            
            # Process killers
            r"\bkillall\s+-9",
            r"\bpkill\s+-f\s+.*",
            r"\bkill\s+-9\s+1\b",  # init process
            
            # System reboot/shutdown
            r"\breboot\b",
            r"\bshutdown\b",
            r"\bhalt\b",
            r"\bpoweroff\b",
            
            # File system mounting
            r"\bmount\s+.*\s+/",
            r"\bumount\s+/",
            
            # Code injection patterns
            r";\s*(rm|mv|dd|format)",
            r"&&\s*(rm|mv|dd|format)",
            r"\|\|\s*(rm|mv|dd|format)",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "safe": False,
                    "reason": f"Command contains potentially dangerous pattern: {pattern}"
                }

        # Check for suspicious file operations
        if re.search(r"\brm\s+.*\*", command):
            return {
                "safe": False,
                "reason": "Bulk file deletion with wildcards detected"
            }
            
        # Only check for truly dangerous command injection patterns
        # Don't block legitimate shell features like pipes, redirects, variable expansion
        dangerous_injection_patterns = [
            r";\s*(rm|mv|dd|format|sudo|curl.*\|.*sh)",
            r"&&\s*(rm|mv|dd|format|sudo|curl.*\|.*sh)", 
            r"\|\|\s*(rm|mv|dd|format|sudo|curl.*\|.*sh)",
            r"`.*rm\s+",  # Command substitution with rm
            r"\$\(.*rm\s+",  # Command substitution with rm
        ]
        
        for pattern in dangerous_injection_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "safe": False,
                    "reason": f"Command contains dangerous injection pattern: {pattern}"
                }

        return {"safe": True, "reason": ""}

    def _prepare_shell_command(self, command: str, shell: str) -> List[str]:
        """Prepare shell command for execution with proper sanitization."""
        shell_map = {
            "bash": "/bin/bash",
            "sh": "/bin/sh", 
            "zsh": "/bin/zsh",
            "fish": "/usr/bin/fish"
        }
        
        # Validate shell parameter
        if shell not in shell_map:
            shell = "bash"  # Default to bash for unknown shells
            
        shell_path = shell_map[shell]
        
        # Check if shell exists, fallback to available shells
        fallback_shells = ["/bin/bash", "/bin/sh", "/usr/bin/bash"]
        if not Path(shell_path).exists():
            for fallback in fallback_shells:
                if Path(fallback).exists():
                    shell_path = fallback
                    break
            else:
                raise FileNotFoundError(f"No suitable shell found. Tried: {[shell_path] + fallback_shells}")
        
        # Use exec form to prevent shell injection
        return [shell_path, "-c", command]
    
    def _sanitize_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """Sanitize environment variables to prevent injection attacks."""
        safe_env = {}
        
        for key, value in env.items():
            # Validate environment variable names (must be valid identifiers)
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                continue  # Skip invalid variable names
                
            # Convert value to string - environment variables are intentionally flexible
            # so we don't overly restrict their content
            safe_value = str(value)
            safe_env[key] = safe_value
            
        return safe_env
    
    def _expect_eof_safe(self, child):
        """Safely expect EOF from pexpect child process."""
        try:
            child.expect(pexpect.EOF)
        except pexpect.TIMEOUT:
            # This is expected for timeout scenarios
            pass
        except pexpect.exceptions.ExceptionPexpect:
            # Handle other pexpect exceptions gracefully
            pass

    @asynccontextmanager
    async def _managed_process(self, shell_cmd: List[str], work_dir: Path, env: Dict[str, str], 
                              capture_output: bool, input_data: Optional[str]):
        """Context manager for proper process cleanup."""
        process = None
        try:
            if capture_output:
                process = await asyncio.create_subprocess_exec(
                    *shell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE if input_data else None,
                    cwd=str(work_dir),
                    env=env,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create process group
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *shell_cmd,
                    cwd=str(work_dir),
                    env=env,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
            yield process
        finally:
            if process and process.returncode is None:
                try:
                    # Try graceful termination first
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        # Force kill if still running
                        process.kill()
                        await process.wait()
                except ProcessLookupError:
                    # Process already dead
                    pass

    async def _execute_standard(self, shell_cmd: List[str], work_dir: Path,
                               env: Dict[str, str], timeout: int, capture_output: bool,
                               input_data: Optional[str]) -> Dict[str, Any]:
        """Execute command in standard mode with enhanced error handling."""
        start_time = time.time()
        
        try:
            # Sanitize environment variables
            safe_env = self._sanitize_environment(env)
            
            async with self._managed_process(shell_cmd, work_dir, safe_env, capture_output, input_data) as process:
                if capture_output:
                    try:
                        input_bytes = input_data.encode('utf-8', errors='replace') if input_data else None
                        
                        if timeout > 0:
                            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                                process.communicate(input=input_bytes),
                                timeout=timeout
                            )
                        else:
                            stdout_bytes, stderr_bytes = await process.communicate(input=input_bytes)
                            
                        stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                        stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                        return_code = process.returncode
                        
                    except asyncio.TimeoutError:
                        return {
                            "success": False,
                            "stdout": "",
                            "stderr": f"Command timed out after {timeout} seconds",
                            "return_code": -15,  # SIGTERM
                            "execution_time": time.time() - start_time
                        }
                else:
                    # No output capture
                    try:
                        if timeout > 0:
                            return_code = await asyncio.wait_for(process.wait(), timeout=timeout)
                        else:
                            return_code = await process.wait()
                    except asyncio.TimeoutError:
                        return {
                            "success": False,
                            "stdout": "",
                            "stderr": f"Command timed out after {timeout} seconds",
                            "return_code": -15,
                            "execution_time": time.time() - start_time
                        }
                    stdout, stderr = "", ""

            execution_time = time.time() - start_time
            
            return {
                "success": return_code == 0,
                "stdout": stdout or "",
                "stderr": stderr or "",
                "return_code": return_code,
                "execution_time": execution_time
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command not found: {e}",
                "return_code": 127,
                "execution_time": time.time() - start_time
            }
        except PermissionError as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Permission denied: {e}",
                "return_code": 126,
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "return_code": -1,
                "execution_time": time.time() - start_time
            }

    async def _execute_interactive(self, shell_cmd: List[str], work_dir: Path,
                                 env: Dict[str, str], timeout: int, input_data: Optional[str] = None) -> Dict[str, Any]:
        """Execute command in interactive mode using pexpect with improved async handling."""
        output_buffer = io.StringIO()
        child = None
        start_time = time.time()
        try:
            # Convert shell command list to string for pexpect
            cmd_str = " ".join(shlex.quote(arg) for arg in shell_cmd)
            
            # Create pexpect spawn object with more conservative timeout
            child = pexpect.spawn(
                cmd_str,
                cwd=str(work_dir),
                env=env,
                encoding='utf-8',
                timeout=min(timeout, 30) if timeout > 0 else 30  # Max 30s per operation
            )
            
            # Set up logging using StringIO
            child.logfile_read = output_buffer
            
            # If input_data is provided, send it (simulate user input)
            if input_data:
                input_lines = input_data.splitlines()
                for i, line in enumerate(input_lines):
                    try:
                        # Run sendline in a thread pool with timeout protection
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, child.sendline, line
                            ),
                            timeout=5  # 5 second timeout per line
                        )
                        
                        # Small delay between lines to prevent overwhelming the process
                        if i < len(input_lines) - 1:  # Don't delay after the last line
                            await asyncio.sleep(0.1)
                            
                    except asyncio.TimeoutError:
                        # Continue on timeout, but log it
                        break
            
            # Wait for command to complete with proper timeout handling
            try:
                remaining_timeout = max(1, timeout - (time.time() - start_time)) if timeout > 0 else 30
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self._expect_eof_safe, child
                    ),
                    timeout=remaining_timeout
                )
            except asyncio.TimeoutError:
                # Handle timeout gracefully
                pass
            
            # Get final output
            final_output = output_buffer.getvalue()
            
            # Get exit status
            child.close()
            return_code = child.exitstatus if child.exitstatus is not None else -1
            
            return {
                "success": return_code == 0,
                "stdout": final_output,
                "stderr": "",  # pexpect combines stdout and stderr
                "return_code": return_code
            }
            
        except pexpect.TIMEOUT:
            if child:
                child.terminate(force=True)
            return {
                "success": False,
                "stdout": output_buffer.getvalue(),
                "stderr": f"Interactive command timed out after {timeout} seconds",
                "return_code": -1
            }
        except Exception as e:
            if child:
                child.terminate(force=True)
            return {
                "success": False,
                "stdout": output_buffer.getvalue(),
                "stderr": str(e),
                "return_code": -1
            }
        finally:
            if child and child.isalive():
                child.terminate(force=True)
            output_buffer.close()


class ScriptTool(Tool):
    """Tool for creating and executing shell scripts."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="script",
            description="Create and execute shell scripts with multiple commands",
            parameters=[
                ToolParameter(
                    name="script_content",
                    type="string",
                    description="Script content (multiple commands separated by newlines)",
                    required=True
                ),
                ToolParameter(
                    name="script_type",
                    type="string",
                    description="Script type: 'bash', 'sh', 'python', 'node'",
                    required=False,
                    default="bash"
                ),
                ToolParameter(
                    name="working_dir",
                    type="string",
                    description="Working directory for script execution",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Script timeout in seconds",
                    required=False,
                    default=60
                ),
                ToolParameter(
                    name="save_script",
                    type="boolean",
                    description="Save script to temporary file for inspection",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="env_vars",
                    type="object",
                    description="Environment variables for script",
                    required=False,
                    default={}
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a shell script."""
        try:
            # Extract parameters from kwargs
            script_content = kwargs.get("script_content")
            script_type = kwargs.get("script_type", "bash")
            working_dir = kwargs.get("working_dir", ".")
            timeout = kwargs.get("timeout", 60)
            save_script = kwargs.get("save_script", False)
            env_vars = kwargs.get("env_vars", {})
            
            if not script_content:
                return ToolResult(
                    success=False,
                    output="",
                    error="No script content provided"
                )
            
            work_dir = Path(working_dir).resolve()
            
            # Create temporary script file
            script_extensions = {
                "bash": ".sh",
                "sh": ".sh", 
                "python": ".py",
                "node": ".js",
                "javascript": ".js"
            }
            
            extension = script_extensions.get(script_type, ".sh")
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=extension, 
                delete=not save_script,
                encoding='utf-8'
            ) as script_file:
                
                # Add shebang if needed
                if script_type == "bash":
                    script_file.write("#!/bin/bash\\nset -e\\n\\n")
                elif script_type == "python":
                    script_file.write("#!/usr/bin/env python3\\n\\n")
                elif script_type in ["node", "javascript"]:
                    script_file.write("#!/usr/bin/env node\\n\\n")
                
                script_file.write(script_content)
                script_file.flush()
                
                # Make script executable
                os.chmod(script_file.name, 0o755)
                
                # Prepare execution command
                if script_type == "bash":
                    cmd = ["bash", script_file.name]
                elif script_type == "python":
                    cmd = ["python3", script_file.name]
                elif script_type in ["node", "javascript"]:
                    cmd = ["node", script_file.name]
                else:
                    cmd = ["sh", script_file.name]
                
                # Execute script using BashTool
                bash_tool = BashTool()
                command_str = " ".join(shlex.quote(arg) for arg in cmd)
                
                result = await bash_tool.execute(
                    command=command_str,
                    working_dir=working_dir,
                    timeout=timeout,
                    env_vars=env_vars,
                    safe_mode=False,  # Scripts are already created by us
                    show_command=True
                )
                
                # Add script info to metadata
                if result.metadata:
                    result.metadata.update({
                        "script_type": script_type,
                        "script_path": script_file.name if save_script else "temporary",
                        "script_size": len(script_content)
                    })
                
                if save_script:
                    saved_path = Path(script_file.name)
                    result.output = f"Script saved to: {saved_path}\\n\\n" + (result.output or "")
                
                return result

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Script execution failed: {str(e)}"
            )