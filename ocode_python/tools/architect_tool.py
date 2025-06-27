"""
Codebase architecture analysis and visualization tool for OCode.
"""

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class ArchitectTool(Tool):
    """Tool for analyzing codebase architecture, dependencies, and design patterns."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the architect tool specification.

        Returns:
            ToolDefinition with parameters for comprehensive codebase analysis
            including architecture overview, dependencies, patterns, metrics,
            and diagram generation.
        """
        return ToolDefinition(
            name="architect",
            description="Analyze codebase architecture, dependencies, design patterns, and generate architectural insights",  # noqa: E501
            parameters=[  # noqa: E501
                ToolParameter(
                    name="analysis_type",
                    type="string",
                    description="Type of analysis: 'overview', 'dependencies', 'structure', 'patterns', 'metrics', 'health', 'diagram'",  # noqa: E501
                    required=True,  # noqa: E501
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to analyze (file, directory, or project root)",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Programming language to focus on: 'python', 'javascript', 'typescript', 'java', 'auto'",  # noqa: E501
                    required=False,  # noqa: E501
                    default="auto",
                ),
                ToolParameter(
                    name="depth",
                    type="number",
                    description="Analysis depth (1=surface, 3=deep)",
                    required=False,
                    default=2,
                ),
                ToolParameter(
                    name="include_patterns",
                    type="array",
                    description="File patterns to include (e.g., ['*.py', '*.js'])",
                    required=False,
                ),
                ToolParameter(
                    name="exclude_patterns",
                    type="array",
                    description="File patterns to exclude (e.g., ['*test*', 'node_modules'])",  # noqa: E501
                    required=False,  # noqa: E501
                    default=[
                        "*test*",
                        "*__pycache__*",
                        "node_modules",
                        ".git",
                        "venv",
                        ".env",
                    ],
                ),
                ToolParameter(
                    name="output_format",
                    type="string",
                    description="Output format: 'summary', 'detailed', 'json', 'mermaid'",  # noqa: E501
                    required=False,  # noqa: E501
                    default="summary",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Perform architectural analysis of the codebase."""
        try:
            # Extract parameters
            analysis_type = kwargs.get("analysis_type")
            path = kwargs.get("path", ".")
            language = kwargs.get("language", "auto")
            depth = kwargs.get("depth", 2)
            include_patterns = kwargs.get("include_patterns")
            exclude_patterns = kwargs.get("exclude_patterns")
            output_format = kwargs.get("output_format", "summary")

            if not analysis_type:
                return ToolResult(
                    success=False,
                    output="",
                    error="analysis_type parameter is required",
                )

            # Set default exclude patterns if none provided
            if exclude_patterns is None:
                exclude_patterns = [
                    "*test*",
                    "*__pycache__*",
                    "node_modules",
                    ".git",
                    "venv",
                    ".env",
                ]

            # Convert path to Path object
            analysis_path = Path(path).resolve()

            if not analysis_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Path does not exist: {path}"
                )

            # Detect language if auto
            if language == "auto":
                language = self._detect_primary_language(analysis_path)

            # Perform the requested analysis
            if analysis_type == "overview":
                results = await self._analyze_overview(
                    analysis_path, language, include_patterns, exclude_patterns
                )
            elif analysis_type == "dependencies":
                results = await self._analyze_dependencies(
                    analysis_path, language, depth, include_patterns, exclude_patterns
                )
            elif analysis_type == "structure":
                results = await self._analyze_structure(
                    analysis_path, language, depth, include_patterns, exclude_patterns
                )
            elif analysis_type == "patterns":
                results = await self._analyze_patterns(
                    analysis_path, language, include_patterns, exclude_patterns
                )
            elif analysis_type == "metrics":
                results = await self._analyze_metrics(
                    analysis_path, language, include_patterns, exclude_patterns
                )
            elif analysis_type == "health":
                results = await self._analyze_health(
                    analysis_path, language, include_patterns, exclude_patterns
                )
            elif analysis_type == "diagram":
                results = await self._generate_diagram(
                    analysis_path, language, include_patterns, exclude_patterns
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown analysis type: {analysis_type}",
                )

            # Format output
            if output_format == "json":
                output = json.dumps(results, indent=2)
            elif output_format == "mermaid":
                output = self._format_mermaid_output(results, analysis_type)
            elif output_format == "detailed":
                output = self._format_detailed_output(results, analysis_type)
            else:  # summary
                output = self._format_summary_output(results, analysis_type)

            return ToolResult(success=True, output=output, metadata=results)

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error in architectural analysis: {str(e)}",
            )

    def _detect_primary_language(self, path: Path) -> str:
        """Detect the primary programming language in the codebase."""
        language_counts: Dict[str, int] = defaultdict(int)

        for file_path in path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in [".py"]:
                    language_counts["python"] += 1
                elif suffix in [".js", ".jsx"]:
                    language_counts["javascript"] += 1
                elif suffix in [".ts", ".tsx"]:
                    language_counts["typescript"] += 1
                elif suffix in [".java"]:
                    language_counts["java"] += 1
                elif suffix in [".go"]:
                    language_counts["go"] += 1
                elif suffix in [".rs"]:
                    language_counts["rust"] += 1

        if language_counts:
            return max(language_counts, key=lambda x: language_counts.get(x, 0))
        return "unknown"

    def _should_include_file(
        self,
        file_path: Path,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> bool:
        """Check if a file should be included in analysis."""
        file_str = str(file_path)

        # Check exclude patterns first
        if exclude_patterns:
            for pattern in exclude_patterns:
                if self._matches_pattern(file_str, pattern):
                    return False

        # Check include patterns
        if include_patterns:
            return any(
                self._matches_pattern(file_str, pattern) for pattern in include_patterns
            )

        # Default: include common source code files
        return file_path.suffix.lower() in [
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
        ]

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a simple glob-like pattern."""
        import fnmatch

        return fnmatch.fnmatch(text, pattern)

    async def _analyze_overview(
        self,
        path: Path,
        language: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Generate high-level overview of the codebase."""
        overview: Dict[str, Any] = {
            "path": str(path),
            "language": language,
            "type": "project" if path.is_dir() else "file",
            "files": {},
            "structure": {},
            "summary": {},
        }

        # Collect file statistics
        total_files = 0
        total_lines = 0
        file_types = defaultdict(int)
        directories = set()

        if path.is_file():
            # Analyze single file
            overview["files"] = self._analyze_single_file(path)
            total_files = 1
            files_info = overview["files"]
            if isinstance(files_info, dict):
                total_lines = files_info.get("lines", 0)
            else:
                total_lines = 0
            file_types[path.suffix] = 1
        else:
            # Analyze directory
            for file_path in path.rglob("*"):
                if file_path.is_file() and self._should_include_file(
                    file_path, include_patterns, exclude_patterns
                ):
                    total_files += 1
                    file_types[file_path.suffix] += 1

                    # Count lines
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            lines = len(f.readlines())
                            total_lines += lines
                    except Exception:  # nosec
                        continue

                if file_path.is_dir():
                    directories.add(str(file_path.relative_to(path)))

        overview["summary"] = {
            "total_files": total_files,
            "total_lines": total_lines,
            "file_types": dict(file_types),
            "directories": len(directories),
            "avg_file_size": total_lines // max(total_files, 1),
        }

        # Identify key architecture files
        arch_files = self._identify_architecture_files(path)
        overview["architecture_files"] = arch_files

        return overview

    def _analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single source file."""
        file_info = {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "extension": file_path.suffix,
            "lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": "unknown",
        }

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                file_info["lines"] = len(content.splitlines())

            # Language-specific analysis
            if file_path.suffix == ".py":
                file_info.update(self._analyze_python_file(content))
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                file_info.update(self._analyze_javascript_file(content))

        except Exception:  # nosec
            pass

        return file_info

    def _analyze_python_file(self, content: str) -> Dict[str, Any]:
        """Analyze Python file using AST."""
        info: Dict[str, Any] = {
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": "low",
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    info["functions"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": len(node.args.args),
                            "decorators": len(node.decorator_list),
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    info["classes"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "methods": len(
                                [n for n in node.body if isinstance(n, ast.FunctionDef)]
                            ),
                            "bases": len(node.bases),
                        }
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            info["imports"].append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            info["imports"].append(f"{module}.{alias.name}")

            # Simple complexity estimate
            total_elements = len(info["functions"]) + len(info["classes"])
            if total_elements > 20:
                info["complexity"] = "high"
            elif total_elements > 10:
                info["complexity"] = "medium"
            else:
                info["complexity"] = "low"

        except SyntaxError:
            info["complexity"] = "syntax_error"
        except Exception:  # nosec
            pass

        return info

    def _analyze_javascript_file(self, content: str) -> Dict[str, Any]:
        """Basic analysis of JavaScript/TypeScript files."""
        info: Dict[str, Any] = {
            "functions": [],
            "classes": [],
            "imports": [],
            "exports": [],
            "complexity": "low",
        }

        lines = content.splitlines()

        # Simple regex-based analysis (could be enhanced with proper parser)
        function_pattern = re.compile(
            r"function\s+(\w+)|(\w+)\s*[=:]\s*function|(\w+)\s*[=:]\s*\([^)]*\)\s*=>"
        )
        class_pattern = re.compile(r"class\s+(\w+)")
        import_pattern = re.compile(
            r'import\s+.*from\s+["\']([^"\']+)["\']|require\(["\']([^"\']+)["\']\)'
        )
        export_pattern = re.compile(r"export\s+(default\s+)?(\w+)")

        for line_num, line in enumerate(lines, 1):
            # Find functions
            func_match = function_pattern.search(line)
            if func_match:
                func_name = (
                    func_match.group(1)
                    or func_match.group(2)
                    or func_match.group(3)
                    or "anonymous"
                )
                info["functions"].append({"name": func_name, "line": line_num})

            # Find classes
            class_match = class_pattern.search(line)
            if class_match:
                info["classes"].append({"name": class_match.group(1), "line": line_num})

            # Find imports
            import_match = import_pattern.search(line)
            if import_match:
                module = import_match.group(1) or import_match.group(2)
                info["imports"].append(module)

            # Find exports
            export_match = export_pattern.search(line)
            if export_match:
                info["exports"].append(export_match.group(2))

        # Simple complexity estimate
        total_elements = len(info["functions"]) + len(info["classes"])
        if total_elements > 15:
            info["complexity"] = "high"
        elif total_elements > 8:
            info["complexity"] = "medium"
        else:
            info["complexity"] = "low"

        return info

    def _identify_architecture_files(self, path: Path) -> List[Dict[str, str]]:
        """Identify key architecture and configuration files."""
        arch_files = []

        important_files = [
            "README.md",
            "readme.md",
            "README.txt",
            "package.json",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Makefile",
            "makefile",
            ".gitignore",
            ".env",
            ".env.example",
            "config.py",
            "settings.py",
            "config.json",
            "config.yaml",
            "main.py",
            "app.py",
            "index.js",
            "index.ts",
            "schema.sql",
            "migrations",
            "models.py",
        ]

        if path.is_file():
            if path.name in important_files:
                arch_files.append({"file": str(path), "type": "config"})
        else:
            for pattern in important_files:
                for file_path in path.rglob(pattern):
                    if file_path.is_file():
                        file_type = self._classify_architecture_file(file_path.name)
                        arch_files.append(
                            {
                                "file": str(file_path.relative_to(path)),
                                "type": file_type,
                            }
                        )

        return arch_files

    def _classify_architecture_file(self, filename: str) -> str:
        """Classify the type of architecture file."""
        filename_lower = filename.lower()

        if filename_lower in ["readme.md", "readme.txt"]:
            return "documentation"
        elif filename_lower in [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
        ]:
            return "dependencies"
        elif filename_lower in [
            "dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
        ]:
            return "containerization"
        elif filename_lower in ["makefile"]:
            return "build"
        elif (
            filename_lower.startswith(".env")
            or "config" in filename_lower
            or "settings" in filename_lower
        ):
            return "configuration"
        elif filename_lower in ["main.py", "app.py", "index.js", "index.ts"]:
            return "entry_point"
        elif "schema" in filename_lower or "model" in filename_lower:
            return "data_model"
        else:
            return "other"

    async def _analyze_dependencies(
        self,
        path: Path,
        language: str,
        depth: int,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Analyze code dependencies and relationships.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            depth: Analysis depth (not currently used).
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing internal/external dependencies, dependency graph,
            circular dependencies, and statistics.
        """
        dependencies: Dict[str, Any] = {
            "internal": defaultdict(set),
            "external": set(),
            "dependency_graph": {},
            "circular_dependencies": [],
            "dependency_depth": {},
            "statistics": {},
        }

        files_analyzed = []

        if path.is_file():
            files_to_analyze = [path]
        else:
            files_to_analyze = [
                f
                for f in path.rglob("*")
                if f.is_file()
                and self._should_include_file(f, include_patterns, exclude_patterns)
            ]

        for file_path in files_to_analyze:
            file_deps = self._extract_file_dependencies(file_path, language)
            if file_deps:
                rel_path = str(
                    file_path.relative_to(path) if path.is_dir() else file_path.name
                )
                files_analyzed.append(rel_path)

                dependencies["dependency_graph"][rel_path] = file_deps

                for dep in file_deps.get("internal", []):
                    internal_deps = dependencies["internal"]
                    if rel_path not in internal_deps:
                        internal_deps[rel_path] = set()
                    internal_deps[rel_path].add(dep)

                for dep in file_deps.get("external", []):
                    external_deps = dependencies["external"]
                    if isinstance(external_deps, set):
                        external_deps.add(dep)

        # Detect circular dependencies
        internal_deps = dependencies.get("internal", {})
        if isinstance(internal_deps, dict):
            dependencies["circular_dependencies"] = self._detect_circular_dependencies(
                internal_deps
            )

        # Calculate statistics
        dependencies["statistics"] = {
            "files_analyzed": len(files_analyzed),
            "total_internal_deps": (
                sum(len(deps) for deps in dependencies["internal"].values())
                if isinstance(dependencies["internal"], dict)
                else 0
            ),
            "total_external_deps": len(dependencies["external"]),
            "avg_deps_per_file": (
                sum(len(deps) for deps in dependencies["internal"].values())
                / max(len(files_analyzed), 1)
                if isinstance(dependencies["internal"], dict)
                else 0
            ),
            "files_with_no_deps": len(
                [
                    f
                    for f in files_analyzed
                    if f not in dependencies["internal"]
                    or not dependencies["internal"][f]
                ]
            ),
            "most_dependent_files": sorted(
                dependencies["internal"].items(), key=lambda x: len(x[1]), reverse=True
            )[:5],
        }

        return dependencies

    def _extract_file_dependencies(
        self, file_path: Path, language: str
    ) -> Dict[str, List[str]]:
        """Extract dependencies from a single file.

        Args:
            file_path: Path to the file to analyze.
            language: Programming language hint.

        Returns:
            Dictionary with 'internal' and 'external' dependency lists.
        """
        deps: Dict[str, List[str]] = {"internal": [], "external": []}

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if language == "python" or file_path.suffix == ".py":
                deps = self._extract_python_dependencies(content, file_path)
            elif language in ["javascript", "typescript"] or file_path.suffix in [
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
            ]:
                deps = self._extract_javascript_dependencies(content, file_path)

        except Exception:  # nosec
            pass

        return deps

    def _extract_python_dependencies(
        self, content: str, file_path: Path
    ) -> Dict[str, List[str]]:
        """Extract dependencies from Python code.

        Uses AST parsing with regex fallback for syntax errors.

        Args:
            content: String content of the Python file.
            file_path: Path to the file being analyzed.

        Returns:
            Dictionary with 'internal' and 'external' dependency lists.
        """
        deps: Dict[str, List[str]] = {"internal": [], "external": []}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if self._is_internal_module(alias.name, file_path):
                            deps["internal"].append(alias.name)
                        else:
                            deps["external"].append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                    if module:
                        if self._is_internal_module(module, file_path):
                            deps["internal"].append(module)
                        else:
                            deps["external"].append(module)

        except SyntaxError:
            # Fallback to regex for syntax errors
            import_pattern = re.compile(r"(?:from\s+(\S+)\s+import|import\s+(\S+))")
            for match in import_pattern.finditer(content):
                module = match.group(1) or match.group(2)
                if self._is_internal_module(module, file_path):
                    deps["internal"].append(module)
                else:
                    deps["external"].append(module)

        return deps

    def _extract_javascript_dependencies(
        self, content: str, file_path: Path
    ) -> Dict[str, List[str]]:
        """Extract dependencies from JavaScript/TypeScript code.

        Uses regex to match import statements and require calls.

        Args:
            content: String content of the JavaScript/TypeScript file.
            file_path: Path to the file being analyzed.

        Returns:
            Dictionary with 'internal' and 'external' dependency lists.
        """
        deps: Dict[str, List[str]] = {"internal": [], "external": []}

        # Match import statements and require calls
        import_patterns = [
            re.compile(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'),
            re.compile(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'),
            re.compile(r'import\s*\(\s*["\']([^"\']+)["\']\s*\)'),  # Dynamic imports
        ]

        for pattern in import_patterns:
            for match in pattern.finditer(content):
                module = match.group(1)
                if self._is_internal_module(module, file_path):
                    deps["internal"].append(module)
                else:
                    deps["external"].append(module)

        return deps

    def _is_internal_module(self, module: str, file_path: Path) -> bool:
        """Check if a module is internal to the project.

        Args:
            module: Module name to check.
            file_path: Current file path for context.

        Returns:
            True if the module is internal to the project, False if external.
        """
        # Relative imports are internal
        if module.startswith("."):
            return True

        # Check if module exists in project structure
        project_root = self._find_project_root(file_path)
        if project_root:
            # Convert module path to file path
            module_parts = module.split(".")
            potential_paths = [
                project_root / ("/".join(module_parts) + ".py"),
                project_root / "/".join(module_parts) / "__init__.py",
                project_root / ("/".join(module_parts) + ".js"),
                project_root / ("/".join(module_parts) + ".ts"),
                project_root / "/".join(module_parts) / "index.js",
                project_root / "/".join(module_parts) / "index.ts",
            ]

            return any(p.exists() for p in potential_paths)

        return False

    def _find_project_root(self, file_path: Path) -> Optional[Path]:
        """Find the project root directory.

        Searches up the directory tree for common project root indicators.

        Args:
            file_path: Starting file path.

        Returns:
            Path to project root if found, None otherwise.
        """
        current = file_path.parent if file_path.is_file() else file_path

        while current != current.parent:
            # Look for common project root indicators
            if any(
                (current / indicator).exists()
                for indicator in [
                    "setup.py",
                    "pyproject.toml",
                    "package.json",
                    ".git",
                    "Makefile",
                ]
            ):
                return current
            current = current.parent

        return None

    def _detect_circular_dependencies(
        self, dependencies: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """Detect circular dependencies in the dependency graph.

        Uses depth-first search to find cycles in the dependency graph.

        Args:
            dependencies: Dictionary mapping file/module names to their dependencies.

        Returns:
            List of cycles, where each cycle is a list of file/module names.
        """
        circular_deps = []

        def dfs(
            node: str, path: List[str], visited: Set[str], rec_stack: Set[str]
        ) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, []):
                if neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in circular_deps:
                        circular_deps.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, path.copy(), visited, rec_stack)

            rec_stack.remove(node)

        visited: Set[str] = set()
        for node in dependencies:
            if node not in visited:
                dfs(node, [], visited, set())

        return circular_deps

    async def _analyze_structure(
        self,
        path: Path,
        language: str,
        depth: int,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Analyze the structural organization of the codebase.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            depth: Maximum depth for directory tree analysis.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing hierarchy, modules, packages, entry points,
            test files, documentation, configuration, and structural metrics.
        """
        structure: Dict[str, Any] = {
            "hierarchy": {},
            "modules": [],
            "packages": [],
            "entry_points": [],
            "test_files": [],
            "documentation": [],
            "configuration": [],
            "metrics": {},
        }

        if path.is_file():
            # Single file analysis
            structure["modules"] = [self._analyze_single_file(path)]
        else:
            # Directory analysis
            structure["hierarchy"] = self._build_directory_tree(
                path, depth, include_patterns, exclude_patterns
            )

            for file_path in path.rglob("*"):
                if not file_path.is_file() or not self._should_include_file(
                    file_path, include_patterns, exclude_patterns
                ):
                    continue

                rel_path = str(file_path.relative_to(path))
                file_info = self._analyze_single_file(file_path)

                # Classify files
                if self._is_test_file(file_path):
                    structure["test_files"].append(rel_path)
                elif self._is_documentation_file(file_path):
                    structure["documentation"].append(rel_path)
                elif self._is_configuration_file(file_path):
                    structure["configuration"].append(rel_path)
                elif self._is_entry_point(file_path):
                    structure["entry_points"].append(rel_path)
                elif file_path.is_dir() or (file_path / "__init__.py").exists():
                    structure["packages"].append(rel_path)
                else:
                    structure["modules"].append(file_info)

        # Calculate structural metrics
        structure["metrics"] = {
            "total_modules": len(structure["modules"]),
            "total_packages": len(structure["packages"]),
            "test_coverage_files": len(structure["test_files"]),
            "documentation_files": len(structure["documentation"]),
            "config_files": len(structure["configuration"]),
            "max_depth": self._calculate_max_depth(structure["hierarchy"]),
            "avg_files_per_directory": self._calculate_avg_files_per_dir(
                structure["hierarchy"]
            ),
        }

        return structure

    def _build_directory_tree(
        self,
        path: Path,
        max_depth: int,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
        current_depth: int = 0,
    ) -> Dict[str, Any]:
        """Build a tree representation of the directory structure.

        Args:
            path: Directory path to analyze.
            max_depth: Maximum depth to traverse.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.
            current_depth: Current recursion depth.

        Returns:
            Dictionary representing the directory tree with type, children,
            files, and size information.
        """
        if current_depth >= max_depth:
            return {}

        tree: Dict[str, Any] = {
            "type": "directory",
            "children": {},
            "files": [],
            "size": 0,
        }

        try:
            for item in path.iterdir():
                if item.name.startswith(".") and item.name not in [
                    ".env",
                    ".gitignore",
                ]:
                    continue

                if item.is_dir():
                    if not any(
                        self._matches_pattern(str(item), pattern)
                        for pattern in (exclude_patterns or [])
                    ):
                        children = tree.get("children", {})
                        if isinstance(children, dict):
                            children[item.name] = self._build_directory_tree(
                                item,
                                max_depth,
                                include_patterns,
                                exclude_patterns,
                                current_depth + 1,
                            )
                elif item.is_file() and self._should_include_file(
                    item, include_patterns, exclude_patterns
                ):
                    files = tree.get("files", [])
                    if isinstance(files, list):
                        files.append(
                            {
                                "name": item.name,
                                "size": item.stat().st_size,
                                "extension": item.suffix,
                            }
                        )
                    size = tree.get("size", 0)
                    if isinstance(size, (int, float)):
                        tree["size"] = size + item.stat().st_size

        except PermissionError:
            pass

        return tree

    def _is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file.

        Args:
            file_path: Path to check.

        Returns:
            True if the file appears to be a test file based on naming conventions.
        """
        name_lower = file_path.name.lower()
        return any(
            pattern in name_lower for pattern in ["test", "spec", "_test", ".test"]
        )

    def _is_documentation_file(self, file_path: Path) -> bool:
        """Check if a file is documentation.

        Args:
            file_path: Path to check.

        Returns:
            True if the file appears to be documentation based on name or extension.
        """
        name_lower = file_path.name.lower()
        return any(
            pattern in name_lower
            for pattern in ["readme", "doc", "docs", ".md", ".txt"]
        ) or file_path.suffix.lower() in [".md", ".txt", ".rst"]

    def _is_configuration_file(self, file_path: Path) -> bool:
        """Check if a file is a configuration file.

        Args:
            file_path: Path to check.

        Returns:
            True if the file appears to be a configuration file.
        """
        name_lower = file_path.name.lower()
        return any(
            pattern in name_lower for pattern in ["config", "settings", ".env", "setup"]
        ) or file_path.suffix.lower() in [
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
        ]

    def _is_entry_point(self, file_path: Path) -> bool:
        """Check if a file is likely an entry point.

        Args:
            file_path: Path to check.

        Returns:
            True if the file appears to be an application entry point.
        """
        name_lower = file_path.name.lower()
        return name_lower in [
            "main.py",
            "app.py",
            "index.js",
            "index.ts",
            "server.js",
            "run.py",
        ]

    def _calculate_max_depth(self, hierarchy: Dict[str, Any]) -> int:
        """Calculate the maximum depth of the directory tree.

        Args:
            hierarchy: Directory tree structure.

        Returns:
            Maximum depth of the tree.
        """
        if not hierarchy or "children" not in hierarchy:
            return 0

        max_child_depth = 0
        for child in hierarchy["children"].values():
            child_depth = self._calculate_max_depth(child)
            max_child_depth = max(max_child_depth, child_depth)

        return 1 + max_child_depth

    def _calculate_avg_files_per_dir(self, hierarchy: Dict[str, Any]) -> float:
        """Calculate average number of files per directory.

        Args:
            hierarchy: Directory tree structure.

        Returns:
            Average number of files per directory.
        """
        total_files = 0
        total_dirs = 0

        def count_files_and_dirs(node: Dict[str, Any]) -> Tuple[int, int]:
            if "files" not in node:
                return 0, 0

            files = len(node["files"])
            dirs = 1  # Current directory

            for child in node.get("children", {}).values():
                child_files, child_dirs = count_files_and_dirs(child)
                files += child_files
                dirs += child_dirs

            return files, dirs

        total_files, total_dirs = count_files_and_dirs(hierarchy)
        return total_files / max(total_dirs, 1)

    async def _analyze_patterns(
        self,
        path: Path,
        language: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Analyze design patterns and architectural patterns in the code.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing identified design patterns, architectural patterns,
            anti-patterns, code smells, and recommendations.
        """
        patterns: Dict[str, Any] = {
            "design_patterns": {},
            "architectural_patterns": {},
            "anti_patterns": {},
            "code_smells": [],
            "recommendations": [],
        }

        # This is a simplified pattern detection - could be greatly enhanced
        patterns["design_patterns"] = {
            "singleton": [],
            "factory": [],
            "observer": [],
            "decorator": [],
            "adapter": [],
        }

        patterns["architectural_patterns"] = {
            "mvc": False,
            "layered": False,
            "microservices": False,
            "rest_api": False,
        }

        patterns["anti_patterns"] = {
            "god_class": [],
            "long_method": [],
            "duplicate_code": [],
            "magic_numbers": [],
        }

        # Placeholder for pattern detection logic
        patterns["recommendations"] = [
            "Consider implementing proper separation of concerns",
            "Review large files for potential refactoring opportunities",
            "Ensure consistent naming conventions across the codebase",
        ]

        return patterns

    async def _analyze_metrics(
        self,
        path: Path,
        language: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Calculate various code metrics.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing size metrics, complexity metrics,
            quality metrics, and maintainability assessment.
        """
        metrics: Dict[str, Any] = {
            "size_metrics": {},
            "complexity_metrics": {},
            "quality_metrics": {},
            "maintainability": {},
        }

        total_files = 0
        total_lines = 0
        total_functions = 0
        total_classes = 0
        complexity_scores = []

        files_to_analyze = []
        if path.is_file():
            files_to_analyze = [path]
        else:
            files_to_analyze = [
                f
                for f in path.rglob("*")
                if f.is_file()
                and self._should_include_file(f, include_patterns, exclude_patterns)
            ]

        for file_path in files_to_analyze:
            file_info = self._analyze_single_file(file_path)
            total_files += 1
            total_lines += file_info.get("lines", 0)
            total_functions += len(file_info.get("functions", []))
            total_classes += len(file_info.get("classes", []))

            # Simple complexity score based on file size and structure
            complexity_score = (
                file_info.get("lines", 0) * 0.1
                + len(file_info.get("functions", [])) * 2
                + len(file_info.get("classes", [])) * 3
            )
            complexity_scores.append(complexity_score)

        metrics["size_metrics"] = {
            "total_files": total_files,
            "total_lines": total_lines,
            "avg_lines_per_file": total_lines / max(total_files, 1),
            "largest_files": [],  # Would need more detailed analysis
            "smallest_files": [],
        }

        metrics["complexity_metrics"] = {
            "total_functions": total_functions,
            "total_classes": total_classes,
            "avg_functions_per_file": total_functions / max(total_files, 1),
            "avg_classes_per_file": total_classes / max(total_files, 1),
            "complexity_distribution": {
                "low": len([s for s in complexity_scores if s < 50]),
                "medium": len([s for s in complexity_scores if 50 <= s < 150]),
                "high": len([s for s in complexity_scores if s >= 150]),
            },
        }

        metrics["quality_metrics"] = {
            "code_to_test_ratio": "unknown",  # Would need test file analysis
            "documentation_coverage": "unknown",
            "dependency_health": "unknown",
        }

        # Simple maintainability index
        avg_complexity = sum(complexity_scores) / max(len(complexity_scores), 1)
        if avg_complexity < 50:
            maintainability_score = "high"
        elif avg_complexity < 100:
            maintainability_score = "medium"
        else:
            maintainability_score = "low"

        metrics["maintainability"] = {
            "score": maintainability_score,
            "avg_complexity": avg_complexity,
            "factors": [],
        }

        return metrics

    async def _analyze_health(
        self,
        path: Path,
        language: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Analyze overall codebase health and quality.

        Combines various analyses to provide an overall health assessment.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing overall score, category scores,
            identified issues, and recommendations.
        """
        health: Dict[str, Any] = {
            "overall_score": 0,
            "categories": {},
            "issues": [],
            "recommendations": [],
            "trends": {},
        }

        # Get various analyses for health assessment
        structure = await self._analyze_structure(
            path, language, 2, include_patterns, exclude_patterns
        )
        metrics = await self._analyze_metrics(
            path, language, include_patterns, exclude_patterns
        )
        dependencies = await self._analyze_dependencies(
            path, language, 2, include_patterns, exclude_patterns
        )

        # Score different aspects (0 - 100)
        scores = {}

        # Structure score
        max_depth = structure["metrics"].get("max_depth", 0)
        if max_depth <= 3:
            scores["structure"] = 90
        elif max_depth <= 5:
            scores["structure"] = 70
        else:
            scores["structure"] = 50

        # Complexity score
        complexity_dist = metrics["complexity_metrics"]["complexity_distribution"]
        total_files = (
            complexity_dist["low"] + complexity_dist["medium"] + complexity_dist["high"]
        )
        if total_files > 0:
            low_ratio = complexity_dist["low"] / total_files
            if low_ratio > 0.8:
                scores["complexity"] = 90
            elif low_ratio > 0.6:
                scores["complexity"] = 70
            else:
                scores["complexity"] = 50
        else:
            scores["complexity"] = 100

        # Dependency score
        circular_deps = len(dependencies["circular_dependencies"])
        if circular_deps == 0:
            scores["dependencies"] = 90
        elif circular_deps <= 2:
            scores["dependencies"] = 70
        else:
            scores["dependencies"] = 40

        # Documentation score
        doc_files = len(structure["documentation"])
        total_files = structure["metrics"]["total_modules"]
        if total_files > 0:
            doc_ratio = doc_files / total_files
            if doc_ratio > 0.3:
                scores["documentation"] = 90
            elif doc_ratio > 0.1:
                scores["documentation"] = 70
            else:
                scores["documentation"] = 40
        else:
            scores["documentation"] = 100

        # Test coverage score (basic estimation)
        test_files = len(structure["test_files"])
        if test_files > total_files * 0.5:
            scores["testing"] = 90
        elif test_files > total_files * 0.2:
            scores["testing"] = 70
        else:
            scores["testing"] = 40

        health["categories"] = scores
        health["overall_score"] = sum(scores.values()) / len(scores) if scores else 0

        # Generate issues and recommendations
        if scores.get("complexity", 0) < 70:
            issues = health.get("issues", [])
            if isinstance(issues, list):
                issues.append("High complexity detected in some files")
            recommendations = health.get("recommendations", [])
            if isinstance(recommendations, list):
                recommendations.append(
                    "Consider refactoring complex functions and classes"
                )

        if scores.get("dependencies", 0) < 70:
            issues = health.get("issues", [])
            if isinstance(issues, list):
                issues.append("Circular dependencies detected")
            recommendations = health.get("recommendations", [])
            if isinstance(recommendations, list):
                recommendations.append(
                    "Resolve circular dependencies to improve maintainability"
                )

        if scores.get("documentation", 0) < 70:
            issues = health.get("issues", [])
            if isinstance(issues, list):
                issues.append("Low documentation coverage")
            recommendations = health.get("recommendations", [])
            if isinstance(recommendations, list):
                recommendations.append("Add more documentation and README files")

        if scores.get("testing", 0) < 70:
            issues = health.get("issues", [])
            if isinstance(issues, list):
                issues.append("Insufficient test coverage")
            recommendations = health.get("recommendations", [])
            if isinstance(recommendations, list):
                recommendations.append("Add more unit tests and integration tests")

        return health

    async def _generate_diagram(
        self,
        path: Path,
        language: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Generate architectural diagrams and visualizations.

        Args:
            path: Path to analyze (file or directory).
            language: Primary programming language.
            include_patterns: List of glob patterns for files to include.
            exclude_patterns: List of glob patterns for files to exclude.

        Returns:
            Dictionary containing components, relationships, layers,
            and generated diagram code (Mermaid and GraphViz).
        """
        diagram: Dict[str, Any] = {
            "type": "architecture_diagram",
            "components": [],
            "relationships": [],
            "layers": [],
            "mermaid_code": "",
            "graphviz_code": "",
        }

        # Get dependency information for diagram
        dependencies = await self._analyze_dependencies(
            path, language, 2, include_patterns, exclude_patterns
        )
        structure = await self._analyze_structure(
            path, language, 2, include_patterns, exclude_patterns
        )

        # Build component list
        for module in structure["modules"][:20]:  # Limit to avoid clutter
            components = diagram.get("components", [])
            if isinstance(components, list):
                components.append(
                    {
                        "name": Path(module["path"]).stem,
                        "type": "module",
                        "functions": len(module.get("functions", [])),
                        "classes": len(module.get("classes", [])),
                    }
                )

        # Build relationships from dependencies
        for source, targets in dependencies["dependency_graph"].items():
            for target in targets.get("internal", [])[:5]:  # Limit connections
                relationships = diagram.get("relationships", [])
                if isinstance(relationships, list):
                    relationships.append(
                        {"from": Path(source).stem, "to": target, "type": "depends_on"}
                    )

        # Generate Mermaid diagram code
        diagram["mermaid_code"] = self._generate_mermaid_code(diagram)

        return diagram

    def _generate_mermaid_code(self, diagram: Dict[str, Any]) -> str:
        """Generate Mermaid diagram code.

        Args:
            diagram: Dictionary containing components and relationships.

        Returns:
            String containing Mermaid diagram syntax.
        """
        mermaid = "graph TD\n"

        # Add components
        for component in diagram["components"]:
            name = component["name"].replace("-", "_").replace(".", "_")
            label = f"{component['name']}"
            if component["classes"] > 0:
                label += f"\\n{component['classes']} classes"
            if component["functions"] > 0:
                label += f"\\n{component['functions']} functions"

            mermaid += f'    {name}["{label}"]\n'

        # Add relationships
        for rel in diagram["relationships"]:
            from_name = rel["from"].replace("-", "_").replace(".", "_")
            to_name = rel["to"].replace("-", "_").replace(".", "_")
            mermaid += f"    {from_name} --> {to_name}\n"

        return mermaid

    def _format_summary_output(
        self, results: Dict[str, Any], analysis_type: str
    ) -> str:
        """Format results as summary output.

        Args:
            results: Analysis results dictionary.
            analysis_type: Type of analysis performed.

        Returns:
            Formatted string with human-readable summary.
        """
        output = f"🏗️  Architecture Analysis: {analysis_type.title()}\n"
        output += "=" * 50 + "\n\n"

        if analysis_type == "overview":
            summary = results.get("summary", {})
            output += "Project Overview:\n"
            output += f"• Language: {results.get('language', 'unknown')}\n"
            output += f"• Total Files: {summary.get('total_files', 0)}\n"
            output += f"• Total Lines: {summary.get('total_lines', 0)}\n"
            output += (
                f"• Average File Size: {summary.get('avg_file_size', 0)} lines\n\n"
            )

            if results.get("architecture_files"):
                output += "Key Architecture Files:\n"
                for arch_file in results["architecture_files"][:10]:
                    output += f"• {arch_file['file']} ({arch_file['type']})\n"

        elif analysis_type == "dependencies":
            stats = results.get("statistics", {})
            output += "Dependency Analysis:\n"
            output += f"• Files Analyzed: {stats.get('files_analyzed', 0)}\n"
            output += (
                f"• Internal Dependencies: {stats.get('total_internal_deps', 0)}\n"
            )
            output += (
                f"• External Dependencies: {stats.get('total_external_deps', 0)}\n"
            )
            output += f"• Average Dependencies per File: {stats.get('avg_deps_per_file', 0):.1f}\n"  # noqa: E501
            if results.get("circular_dependencies"):
                output += f"\n⚠️  Circular Dependencies Found: {len(results['circular_dependencies'])}\n"  # noqa: E501
        elif analysis_type == "health":
            output += (
                f"Codebase Health Score: {results.get('overall_score', 0):.1f}/100\n\n"
            )

            categories = results.get("categories", {})
            for category, score in categories.items():
                status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
                output += f"{status} {category.title()}: {score:.1f}/100\n"

            issues = results.get("issues", [])
            if issues:
                output += "\nIssues Found:\n"
                for issue in issues:
                    output += f"• {issue}\n"

        return output

    def _format_detailed_output(
        self, results: Dict[str, Any], analysis_type: str
    ) -> str:
        """Format results as detailed output.

        Args:
            results: Analysis results dictionary.
            analysis_type: Type of analysis performed.

        Returns:
            Formatted string with summary plus full JSON details.
        """
        output = self._format_summary_output(results, analysis_type)
        output += "\n" + "=" * 50 + "\nDetailed Results:\n"
        output += json.dumps(results, indent=2)
        return output

    def _format_mermaid_output(
        self, results: Dict[str, Any], analysis_type: str
    ) -> str:
        """Format results as Mermaid diagram code.

        Args:
            results: Analysis results dictionary.
            analysis_type: Type of analysis performed.

        Returns:
            Mermaid diagram code or error message if not available.
        """
        if analysis_type == "diagram" and "mermaid_code" in results:
            mermaid_code = results["mermaid_code"]
            return str(mermaid_code)
        else:
            return f"Mermaid diagrams not available for analysis type: {analysis_type}"
