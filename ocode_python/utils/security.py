"""
Security and permission management for OCode.
"""

import os
import re
import subprocess  # nosec B404 - Required for security manager command validation
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PermissionLevel(Enum):
    """Permission levels for operations."""

    DENIED = "denied"
    READ_ONLY = "read_only"
    RESTRICTED = "restricted"
    FULL = "full"


class OperationType(Enum):
    """Types of operations that can be controlled."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_EXEC = "shell_exec"
    GIT_OPERATION = "git_operation"
    NETWORK_ACCESS = "network_access"
    ENVIRONMENT_READ = "environment_read"
    ENVIRONMENT_WRITE = "environment_write"


@dataclass
class PermissionRule:
    """Represents a permission rule."""

    operation: OperationType
    pattern: str  # Path pattern or command pattern
    permission: PermissionLevel
    description: str

    def matches(self, target: str) -> bool:
        """Check if this rule matches the target.

        Uses fnmatch for glob-style pattern matching.

        Args:
            target: Path or command to match against.

        Returns:
            True if the pattern matches the target.
        """
        # Support glob-style patterns
        import fnmatch

        return fnmatch.fnmatch(target, self.pattern)


class PermissionManager:
    """
    Manages permissions and security policies for OCode operations.

    Implements a whitelist-first security model with configurable rules.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize permission manager.

        Args:
            config_path: Path to security configuration file
        """
        self.config_path = config_path
        self.rules: List[PermissionRule] = []
        self.blocked_paths: Set[str] = set()
        self.allowed_paths: Set[str] = set()
        self.blocked_commands: Set[str] = set()
        self.allowed_commands: Set[str] = set()

        # Security callbacks for custom validation
        self.validators: Dict[OperationType, List[Callable]] = {}

        # Load default security rules
        self._load_default_rules()

        # Load configuration if provided
        if config_path and config_path.exists():
            self._load_config(config_path)

    def _load_default_rules(self):
        """Load default security rules.

        Sets up default blocked paths, dangerous commands, and
        safe commands with appropriate permission levels.
        """
        # Default blocked paths (high-security system directories)
        default_blocked = [
            "/etc/*",
            "/bin/*",
            "/sbin/*",
            "/usr/bin/*",
            "/usr/sbin/*",
            "/boot/*",
            "/sys/*",
            "/proc/*",
            "/dev/*",
            "C:\\Windows\\*",
            "C:\\Program Files\\*",
            "C:\\Program Files (x86)\\*",
        ]

        for pattern in default_blocked:
            self.blocked_paths.add(pattern)
            self.add_rule(
                PermissionRule(
                    operation=OperationType.FILE_WRITE,
                    pattern=pattern,
                    permission=PermissionLevel.DENIED,
                    description=f"Block writes to system directory: {pattern}",
                )
            )

            self.add_rule(
                PermissionRule(
                    operation=OperationType.FILE_DELETE,
                    pattern=pattern,
                    permission=PermissionLevel.DENIED,
                    description=f"Block deletes in system directory: {pattern}",
                )
            )

        # Default blocked commands
        dangerous_commands = [
            "rm",
            "rmdir",
            "del",
            "format",
            "fdisk",
            "mkfs",
            "sudo",
            "su",
            "passwd",
            "useradd",
            "userdel",
            "kill",
            "killall",
            "pkill",
            "taskkill",
            "chmod",
            "chown",
            "icacls",
            "takeown",
            "dd",
            "mount",
            "umount",
        ]

        for cmd in dangerous_commands:
            self.blocked_commands.add(cmd)
            self.add_rule(
                PermissionRule(
                    operation=OperationType.SHELL_EXEC,
                    pattern=f"{cmd}*",
                    permission=PermissionLevel.DENIED,
                    description=f"Block dangerous command: {cmd}",
                )
            )

        # Allow common safe commands
        safe_commands = [
            "ls",
            "dir",
            "cat",
            "type",
            "echo",
            "pwd",
            "cd",
            "grep",
            "find",
            "head",
            "tail",
            "wc",
            "sort",
            "python*",
            "pip*",
            "npm*",
            "node*",
            "git*",
            "curl",
            "wget",
            "test",
            "pytest",
            "sleep",
        ]

        for cmd in safe_commands:
            self.allowed_commands.add(cmd)
            self.add_rule(
                PermissionRule(
                    operation=OperationType.SHELL_EXEC,
                    pattern=f"{cmd}*",
                    permission=PermissionLevel.RESTRICTED,
                    description=f"Allow safe command: {cmd}",
                )
            )

        # Default file access rules
        self.add_rule(
            PermissionRule(
                operation=OperationType.FILE_READ,
                pattern="*",
                permission=PermissionLevel.READ_ONLY,
                description="Default read access to all files",
            )
        )

        # Git operations are generally safe
        self.add_rule(
            PermissionRule(
                operation=OperationType.GIT_OPERATION,
                pattern="*",
                permission=PermissionLevel.RESTRICTED,
                description="Allow git operations with restrictions",
            )
        )

    def _load_config(self, config_path: Path):
        """Load configuration from file.

        Loads custom security rules and path/command restrictions
        from a JSON configuration file.

        Args:
            config_path: Path to the security configuration file.
        """
        try:
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

            # Load custom rules
            if "rules" in config:
                for rule_data in config["rules"]:
                    rule = PermissionRule(
                        operation=OperationType(rule_data["operation"]),
                        pattern=rule_data["pattern"],
                        permission=PermissionLevel(rule_data["permission"]),
                        description=rule_data.get("description", ""),
                    )
                    self.add_rule(rule)

            # Load path restrictions
            if "blocked_paths" in config:
                self.blocked_paths.update(config["blocked_paths"])

            if "allowed_paths" in config:
                self.allowed_paths.update(config["allowed_paths"])

            # Load command restrictions
            if "blocked_commands" in config:
                self.blocked_commands.update(config["blocked_commands"])

            if "allowed_commands" in config:
                self.allowed_commands.update(config["allowed_commands"])

        except Exception as e:
            print(f"Warning: Failed to load security config: {e}")

    def add_rule(self, rule: PermissionRule):
        """Add a permission rule.

        Args:
            rule: PermissionRule to add to the security policy.
        """
        self.rules.append(rule)

    def add_validator(self, operation: OperationType, validator: Callable[[str], bool]):
        """Add a custom validator for an operation type.

        Custom validators are called before rule-based checks.

        Args:
            operation: Operation type to validate.
            validator: Function that returns True if operation is allowed.
        """
        if operation not in self.validators:
            self.validators[operation] = []
        self.validators[operation].append(validator)

    def check_permission(
        self, operation: OperationType, target: str
    ) -> PermissionLevel:
        """
        Check permission for an operation on a target.

        Args:
            operation: Type of operation
            target: Target path, command, or resource

        Returns:
            Permission level for the operation
        """
        # Run custom validators first
        if operation in self.validators:
            for validator in self.validators[operation]:
                if not validator(target):
                    return PermissionLevel.DENIED

        # Check explicit blocks/allows first
        if operation in [
            OperationType.FILE_READ,
            OperationType.FILE_WRITE,
            OperationType.FILE_DELETE,
        ]:
            if self._is_path_blocked(target):
                return PermissionLevel.DENIED
            if self.allowed_paths and not self._is_path_allowed(target):
                return PermissionLevel.DENIED

        elif operation == OperationType.SHELL_EXEC:
            command = target.split()[0] if target else ""
            if command in self.blocked_commands:
                return PermissionLevel.DENIED

        # Check rules (most specific first)
        matching_rules = [
            rule
            for rule in self.rules
            if rule.operation == operation and rule.matches(target)
        ]

        if matching_rules:
            # Return the most restrictive permission from matching rules
            permissions = [rule.permission for rule in matching_rules]

            if PermissionLevel.DENIED in permissions:
                return PermissionLevel.DENIED
            elif PermissionLevel.READ_ONLY in permissions:
                return PermissionLevel.READ_ONLY
            elif PermissionLevel.RESTRICTED in permissions:
                return PermissionLevel.RESTRICTED
            else:
                return PermissionLevel.FULL

        # Default to restricted access
        return PermissionLevel.RESTRICTED

    def _is_path_blocked(self, path: str) -> bool:
        """Check if path is explicitly blocked.

        Args:
            path: Path to check.

        Returns:
            True if path matches any blocked pattern.
        """
        import fnmatch

        abs_path = os.path.abspath(path)

        for blocked_pattern in self.blocked_paths:
            if fnmatch.fnmatch(abs_path, blocked_pattern):
                return True

        return False

    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is explicitly allowed.

        Args:
            path: Path to check.

        Returns:
            True if path matches any allowed pattern.
        """
        import fnmatch

        abs_path = os.path.abspath(path)

        for allowed_pattern in self.allowed_paths:
            if fnmatch.fnmatch(abs_path, allowed_pattern):
                return True

        return False

    def can_read_file(self, file_path: str) -> bool:
        """Check if file can be read.

        Args:
            file_path: Path to the file.

        Returns:
            True if read access is allowed.
        """
        permission = self.check_permission(OperationType.FILE_READ, file_path)
        return permission != PermissionLevel.DENIED

    def can_write_file(self, file_path: str) -> bool:
        """Check if file can be written.

        Args:
            file_path: Path to the file.

        Returns:
            True if write access is allowed.
        """
        permission = self.check_permission(OperationType.FILE_WRITE, file_path)
        return permission in [PermissionLevel.RESTRICTED, PermissionLevel.FULL]

    def can_delete_file(self, file_path: str) -> bool:
        """Check if file can be deleted.

        Args:
            file_path: Path to the file.

        Returns:
            True if delete access is allowed (requires FULL permission).
        """
        permission = self.check_permission(OperationType.FILE_DELETE, file_path)
        return permission == PermissionLevel.FULL

    def can_execute_command(self, command: str) -> bool:
        """Check if command can be executed.

        Args:
            command: Command string to check.

        Returns:
            True if command execution is allowed.
        """
        permission = self.check_permission(OperationType.SHELL_EXEC, command)
        return permission != PermissionLevel.DENIED

    def sanitize_command(self, command: str) -> Optional[str]:
        """
        Sanitize a command for safe execution.

        Args:
            command: Command to sanitize

        Returns:
            Sanitized command or None if command is not safe
        """
        if not self.can_execute_command(command):
            return None

        # Remove dangerous operators and characters
        dangerous_patterns = [
            r"[;&|`$()]",  # Command injection characters
            r">\s*/",  # Redirect to root paths
            r">.*etc",  # Redirect to etc directory
            r"rm\s+-rf",  # Dangerous rm flags
            r"sudo",  # Sudo commands
            r"su\s",  # Switch user
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return None

        return command

    def get_safe_environment(self) -> Dict[str, str]:
        """Get sanitized environment variables.

        Only includes a whitelist of safe environment variables
        to prevent information leakage.

        Returns:
            Dictionary of safe environment variables.
        """
        safe_env = {}

        # Only include safe environment variables
        safe_vars = {
            "PATH",
            "HOME",
            "USER",
            "SHELL",
            "LANG",
            "LC_ALL",
            "PYTHONPATH",
            "NODE_PATH",
            "GOPATH",
            "JAVA_HOME",
            "OCODE_MODEL",
            "OLLAMA_HOST",
        }

        for var in safe_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        return safe_env

    def create_sandbox_config(self, allowed_paths: List[str]) -> Dict[str, Any]:
        """
        Create sandbox configuration for restricted execution.

        Args:
            allowed_paths: List of paths to allow access to

        Returns:
            Sandbox configuration dictionary
        """
        return {
            "allowed_paths": allowed_paths,
            "blocked_paths": list(self.blocked_paths),
            "allowed_commands": list(self.allowed_commands),
            "blocked_commands": list(self.blocked_commands),
            "environment": self.get_safe_environment(),
            "network_access": False,
            "max_execution_time": 300,  # 5 minutes
            "max_memory": 512 * 1024 * 1024,  # 512MB
        }

    def validate_file_operation(
        self, operation: str, file_path: str
    ) -> Tuple[bool, str]:
        """
        Validate a file operation.

        Args:
            operation: Operation type ("read", "write", "delete")
            file_path: Target file path

        Returns:
            (is_allowed, reason)
        """
        try:
            abs_path = os.path.abspath(file_path)

            # Check if path exists and is accessible
            if operation == "read":
                if not os.path.exists(abs_path):
                    return False, f"File does not exist: {file_path}"
                if not os.access(abs_path, os.R_OK):
                    return False, f"No read permission: {file_path}"
                if not self.can_read_file(abs_path):
                    return False, f"Read access denied by security policy: {file_path}"

            elif operation == "write":
                # Check parent directory for new files
                parent_dir = os.path.dirname(abs_path)
                if not os.path.exists(parent_dir):
                    return False, f"Parent directory does not exist: {parent_dir}"
                if not os.access(parent_dir, os.W_OK):
                    return False, f"No write permission in directory: {parent_dir}"
                if not self.can_write_file(abs_path):
                    return False, f"Write access denied by security policy: {file_path}"

            elif operation == "delete":
                if not os.path.exists(abs_path):
                    return False, f"File does not exist: {file_path}"
                if not os.access(abs_path, os.W_OK):
                    return False, f"No delete permission: {file_path}"
                if not self.can_delete_file(abs_path):
                    return (
                        False,
                        f"Delete access denied by security policy: {file_path}",
                    )

            return True, "Operation allowed"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def export_policy(self, output_path: Path):
        """Export current security policy to file.

        Exports all rules and restrictions to a JSON file for
        backup or sharing.

        Args:
            output_path: Path where the policy JSON will be written.
        """
        policy = {
            "rules": [
                {
                    "operation": rule.operation.value,
                    "pattern": rule.pattern,
                    "permission": rule.permission.value,
                    "description": rule.description,
                }
                for rule in self.rules
            ],
            "blocked_paths": list(self.blocked_paths),
            "allowed_paths": list(self.allowed_paths),
            "blocked_commands": list(self.blocked_commands),
            "allowed_commands": list(self.allowed_commands),
        }

        import json

        with open(output_path, "w") as f:
            json.dump(policy, f, indent=2)


class SecureShellExecutor:
    """Secure shell command executor with sandboxing."""

    def __init__(self, permission_manager: PermissionManager):
        """Initialize secure shell executor.

        Args:
            permission_manager: PermissionManager instance for security checks.
        """
        self.permission_manager = permission_manager

    async def execute(
        self, command: str, working_dir: Optional[str] = None, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """
        Execute command securely.

        Args:
            command: Command to execute
            working_dir: Working directory
            timeout: Execution timeout

        Returns:
            (success, stdout, stderr)
        """
        # Sanitize command
        safe_command = self.permission_manager.sanitize_command(command)
        if not safe_command:
            return False, "", "Command blocked by security policy"

        # Validate working directory
        if working_dir:
            allowed, reason = self.permission_manager.validate_file_operation(
                "read", working_dir
            )
            if not allowed:
                return False, "", f"Working directory access denied: {reason}"

        try:
            # Get safe environment
            env = self.permission_manager.get_safe_environment()

            # Execute with restrictions
            process = subprocess.Popen(
                safe_command,
                shell=True,  # nosec B602 - command is sanitized above
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                success = process.returncode == 0
                return success, stdout, stderr

            except subprocess.TimeoutExpired:
                process.kill()
                return False, "", f"Command timed out after {timeout} seconds"

        except Exception as e:
            return False, "", f"Execution error: {str(e)}"


def main():
    """Example usage of security system.

    Demonstrates permission checking for various file operations
    and command executions.
    """
    manager = PermissionManager()

    # Test file operations
    test_files = [
        "/tmp/test.txt",  # nosec B108
        "/etc/passwd",
        "~/documents/myfile.py",
        "project/src/main.py",
    ]

    for file_path in test_files:
        print(f"\nFile: {file_path}")
        print(f"  Read: {manager.can_read_file(file_path)}")
        print(f"  Write: {manager.can_write_file(file_path)}")
        print(f"  Delete: {manager.can_delete_file(file_path)}")

    # Test commands
    test_commands = [
        "ls -la",
        "rm -rf /",
        "python script.py",
        "sudo apt install",
        "git status",
    ]

    print("\nCommands:")
    for command in test_commands:
        can_execute = manager.can_execute_command(command)
        sanitized = manager.sanitize_command(command)
        print(f"  {command}: {can_execute} -> {sanitized}")


if __name__ == "__main__":
    main()
