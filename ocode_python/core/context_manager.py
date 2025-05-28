"""
Context Manager for project analysis and intelligent file selection.
"""

import asyncio
import hashlib
import os
import sqlite3
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiofiles
from git import InvalidGitRepositoryError, Repo

from ..languages import language_registry


@dataclass
class FileInfo:
    """Information about a file in the project."""

    path: Path
    size: int
    modified_time: float
    content_hash: str
    language: Optional[str] = None
    symbols: Optional[List[str]] = None
    imports: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.symbols is None:
            self.symbols = []
        if self.imports is None:
            self.imports = []


@dataclass
class ProjectContext:
    """Complete project context for AI processing."""

    files: Dict[Path, str]  # file_path -> content
    file_info: Dict[Path, FileInfo]
    dependencies: Dict[Path, Set[Path]]  # file -> dependencies
    symbols: Dict[str, List[Path]]  # symbol -> files containing it
    project_root: Path
    git_info: Optional[Dict[str, Any]] = None

    def get_relevant_files(self, query: str, max_files: int = 10) -> List[Path]:
        """Get files most relevant to the query."""
        # Simple relevance scoring based on:
        # 1. Query terms in file content
        # 2. Query terms in file path
        # 3. Symbol matches

        scores = defaultdict(float)
        query_lower = query.lower()
        query_terms = query_lower.split()

        for file_path, content in self.files.items():
            score = 0.0
            content_lower = content.lower()
            path_lower = str(file_path).lower()

            # Score based on query terms in content
            for term in query_terms:
                score += content_lower.count(term) * 1.0

            # Score based on query terms in path
            for term in query_terms:
                if term in path_lower:
                    score += 5.0

            # Score based on symbols
            if file_path in self.file_info and self.file_info[file_path].symbols:
                symbols = self.file_info[file_path].symbols
                if symbols:  # Additional None check to satisfy mypy
                    for symbol in symbols:
                        for term in query_terms:
                            if term in symbol.lower():
                                score += 3.0

            if score > 0:
                scores[file_path] = score

        # Sort by score and return top files
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in sorted_files[:max_files]]


