"""
Git integration tools.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Any, List, Optional

from git import InvalidGitRepositoryError, Repo

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class GitStatusTool(Tool):
    """Tool for checking git repository status."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_status",
            description="Get the current git repository status",
            category="Git Operations",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Repository path (default: current directory)",
                    required=False,
                    default=".",
                )
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:  # type: ignore[override]
        """Get git status."""
        path = kwargs.get("path", ".")
        try:
            repo = Repo(path, search_parent_directories=True)

            # Get basic info
            branch = repo.active_branch.name
            commit = repo.head.commit.hexsha[:8]

            # Get file status
            modified_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            untracked_files = repo.untracked_files

            # Build status report
            status_lines = [f"Branch: {branch}", f"Commit: {commit}", ""]

            if staged_files:
                status_lines.append("Staged files:")
                status_lines.extend(f"  {file}" for file in staged_files)
                status_lines.append("")

            if modified_files:
                status_lines.append("Modified files:")
                status_lines.extend(f"  {file}" for file in modified_files)
                status_lines.append("")

            if untracked_files:
                status_lines.append("Untracked files:")
                status_lines.extend(f"  {file}" for file in untracked_files)
                status_lines.append("")

            if not staged_files and not modified_files and not untracked_files:
                status_lines.append("Working directory clean")

            return ToolResult(
                success=True,
                output="\n".join(status_lines).strip(),
                metadata={
                    "branch": branch,
                    "commit": commit,
                    "staged_count": len(staged_files),
                    "modified_count": len(modified_files),
                    "untracked_count": len(untracked_files),
                },
            )

        except InvalidGitRepositoryError:
            return ToolResult(success=False, output="", error="Not a git repository")
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Git status failed: {str(e)}"
            )


class GitCommitTool(Tool):
    """Tool for creating git commits."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_commit",
            description="Create a git commit with specified message",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Commit message",
                    required=True,
                ),
                ToolParameter(
                    name="files",
                    type="array",
                    description="Files to add to commit (default: all modified files)",
                    required=False,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Repository path (default: current directory)",
                    required=False,
                    default=".",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Create git commit."""
        path = kwargs.get("path", ".")
        message = kwargs.get("message")
        files = kwargs.get("files")
        try:
            repo = Repo(path, search_parent_directories=True)

            # Add files to staging
            if files:
                # Add specific files
                for file in files:
                    repo.index.add([file])
            else:
                # Add all modified and untracked files
                modified_files = [item.a_path for item in repo.index.diff(None)]
                untracked_files = repo.untracked_files

                all_files = modified_files + untracked_files
                if all_files:
                    repo.index.add(all_files)

            # Check if there are changes to commit
            if not repo.index.diff("HEAD"):
                return ToolResult(
                    success=False, output="", error="No changes to commit"
                )

            # Create commit
            commit = repo.index.commit(message)

            return ToolResult(
                success=True,
                output=f"Created commit {commit.hexsha[:8]}: {message}",
                metadata={
                    "commit_hash": commit.hexsha,
                    "message": message,
                    "files_changed": len(commit.stats.files),
                },
            )

        except InvalidGitRepositoryError:
            return ToolResult(success=False, output="", error="Not a git repository")
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Git commit failed: {str(e)}"
            )


class GitDiffTool(Tool):
    """Tool for showing git diffs."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_diff",
            description="Show git diff for files or commits",
            parameters=[
                ToolParameter(
                    name="file",
                    type="string",
                    description="Specific file to show diff for",
                    required=False,
                ),
                ToolParameter(
                    name="staged",
                    type="boolean",
                    description="Show staged changes instead of working directory",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="commit",
                    type="string",
                    description="Compare against specific commit",
                    required=False,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Repository path (default: current directory)",
                    required=False,
                    default=".",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Show git diff."""
        path = kwargs.get("path", ".")
        staged = kwargs.get("staged", False)
        commit = kwargs.get("commit")
        file = kwargs.get("file")
        try:
            repo = Repo(path, search_parent_directories=True)

            # Determine what to diff against
            if staged:
                # Staged changes vs HEAD
                diff = repo.index.diff("HEAD")
            elif commit:
                # Working directory vs specific commit
                diff = repo.head.commit.diff(commit)
            else:
                # Working directory vs index
                diff = repo.index.diff(None)

            # Filter by file if specified
            if file:
                diff = [d for d in diff if d.a_path == file or d.b_path == file]

            if not diff:
                return ToolResult(
                    success=True, output="No differences found", metadata={"changes": 0}
                )

            # Format diff output
            diff_lines = []
            for change in diff:
                diff_lines.append(f"diff --git a/{change.a_path} b/{change.b_path}")

                if change.change_type == "A":
                    diff_lines.append("new file")
                elif change.change_type == "D":
                    diff_lines.append("deleted file")
                elif change.change_type == "M":
                    diff_lines.append("modified file")
                elif change.change_type == "R":
                    diff_lines.append(f"renamed from {change.a_path}")

                # Show actual diff content
                try:
                    diff_text = change.diff.decode("utf-8")
                    diff_lines.append(diff_text)
                except Exception:
                    diff_lines.append("(binary file)")

                diff_lines.append("")

            return ToolResult(
                success=True,
                output="\n".join(diff_lines).strip(),
                metadata={
                    "changes": len(diff),
                    "files": [change.a_path for change in diff],
                },
            )

        except InvalidGitRepositoryError:
            return ToolResult(success=False, output="", error="Not a git repository")
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Git diff failed: {str(e)}"
            )


class GitBranchTool(Tool):
    """Tool for git branch operations."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_branch",
            description="Manage git branches",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: 'list', 'create', 'checkout', 'delete'",
                    required=True,
                ),
                ToolParameter(
                    name="branch_name",
                    type="string",
                    description="Branch name (required for create/checkout/delete)",
                    required=False,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Repository path (default: current directory)",
                    required=False,
                    default=".",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Manage git branches."""
        path = kwargs.get("path", ".")
        action = kwargs.get("action")
        branch_name = kwargs.get("branch_name")
        try:
            repo = Repo(path, search_parent_directories=True)

            if action == "list":
                branches = []
                current_branch = repo.active_branch.name

                for branch in repo.branches:
                    prefix = "* " if branch.name == current_branch else "  "
                    branches.append(f"{prefix}{branch.name}")

                return ToolResult(
                    success=True,
                    output="\n".join(branches),
                    metadata={
                        "current_branch": current_branch,
                        "branch_count": len(repo.branches),
                    },
                )

            elif action == "create":
                if not branch_name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Branch name required for create action",
                    )

                repo.create_head(branch_name)
                return ToolResult(
                    success=True,
                    output=f"Created branch '{branch_name}'",
                    metadata={"branch_name": branch_name},
                )

            elif action == "checkout":
                if not branch_name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Branch name required for checkout action",
                    )

                repo.git.checkout(branch_name)
                return ToolResult(
                    success=True,
                    output=f"Switched to branch '{branch_name}'",
                    metadata={"branch_name": branch_name},
                )

            elif action == "delete":
                if not branch_name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Branch name required for delete action",
                    )

                repo.delete_head(branch_name, force=True)
                return ToolResult(
                    success=True,
                    output=f"Deleted branch '{branch_name}'",
                    metadata={"branch_name": branch_name},
                )

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid action: {action}. Use 'list', 'create', 'checkout', or 'delete'",
                )

        except InvalidGitRepositoryError:
            return ToolResult(success=False, output="", error="Not a git repository")
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Git branch operation failed: {str(e)}"
            )