class ContextManager:
    """
    Manages project context, file analysis, and intelligent code selection.

    Features:
    - Automatic project structure discovery
    - File content caching with change detection
    - Dependency graph analysis
    - Symbol indexing
    - Git integration
    """

    def __init__(self, root: Optional[Path] = None, cache_dir: Optional[Path] = None):
        """
        Initialize context manager.

        Args:
            root: Project root directory. Defaults to current directory.
            cache_dir: Cache directory for storing analysis results.
        """
        self.root = Path(root) if root else Path.cwd()

        # Validate root exists
        if not self.root.exists():
            raise ValueError(f"Root directory does not exist: {self.root}")

        if not self.root.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root}")

        self.cache_dir = cache_dir or self.root / ".ocode" / "cache"

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create cache directory: {e}")

        # In-memory caches with size limits
        self.file_cache: Dict[Path, Tuple[str, float]] = {}  # path -> (content, mtime)
        self.file_info_cache: Dict[Path, FileInfo] = {}
        self.max_cache_size = 100  # Maximum number of files to cache

        # Persistent cache database
        self.db_path = self.cache_dir / "context.db"
        self._init_db()

        # Git repository (if available)
        self.repo: Optional[Repo] = None
        self._init_git()

        # File patterns to ignore - compiled for efficiency
        self.ignore_patterns = {
            ".git",
            ".ocode",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            ".env",
            "*.pyc",
            "*.pyo",
            "*.egg-info",
            ".DS_Store",
            "*.log",
            "*.tmp",
            ".idea",
            ".vscode",
        }

        # Compile wildcard patterns
        import fnmatch

        self.wildcard_patterns = [
            pattern
            for pattern in self.ignore_patterns
            if "*" in pattern or "?" in pattern
        ]

    def _init_db(self) -> None:
        """Initialize SQLite database for caching."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_analysis (
                    path TEXT PRIMARY KEY,
                    content_hash TEXT,
                    modified_time REAL,
                    language TEXT,
                    symbols TEXT,
                    imports TEXT,
                    created_at REAL
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dependencies (
                    source_file TEXT,
                    target_file TEXT,
                    dependency_type TEXT,
                    PRIMARY KEY (source_file, target_file)
                )
            """
            )

    def _init_git(self) -> None:
        """Initialize Git repository if available."""
        try:
            self.repo = Repo(self.root, search_parent_directories=True)
        except InvalidGitRepositoryError:
            self.repo = None

    def _should_ignore(self, path: Path) -> bool:
        """Check if file should be ignored."""
        import fnmatch

        # Check if any part of the path matches ignore patterns
        parts = path.parts
        path_str = str(path)

        # Check exact matches in path parts
        for pattern in self.ignore_patterns:
            if "*" not in pattern and "?" not in pattern:
                # Exact match pattern
                if pattern in parts:
                    return True

        # Check wildcard patterns
        for pattern in self.wildcard_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True
            # Also check against full path for patterns like "**/test"
            if fnmatch.fnmatch(path_str, pattern):
                return True

        # Only check file size if path exists and is a file
        if path.exists() and path.is_file():
            try:
                stat = path.stat()
                if stat.st_size > 1024 * 1024:
                    return True
            except (OSError, PermissionError):
                # Permission errors mean we should ignore it
                return True

        return False

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for file content."""
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    async def _read_file(self, path: Path) -> Optional[str]:
        """Read file content safely."""
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
                return str(content)
        except (UnicodeDecodeError, PermissionError, FileNotFoundError):
            return None

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        # Use language registry to get analyzer for file
        analyzer = language_registry.get_analyzer_for_file(path)
        if analyzer:
            return analyzer.language
        return None

    def _extract_symbols(self, content: str, language: str) -> List[str]:
        """Extract symbols (functions, classes, etc.) from code."""
        analyzer = language_registry.get_analyzer(language)
        if analyzer:
            try:
                symbols = analyzer.extract_symbols(content)
                return [symbol.name for symbol in symbols]
            except Exception:
                # Fallback to empty list if analysis fails
                pass
        return []

    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from code."""
        analyzer = language_registry.get_analyzer(language)
        if analyzer:
            try:
                imports = analyzer.extract_imports(content)
                return [imp.module for imp in imports]
            except Exception:
                # Fallback to empty list if analysis fails
                pass
        return []

    def _manage_cache_size(self) -> None:
        """Manage cache size to prevent unbounded growth."""
        if len(self.file_cache) > self.max_cache_size:
            # Remove oldest entries (simple LRU)
            sorted_entries = sorted(
                self.file_cache.items(), key=lambda x: x[1][1]  # Sort by mtime
            )
            # Remove entries to get back under limit
            num_to_remove = len(self.file_cache) - self.max_cache_size + 1
            for path, _ in sorted_entries[:num_to_remove]:
                del self.file_cache[path]
                if path in self.file_info_cache:
                    del self.file_info_cache[path]

    async def analyze_file(self, path: Path) -> Optional[FileInfo]:
        """Analyze a single file and extract metadata."""
        if self._should_ignore(path) or not path.is_file():
            return None

        try:
            stat = path.stat()
            mtime = stat.st_mtime

            # Check in-memory cache first
            if path in self.file_info_cache:
                cached_info = self.file_info_cache[path]
                if cached_info.modified_time == mtime:
                    return cached_info

            # Check persistent cache
            cached_info = self._get_cached_analysis(path, mtime)
            if cached_info:
                self.file_info_cache[path] = cached_info
                return cached_info

            # Read and analyze file
            content = await self._read_file(path)
            if content is None:
                return None

            content_hash = self._get_content_hash(content)
            language = self._detect_language(path)

            symbols = []
            imports = []

            if language:
                symbols = self._extract_symbols(content, language)
                imports = self._extract_imports(content, language)

            file_info = FileInfo(
                path=path,
                size=stat.st_size,
                modified_time=mtime,
                content_hash=content_hash,
                language=language,
                symbols=symbols,
                imports=imports,
            )

            # Cache the analysis
            self._cache_analysis(file_info)
            self.file_info_cache[path] = file_info

            # Manage cache size
            self._manage_cache_size()

            return file_info

        except (PermissionError, OSError):
            # Log but don't print for expected errors
            return None
        except Exception as e:
            # Log error analyzing file
            _ = e  # Using the exception variable
            return None

    def _get_cached_analysis(self, path: Path, mtime: float) -> Optional[FileInfo]:
        """Get cached file analysis if still valid."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM file_analysis WHERE path = ? AND modified_time = ?",
                    (str(path), mtime),
                )
                row = cursor.fetchone()

                if row:
                    return FileInfo(
                        path=Path(row[0]),
                        content_hash=row[1],
                        modified_time=row[2],
                        language=row[3],
                        symbols=row[4].split(",") if row[4] else [],
                        imports=row[5].split(",") if row[5] else [],
                        size=0,  # We don't cache size
                    )
        except sqlite3.Error:
            # Database error - continue without cache
            pass

        return None

    def _cache_analysis(self, file_info: FileInfo) -> None:
        """Cache file analysis to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO file_analysis
                       (path, content_hash, modified_time, language, symbols, imports, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(file_info.path),
                        file_info.content_hash,
                        file_info.modified_time,
                        file_info.language,
                        ",".join(file_info.symbols or []),
                        ",".join(file_info.imports or []),
                        time.time(),
                    ),
                )
        except sqlite3.Error:
            # Database error - continue without persistent cache
            pass

    async def scan_project(self) -> List[Path]:
        """Scan project directory for relevant files."""
        files = []

        for root, dirs, filenames in os.walk(self.root):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]

            for filename in filenames:
                file_path = Path(root) / filename
                if not self._should_ignore(file_path):
                    files.append(file_path)

        return files

    def _detect_multi_action_query(self, query_lower: str) -> Optional[Dict[str, Any]]:
        """
        Detect queries that require multiple actions/tools and should be delegated to multiple agents.

        Returns None if not a multi-action query, otherwise returns categorization result.
        """
        # Define common multi-action patterns
        multi_patterns = [
            # Test + Git patterns
            {
                "pattern": r"(run|execute) test.*and.*(commit|push)",
                "description": "Run tests then commit",
                "primary_tools": ["test_runner"],
                "secondary_tools": ["git_commit"],
                "workflow": "test_then_git",
                "category": "multi_action_test_git",
            },
            {
                "pattern": r"test.*coverage.*and.*(commit|push)",
                "description": "Test with coverage then commit",
                "primary_tools": ["test_runner", "coverage"],
                "secondary_tools": ["git_commit"],
                "workflow": "test_coverage_git",
                "category": "multi_action_test_git",
            },
            # File operations + Git patterns
            {
                "pattern": r"(edit|modify|update).*and.*(commit|save to git)",
                "description": "Edit files then commit",
                "primary_tools": ["file_edit"],
                "secondary_tools": ["git_commit"],
                "workflow": "edit_then_git",
                "category": "multi_action_file_git",
            },
            # Test + Build + Deploy patterns
            {
                "pattern": r"(test|run tests?).*then.*(build|compile).*then.*(deploy|push)",
                "description": "Test, build, and deploy",
                "primary_tools": ["test_runner"],
                "secondary_tools": ["bash", "git_commit"],
                "workflow": "test_build_deploy",
                "category": "multi_action_cicd",
            },
            # Create + Test patterns
            {
                "pattern": r"(create|add|build).*and.*(test|write tests)",
                "description": "Create component and write tests",
                "primary_tools": ["file_write", "file_edit"],
                "secondary_tools": ["test_runner"],
                "workflow": "create_test",
                "category": "multi_action_create_test",
            },
            # Analysis + Documentation patterns
            {
                "pattern": r"(analyze|review).*and.*(document|write docs)",
                "description": "Analyze then document",
                "primary_tools": ["architect"],
                "secondary_tools": ["file_write"],
                "workflow": "analyze_document",
                "category": "multi_action_analysis_docs",
            },
            # Search + Modify patterns
            {
                "pattern": r"(find|search|grep).*and.*(replace|modify|edit|update)",
                "description": "Search then modify",
                "primary_tools": ["grep", "code_grep"],
                "secondary_tools": ["file_edit"],
                "workflow": "search_modify",
                "category": "multi_action_search_edit",
            },
            # Setup + Configure patterns
            {
                "pattern": r"(setup|install|create).*and.*(configure|setup)",
                "description": "Setup then configure",
                "primary_tools": ["bash"],
                "secondary_tools": ["file_write", "file_edit"],
                "workflow": "setup_configure",
                "category": "multi_action_setup",
            },
        ]

        import re

        for pattern_def in multi_patterns:
            if re.search(pattern_def["pattern"], query_lower):
                all_tools = (
                    pattern_def["primary_tools"] + pattern_def["secondary_tools"]
                )

                return {
                    "category": pattern_def["category"],
                    "confidence": 0.9,
                    "suggested_tools": all_tools,
                    "context_strategy": "targeted",
                    "multi_action": True,
                    "workflow": pattern_def["workflow"],
                    "primary_tools": pattern_def["primary_tools"],
                    "secondary_tools": pattern_def["secondary_tools"],
                    "description": pattern_def["description"],
                }

        # Check for general multi-action indicators
        conjunctions = ["and", "then", "after", "followed by", "next", "also"]
        has_conjunction = any(conj in query_lower for conj in conjunctions)

        if has_conjunction:
            # Split query by conjunctions and analyze each part
            import re

            parts = re.split(
                r"\s+(and|then|after|followed by|next|also)\s+", query_lower
            )
            parts = [part.strip() for part in parts if part.strip() not in conjunctions]

            if len(parts) >= 2:
                # Quick categorization of each part
                part_tools = []
                for part in parts:
                    part_result = self._quick_categorize_part(part)
                    if part_result:
                        part_tools.extend(part_result.get("suggested_tools", []))

                if len(set(part_tools)) > 1:  # Multiple different tools needed
                    return {
                        "category": "multi_action_general",
                        "confidence": 0.8,
                        "suggested_tools": list(set(part_tools)),
                        "context_strategy": "targeted",
                        "multi_action": True,
                        "workflow": "sequential_actions",
                        "parts": parts,
                        "description": f'Sequential actions: {" → ".join(parts)}',
                    }

        return None

    def _quick_categorize_part(self, part: str) -> Optional[Dict[str, Any]]:
        """Quick categorization of a query part for multi-action detection."""
        part_lower = part.strip().lower()

        # Test patterns
        if any(kw in part_lower for kw in ["test", "tests", "pytest", "jest"]):
            return {"suggested_tools": ["test_runner"]}

        # Git patterns
        if any(kw in part_lower for kw in ["commit", "push", "git"]):
            return {"suggested_tools": ["git_commit"]}

        # File patterns
        if any(kw in part_lower for kw in ["edit", "modify", "write", "create file"]):
            return {"suggested_tools": ["file_edit", "file_write"]}

        # Search patterns
        if any(kw in part_lower for kw in ["find", "search", "grep", "locate"]):
            return {"suggested_tools": ["grep", "code_grep"]}

        # Build/Shell patterns
        if any(
            kw in part_lower
            for kw in ["build", "compile", "run", "execute", "npm", "docker"]
        ):
            return {"suggested_tools": ["bash"]}

        # Analysis patterns
        if any(kw in part_lower for kw in ["analyze", "review", "check architecture"]):
            return {"suggested_tools": ["architect"]}

        # Documentation patterns
        if any(kw in part_lower for kw in ["document", "write docs", "readme"]):
            return {"suggested_tools": ["file_write"]}

        return None

    def _categorize_query(self, query: str) -> Dict[str, Any]:
        """
        Comprehensive query categorization to determine appropriate context strategy and tools.
        Handles multi-action queries that may require multiple tools/agents.

        Returns:
            Dict with category, confidence, suggested_tools, context_strategy, and multi_action flag
        """
        # Validate query
        if not query or not query.strip():
            return {
                "category": "empty_query",
                "confidence": 1.0,
                "suggested_tools": [],
                "context_strategy": "none",
            }

        query_lower = query.lower().strip()
        suggested_tools = []
        context_strategy = "full"

        # First, check for multi-action queries that need multiple tools/agents
        multi_action_result = self._detect_multi_action_query(query_lower)
        if multi_action_result:
            return multi_action_result

        # Agent management queries
        agent_patterns = {
            "keywords": [
                "agent",
                "agents",
                "reviewer",
                "reviewers",
                "sub-agent",
                "task delegation",
                "delegate",
            ],
            "actions": [
                "create",
                "list",
                "status",
                "how many",
                "count",
                "delegate",
                "terminate",
                "manage",
            ],
        }

        if any(kw in query_lower for kw in agent_patterns["keywords"]):
            if any(action in query_lower for action in agent_patterns["actions"]):
                return {
                    "category": "agent_management",
                    "confidence": 0.9,
                    "suggested_tools": ["agent"],
                    "context_strategy": "minimal",
                }

        # Tool/capability queries
        tool_patterns = {
            "keywords": [
                "tool",
                "tools",
                "command",
                "commands",
                "capability",
                "capabilities",
                "function",
                "functions",
            ],
            "triggers": [
                "available",
                "can use",
                "list",
                "what",
                "show me",
                "help",
                "how to",
                "which",
            ],
        }

        if any(kw in query_lower for kw in tool_patterns["keywords"]) and any(
            trigger in query_lower for trigger in tool_patterns["triggers"]
        ):
            return {
                "category": "tool_listing",
                "confidence": 0.95,
                "suggested_tools": [],
                "context_strategy": "none",
            }

        # File operations - check early for explicit file operations
        file_patterns = {
            "read": ["read", "show", "display", "view", "cat", "open"],
            "write": ["write", "save", "create", "generate", "output"],
            "search": ["find", "search", "grep", "look for", "locate"],
            "edit": ["edit", "modify", "change", "update", "replace"],
            "list": ["list", "ls", "dir", "files in", "contents of"],
        }

        file_confidence = 0.0
        file_tools = []
        file_indicators = [
            "file",
            "files",
            "directory",
            "folder",
            ".py",
            ".js",
            ".ts",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
        ]

        # Boost confidence if file-related terms are present
        has_file_context = any(
            indicator in query_lower for indicator in file_indicators
        )

        for operation, keywords in file_patterns.items():
            if any(kw in query_lower for kw in keywords):
                file_confidence += 0.3 if has_file_context else 0.2
                if operation == "read":
                    file_tools.extend(["file_read", "ls"])
                elif operation == "write":
                    file_tools.extend(["file_write"])
                elif operation == "search":
                    file_tools.extend(["grep", "code_grep", "glob"])
                elif operation == "edit":
                    file_tools.extend(["file_edit"])
                elif operation == "list":
                    file_tools.extend(["ls", "file_list", "glob"])

        # Git operations - check BEFORE file operations to avoid conflicts, but AFTER testing
        git_patterns = {
            "keywords": [
                "git",
                "commit",
                "branch",
                "merge",
                "diff",
                "repository",
                "repo",
            ],
            "actions": ["commit", "push", "pull", "checkout", "merge", "diff", "log"],
            "status_terms": ["git status", "repository status", "repo status"],
            "diff_terms": ["show diff", "git diff", "diff for"],
        }

        git_match = any(kw in query_lower for kw in git_patterns["keywords"])
        git_action = any(action in query_lower for action in git_patterns["actions"])
        status_match = any(term in query_lower for term in git_patterns["status_terms"])
        diff_match = any(term in query_lower for term in git_patterns["diff_terms"])

        # Don't match git if testing keywords are primary focus
        has_test_focus = any(
            kw in query_lower for kw in ["test", "tests", "testing"]
        ) and any(action in query_lower for action in ["run", "execute"])

        if (
            git_match or git_action or status_match or diff_match
        ) and not has_test_focus:
            git_tools = []
            if any(word in query_lower for word in ["status", "state"]) or status_match:
                git_tools.append("git_status")
            if any(word in query_lower for word in ["commit", "save"]):
                git_tools.append("git_commit")
            if (
                any(word in query_lower for word in ["diff", "changes", "difference"])
                or diff_match
            ):
                git_tools.append("git_diff")
            if any(word in query_lower for word in ["branch", "checkout"]):
                git_tools.append("git_branch")

            if not git_tools:
                git_tools = ["git_status"]  # Default

            return {
                "category": "git_operations",
                "confidence": 0.9,
                "suggested_tools": git_tools,
                "context_strategy": "minimal",
            }

        # Early return for strong file operations
        if file_confidence >= 0.5 or (has_file_context and file_confidence >= 0.3):
            return {
                "category": "file_operations",
                "confidence": min(file_confidence, 0.9),
                "suggested_tools": list(set(file_tools)),
                "context_strategy": "targeted",
            }

        # Testing and quality - check BEFORE git operations since "run tests" might also mention git
        testing_patterns = {
            "keywords": [
                "test",
                "tests",
                "testing",
                "coverage",
                "lint",
                "quality",
                "validate",
            ],
            "frameworks": ["pytest", "jest", "unittest", "mocha", "go test", "rspec"],
            "actions": ["run", "execute", "check", "measure", "report"],
            "quality_terms": [
                "code quality",
                "static analysis",
                "quality issues",
                "code check",
            ],
            "test_commands": ["run tests", "execute tests", "run test", "execute test"],
        }

        test_match = any(
            kw in query_lower
            for kw in testing_patterns["keywords"] + testing_patterns["frameworks"]
        )
        test_action = any(
            action in query_lower for action in testing_patterns["actions"]
        )
        quality_match = any(
            term in query_lower for term in testing_patterns["quality_terms"]
        )
        test_command = any(
            cmd in query_lower for cmd in testing_patterns["test_commands"]
        )

        if (test_match and test_action) or quality_match or test_command:
            tools = ["test_runner"]
            if "coverage" in query_lower:
                tools.append("coverage")
            if "lint" in query_lower:
                tools.append("lint")

            return {
                "category": "testing_quality",
                "confidence": 0.85,
                "suggested_tools": tools,
                "context_strategy": "targeted",
            }

        # Architecture analysis
        architecture_patterns = {
            "keywords": [
                "architecture",
                "structure",
                "design",
                "dependencies",
                "patterns",
                "analyze codebase",
                "code structure",
                "project structure",
                "overview",
                "diagram",
                "visualization",
            ],
            "actions": [
                "analyze",
                "review",
                "examine",
                "assess",
                "evaluate",
                "generate",
            ],
        }

        arch_match = any(kw in query_lower for kw in architecture_patterns["keywords"])
        arch_action = any(
            action in query_lower for action in architecture_patterns["actions"]
        )

        if arch_match and (arch_action or "architecture" in query_lower):
            return {
                "category": "architecture_analysis",
                "confidence": 0.9,
                "suggested_tools": ["architect", "think"],
                "context_strategy": "targeted",
            }

        # Shell/command execution - be more specific to avoid conflicts
        shell_patterns = {
            "explicit_keywords": ["shell", "bash", "terminal", "command line"],
            "command_indicators": ["npm", "pip", "docker", "make", "cargo"],
            "script_keywords": ["script", "run script", "execute script"],
        }

        explicit_shell = any(
            kw in query_lower for kw in shell_patterns["explicit_keywords"]
        )
        command_indicator = any(
            cmd in query_lower for cmd in shell_patterns["command_indicators"]
        )
        script_match = any(
            kw in query_lower for kw in shell_patterns["script_keywords"]
        )

        shell_match = explicit_shell or command_indicator or script_match

        if shell_match:
            shell_tools = ["bash"]
            if "script" in query_lower:
                shell_tools.append("script")

            return {
                "category": "shell_execution",
                "confidence": 0.8,
                "suggested_tools": shell_tools,
                "context_strategy": "minimal",
            }

        # Memory/session management
        memory_patterns = {
            "keywords": [
                "remember",
                "save",
                "recall",
                "memory",
                "session",
                "context",
                "persist",
                "store",
            ],
            "actions": ["save", "load", "remember", "recall", "store", "retrieve"],
        }

        # Memory clearing/destructive operations
        lobotomize_patterns = [
            "lobotomize",
            "clear memory",
            "forget everything",
            "wipe memory",
            "reset memory",
            "start fresh",
            "amnesia",
        ]

        memory_match = any(kw in query_lower for kw in memory_patterns["keywords"])
        memory_action = any(
            action in query_lower for action in memory_patterns["actions"]
        )
        lobotomize_match = any(
            pattern in query_lower for pattern in lobotomize_patterns
        )

        if lobotomize_match:
            return {
                "category": "memory_lobotomize",
                "confidence": 0.95,
                "suggested_tools": ["memory_write"],
                "context_strategy": "minimal",
            }
        elif memory_match and memory_action:
            return {
                "category": "memory_management",
                "confidence": 0.85,
                "suggested_tools": ["memory_read", "memory_write"],
                "context_strategy": "minimal",
            }

        # Reasoning/analysis
        reasoning_patterns = {
            "keywords": [
                "think",
                "analyze",
                "reasoning",
                "decision",
                "pros and cons",
                "brainstorm",
                "problem solving",
                "root cause",
                "evaluate",
                "assess",
            ],
            "triggers": [
                "help me think",
                "what are the",
                "should i",
                "how to approach",
                "break down",
            ],
        }

        reasoning_match = any(
            kw in query_lower for kw in reasoning_patterns["keywords"]
        )
        reasoning_trigger = any(
            trigger in query_lower for trigger in reasoning_patterns["triggers"]
        )

        if reasoning_match or reasoning_trigger:
            return {
                "category": "reasoning_analysis",
                "confidence": 0.8,
                "suggested_tools": ["think"],
                "context_strategy": "targeted",
            }

        # Annotation/organization - but check for TODO search which should be file_operations
        annotation_patterns = {
            "keywords": ["note", "bookmark", "annotate", "tag", "organize", "reminder"],
            "todo_creation": ["add todo", "create todo", "mark todo", "todo note"],
            "actions": ["add", "create", "mark", "tag", "annotate", "organize"],
        }

        # Don't match "todo" if it's about searching for TODOs
        is_todo_search = any(
            term in query_lower
            for term in ["find todo", "search todo", "todo comments", "all todo"]
        )

        annotation_match = any(
            kw in query_lower for kw in annotation_patterns["keywords"]
        ) or any(term in query_lower for term in annotation_patterns["todo_creation"])
        annotation_action = any(
            action in query_lower for action in annotation_patterns["actions"]
        )

        # Special case for "mark" + code/section which is annotation
        mark_code = "mark" in query_lower and any(
            term in query_lower
            for term in ["code", "section", "function", "class", "line", "important"]
        )

        if mark_code:
            annotation_match = True
            annotation_action = True

        if annotation_match and annotation_action and not is_todo_search:
            return {
                "category": "annotation_organization",
                "confidence": 0.85,
                "suggested_tools": ["sticker_request"],
                "context_strategy": "targeted",
            }

        # Notebook operations
        notebook_patterns = {
            "keywords": ["notebook", "jupyter", "ipynb", "cell", "kernel"],
            "actions": ["read", "edit", "modify", "run", "execute"],
        }

        notebook_match = any(kw in query_lower for kw in notebook_patterns["keywords"])
        notebook_action = any(
            action in query_lower for action in notebook_patterns["actions"]
        )

        if notebook_match and notebook_action:
            notebook_tools = ["notebook_read"]
            if any(word in query_lower for word in ["edit", "modify", "change"]):
                notebook_tools.append("notebook_edit")

            return {
                "category": "notebook_operations",
                "confidence": 0.9,
                "suggested_tools": notebook_tools,
                "context_strategy": "targeted",
            }

        # File operations (if we detected file patterns earlier)
        if file_confidence >= 0.4:
            return {
                "category": "file_operations",
                "confidence": file_confidence,
                "suggested_tools": list(set(file_tools)),
                "context_strategy": "targeted",
            }

        # Multi-tool workflows (complex cases) - be more specific
        complex_patterns = {
            "refactor": ["refactor", "restructure", "reorganize"],
            "debug": ["debug", "troubleshoot"],
            "optimize": ["optimize", "improve performance", "performance"],
            "document": ["document", "documentation", "docs", "readme"],
            "setup": ["setup", "configure", "install", "initialize", "bootstrap"],
        }

        for workflow_type, keywords in complex_patterns.items():
            # Require explicit workflow keywords, not just any mention
            explicit_match = any(kw in query_lower for kw in keywords)

            # Additional context requirements for some workflows
            if workflow_type == "setup" and explicit_match:
                # "setup" should have project/package context
                has_project_context = any(
                    term in query_lower
                    for term in ["project", "package", "environment", "new"]
                )
                if not has_project_context:
                    continue

            if explicit_match:
                workflow_tools = []
                context_strat = "full"

                if workflow_type == "refactor":
                    workflow_tools = ["architect", "grep", "file_edit", "test_runner"]
                elif workflow_type == "debug":
                    workflow_tools = ["grep", "architect", "test_runner", "think"]
                elif workflow_type == "optimize":
                    workflow_tools = ["architect", "think", "test_runner"]
                elif workflow_type == "document":
                    workflow_tools = ["architect", "file_write", "grep"]
                elif workflow_type == "setup":
                    workflow_tools = ["bash", "file_write", "file_read"]
                    context_strat = "minimal"

                return {
                    "category": f"workflow_{workflow_type}",
                    "confidence": 0.8,
                    "suggested_tools": workflow_tools,
                    "context_strategy": context_strat,
                }

        # Default: general code analysis
        return {
            "category": "code_analysis",
            "confidence": 0.5,
            "suggested_tools": ["architect", "grep", "ls"],
            "context_strategy": "full",
        }

    async def build_context(self, query: str, max_files: int = 20) -> ProjectContext:
        """
        Build comprehensive project context for a query.

        Args:
            query: User query or task description
            max_files: Maximum number of files to include

        Returns:
            ProjectContext with relevant files and metadata

        Raises:
            ValueError: If max_files is invalid
        """
        # Validate inputs
        if max_files < 0:
            raise ValueError("max_files must be non-negative")

        if max_files > 1000:
            # Prevent excessive resource usage
            max_files = 1000

        # Categorize query to determine context strategy
        query_analysis = self._categorize_query(query)
        # query_category = query_analysis["category"]  # Currently unused
        context_strategy = query_analysis.get("context_strategy", "full")

        # Adjust context based on strategy
        if context_strategy == "none":
            max_files = 0  # No files needed (e.g., tool listing)
        elif context_strategy == "minimal":
            max_files = min(
                max_files, 3
            )  # Minimal context (e.g., agent management, git ops)
        elif context_strategy == "targeted":
            max_files = min(max_files, 10)  # Focused context (e.g., specific analysis)
        # else: context_strategy == "full" uses original max_files

        # Scan project files
        all_files = await self.scan_project()

        # Analyze files concurrently
        semaphore = asyncio.Semaphore(10)  # Limit concurrent file operations

        async def analyze_with_semaphore(path):
            async with semaphore:
                return await self.analyze_file(path)

        analysis_tasks = [analyze_with_semaphore(f) for f in all_files]
        file_analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Filter valid analyses
        valid_analyses = {}
        for i, analysis in enumerate(file_analyses):
            if isinstance(analysis, FileInfo):
                valid_analyses[all_files[i]] = analysis

        # Read file contents for analyzed files
        file_contents = {}
        content_tasks = []

        # Limit number of files to read based on max_files
        files_to_read = list(valid_analyses.keys())[
            : max_files * 2
        ]  # Read more than needed for filtering

        for file_path in files_to_read:
            content_tasks.append(self._read_file(file_path))

        contents = await asyncio.gather(*content_tasks, return_exceptions=True)

        for file_path, content in zip(files_to_read, contents):
            if isinstance(content, str) and content:
                file_contents[file_path] = content
                # Cache content with size management
                if len(self.file_cache) < self.max_cache_size:
                    self.file_cache[file_path] = (
                        content,
                        valid_analyses[file_path].modified_time,
                    )
                else:
                    self._manage_cache_size()
                    self.file_cache[file_path] = (
                        content,
                        valid_analyses[file_path].modified_time,
                    )

        # Build symbol index
        symbols = defaultdict(list)
        for file_path, analysis in valid_analyses.items():
            if analysis.symbols:
                for symbol_name in analysis.symbols:
                    symbols[symbol_name].append(file_path)

        # Build dependency graph (simplified)
        dependencies = defaultdict(set)
        for file_path, analysis in valid_analyses.items():
            if analysis.imports:
                for imp_name in analysis.imports:
                    # Try to resolve import to actual files
                    for other_path in valid_analyses.keys():
                        if imp_name in str(other_path) or other_path.stem == imp_name:
                            dependencies[file_path].add(other_path)

        # Get Git information
        git_info = None
        if self.repo:
            try:
                git_info = {
                    "branch": self.repo.active_branch.name,
                    "commit": self.repo.head.commit.hexsha[:8],
                    "modified_files": [
                        item.a_path for item in self.repo.index.diff(None)
                    ],
                    "untracked_files": self.repo.untracked_files,
                }
            except Exception:
                pass

        # Create context and select relevant files
        context = ProjectContext(
            files=file_contents,
            file_info=valid_analyses,
            dependencies=dict(dependencies),
            symbols=dict(symbols),
            project_root=self.root,
            git_info=git_info,
        )

        # Select most relevant files for the query
        relevant_files = context.get_relevant_files(query, max_files)

        # Filter context to only include relevant files
        filtered_files = {
            f: content for f, content in file_contents.items() if f in relevant_files
        }
        filtered_info = {
            f: info for f, info in valid_analyses.items() if f in relevant_files
        }

        context.files = filtered_files
        context.file_info = filtered_info

        return context


async def main() -> None:
    """Example usage of ContextManager."""
    manager = ContextManager()

    print("Scanning project...")
    context = await manager.build_context("authentication login user", max_files=5)

    print(f"Project root: {context.project_root}")
    print(f"Files analyzed: {len(context.files)}")
    print(f"Git info: {context.git_info}")

    for file_path in context.files.keys():
        info = context.file_info.get(file_path)
        if info:
            print(f"{file_path}: {info.language}, {len(info.symbols or [])} symbols")


if __name__ == "__main__":
    asyncio.run(main())
