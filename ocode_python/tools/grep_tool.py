"""
Advanced text and code searching tool with regex support.
"""

import re
import asyncio
import ast
from pathlib import Path
from typing import List, Optional, Dict, Any, Pattern, Union, Set

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class GrepTool(Tool):
    """Tool for advanced text and code searching with regex support."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="grep",
            description="Search for patterns in files using regular expressions",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Search pattern (regex supported)",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to search in (file or directory)",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="file_pattern",
                    type="string",
                    description="File pattern to filter files (e.g., '*.py', '*.{js,ts}')",
                    required=False,
                    default="*"
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Search recursively in subdirectories",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="boolean",
                    description="Case-sensitive search",
                    required=False,
                    default=True
                ),
                ToolParameter(
                    name="whole_word",
                    type="boolean",
                    description="Match whole words only",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="invert_match",
                    type="boolean",
                    description="Show lines that don't match the pattern",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="context_lines",
                    type="number",
                    description="Number of context lines to show around matches",
                    required=False,
                    default=0
                ),
                ToolParameter(
                    name="max_matches",
                    type="number",
                    description="Maximum number of matches to return",
                    required=False,
                    default=100
                ),
                ToolParameter(
                    name="include_line_numbers",
                    type="boolean",
                    description="Include line numbers in output",
                    required=False,
                    default=True
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute text search."""
        try:
            pattern = kwargs.get('pattern')
            path = kwargs.get('path', '.')
            file_pattern = kwargs.get('file_pattern', '*')
            recursive = kwargs.get('recursive', True)
            case_sensitive = kwargs.get('case_sensitive', True)
            whole_word = kwargs.get('whole_word', False)
            invert_match = kwargs.get('invert_match', False)
            context_lines = kwargs.get('context_lines', 0)
            max_matches = kwargs.get('max_matches', 100)
            include_line_numbers = kwargs.get('include_line_numbers', True)

            search_path = Path(path).resolve()
            
            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Search path does not exist: {path}"
                )

            # Compile regex pattern
            regex_flags = 0 if case_sensitive else re.IGNORECASE
            
            if whole_word:
                pattern = f"\\b{pattern}\\b"
            
            try:
                compiled_pattern = re.compile(pattern, regex_flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid regex pattern: {str(e)}"
                )

            # Find files to search
            files_to_search = []
            
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                files_to_search = self._find_files(search_path, file_pattern, recursive)

            # Search in files
            all_matches: List[Dict[str, Any]] = []
            files_searched = 0
            
            for file_path in files_to_search:
                try:
                    matches = await self._search_file(
                        file_path, compiled_pattern, invert_match, 
                        context_lines, include_line_numbers
                    )
                    
                    if matches:
                        all_matches.extend(matches)
                        
                    files_searched += 1
                    
                    # Stop if we hit max matches
                    if len(all_matches) >= max_matches:
                        all_matches = all_matches[:max_matches]
                        break
                        
                except Exception as e:
                    # Skip files that can't be read
                    continue

            # Format output
            if not all_matches:
                output = f"No matches found for pattern: {pattern}"
            else:
                output_lines = [
                    f"Found {len(all_matches)} matches in {files_searched} files:",
                    ""
                ]
                
                current_file = None
                for match in all_matches:
                    if match["file"] != current_file:
                        current_file = match["file"]
                        relative_path = Path(current_file).relative_to(search_path.parent if search_path.is_file() else search_path)
                        output_lines.append(f"📄 {relative_path}:")
                    
                    if include_line_numbers:
                        output_lines.append(f"  {match['line_num']:4d}: {match['text']}")
                    else:
                        output_lines.append(f"  {match['text']}")
                    
                    # Add context lines if any
                    for context in match.get("context", []):
                        if include_line_numbers:
                            output_lines.append(f"  {context['line_num']:4d}| {context['text']}")
                        else:
                            output_lines.append(f"      | {context['text']}")

                if len(all_matches) >= max_matches:
                    output_lines.append(f"\n... truncated at {max_matches} matches")
                
                output = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": pattern,
                    "matches_found": len(all_matches),
                    "files_searched": files_searched,
                    "search_path": str(search_path),
                    "matches": all_matches[:50]  # Limit metadata size
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )

    def _find_files(self, base_path: Path, file_pattern: str, recursive: bool) -> List[Path]:
        """Find files matching the pattern."""
        import fnmatch
        
        files = []
        
        if recursive:
            for file_path in base_path.rglob("*"):
                if file_path.is_file() and fnmatch.fnmatch(file_path.name, file_pattern):
                    files.append(file_path)
        else:
            for file_path in base_path.iterdir():
                if file_path.is_file() and fnmatch.fnmatch(file_path.name, file_pattern):
                    files.append(file_path)
        
        return sorted(files)

    async def _search_file(self, file_path: Path, pattern: Pattern[str], 
                          invert_match: bool, context_lines: int,
                          include_line_numbers: bool) -> List[Dict[str, Any]]:
        """Search for pattern in a single file."""
        matches: List[Dict[str, Any]] = []
        
        try:
            # Try to read as text file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return matches

        # Search through lines
        for i, line in enumerate(lines):
            line_stripped = line.rstrip('\n\r')
            found_match = bool(pattern.search(line_stripped))
            
            if found_match != invert_match:  # XOR logic for invert_match
                match_info: Dict[str, Any] = {
                    "file": str(file_path),
                    "line_num": i + 1,
                    "text": line_stripped,
                    "context": []
                }
                
                # Add context lines if requested
                if context_lines > 0:
                    start_line = max(0, i - context_lines)
                    end_line = min(len(lines), i + context_lines + 1)
                    
                    for ctx_i in range(start_line, end_line):
                        if ctx_i != i:  # Don't include the match line itself
                            match_info["context"].append({
                                "line_num": ctx_i + 1,
                                "text": lines[ctx_i].rstrip('\n\r')
                            })
                
                matches.append(match_info)
        
        return matches


class CodeGrepTool(GrepTool):
    """Enhanced grep tool specifically designed for code searching."""

    def __init__(self):
        super().__init__()
        self._comment_patterns = {
            'python': (r'#.*$', r'""".*?"""', r"'''.*?'''"),
            'javascript': (r'//.*$', r'/\*.*?\*/'),
            'typescript': (r'//.*$', r'/\*.*?\*/'),
        }
        self._string_patterns = {
            'python': (r'""".*?"""', r"'''.*?'''", r'".*?"', r"'.*?'"),
            'javascript': (r'".*?"', r"'.*?'", r'`.*?`'),
            'typescript': (r'".*?"', r"'.*?'", r'`.*?`'),
        }

    @property  
    def definition(self) -> ToolDefinition:
        base_def = super().definition
        base_def.name = "code_grep"
        base_def.description = "Search for code patterns with language-aware features"
        base_def.parameters.extend([
            ToolParameter(
                name="language",
                type="string", 
                description="Programming language for syntax-aware search (python, javascript, etc.)",
                required=False
            ),
            ToolParameter(
                name="search_type",
                type="string",
                description="Type of search: 'function', 'class', 'variable', 'import', 'comment', 'string'",
                required=False,
                default="text"
            ),
            ToolParameter(
                name="exclude_comments",
                type="boolean",
                description="Exclude matches in comments",
                required=False,
                default=False
            ),
            ToolParameter(
                name="exclude_strings",
                type="boolean",
                description="Exclude matches in string literals",
                required=False,
                default=False
            )
        ])
        return base_def

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute code-aware search."""
        
        # Extract parameters
        pattern = kwargs.get('pattern')
        path = kwargs.get('path', '.')
        file_pattern = kwargs.get('file_pattern', '*')
        recursive = kwargs.get('recursive', True)
        case_sensitive = kwargs.get('case_sensitive', True)
        whole_word = kwargs.get('whole_word', False)
        invert_match = kwargs.get('invert_match', False)
        context_lines = kwargs.get('context_lines', 0)
        max_matches = kwargs.get('max_matches', 100)
        include_line_numbers = kwargs.get('include_line_numbers', True)
        language = kwargs.get('language')
        search_type = kwargs.get('search_type', 'text')
        exclude_comments = kwargs.get('exclude_comments', False)
        exclude_strings = kwargs.get('exclude_strings', False)
        
        # Enhanced language-specific parsing
        if search_type != "text":
            # Create language-specific patterns
            if search_type == "function":
                if language == "python":
                    pattern = f"(?:def|async\\s+def)\\s+{pattern}\\s*\\("
                elif language in ["javascript", "typescript"]:
                    pattern = f"(?:function\\s+{pattern}\\s*\\(|const\\s+{pattern}\\s*=\\s*(?:async\\s+)?(?:function|\\([^)]*\\)\\s*=>)|{pattern}\\s*:\\s*(?:async\\s+)?(?:function|\\([^)]*\\)\\s*=>))"
                elif language == "java":
                    pattern = f"(?:public|private|protected|static|\\s)+\\w+\\s+{pattern}\\s*\\("
                elif language == "go":
                    pattern = f"func\\s+(?:\\([^)]+\\)\\s+)?{pattern}\\s*\\("
                elif language == "rust":
                    pattern = f"fn\\s+{pattern}\\s*[<(]"
            elif search_type == "class":
                if language == "python":
                    pattern = f"class\\s+{pattern}\\s*[\\(:]"
                elif language in ["javascript", "typescript"]:
                    pattern = f"class\\s+{pattern}\\s*(?:extends\\s+\\w+\\s*)?[{{\\s]"
                elif language == "java":
                    pattern = f"(?:public\\s+)?class\\s+{pattern}\\s*(?:extends\\s+\\w+\\s*)?(?:implements\\s+[\\w,\\s]+\\s*)?\\{{"
                elif language == "go":
                    pattern = f"type\\s+{pattern}\\s+struct\\s*\\{{"
                elif language == "rust":
                    pattern = f"(?:pub\\s+)?struct\\s+{pattern}\\s*[{{<]"
            elif search_type == "import":
                if language == "python":
                    pattern = f"(?:import\\s+{pattern}|from\\s+{pattern}\\s+import|from\\s+\\S+\\s+import.*{pattern})"
                elif language in ["javascript", "typescript"]:
                    pattern = f"(?:import.*from\\s+['\"].*{pattern}.*['\"]|import\\s+.*{pattern}|require\\(['\"].*{pattern}.*['\"]\\))"
                elif language == "java":
                    pattern = f"import\\s+(?:static\\s+)?.*{pattern}"
                elif language == "go":
                    pattern = f"import\\s+(?:\\(.*{pattern}.*\\)|['\"].*{pattern}.*['\"])"
                elif language == "rust":
                    pattern = f"use\\s+.*{pattern}"
            elif search_type == "variable":
                if language == "python":
                    pattern = f"(?:{pattern}\\s*=|self\\.{pattern}\\s*=)"
                elif language in ["javascript", "typescript"]:
                    pattern = f"(?:(?:let|const|var)\\s+{pattern}\\s*[=;]|this\\.{pattern}\\s*=)"
                elif language == "java":
                    pattern = f"(?:(?:public|private|protected|static|final|\\s)+)?\\w+\\s+{pattern}\\s*[=;]"
                elif language == "go":
                    pattern = f"(?:{pattern}\\s*:=|var\\s+{pattern}\\s+)"
                elif language == "rust":
                    pattern = f"(?:let\\s+(?:mut\\s+)?{pattern}\\s*[=;])"
            elif search_type == "comment":
                if language == "python":
                    pattern = f"#.*{pattern}"
                elif language in ["javascript", "typescript", "java", "go", "rust"]:
                    pattern = f"(?://.*{pattern}|/\\*.*{pattern}.*\\*/)"
            elif search_type == "string":
                if language == "python":
                    pattern = f"(?:['\"].*{pattern}.*['\"]|['\"]['\"]['\"].*{pattern}.*['\"]['\"]['\"])"
                elif language in ["javascript", "typescript"]:
                    pattern = f"(?:['\"].*{pattern}.*['\"]|`.*{pattern}.*`)"
                else:
                    pattern = f"['\"].*{pattern}.*['\"]"

        # Use enhanced search if we have language info
        if language or exclude_comments or exclude_strings:
            return await self._enhanced_search(
                pattern=pattern,
                path=path,
                file_pattern=file_pattern,
                recursive=recursive,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                invert_match=invert_match,
                context_lines=context_lines,
                max_matches=max_matches,
                include_line_numbers=include_line_numbers,
                language=language,
                exclude_comments=exclude_comments,
                exclude_strings=exclude_strings
            )
        else:
            # Fall back to parent implementation
            return await super().execute(
                pattern=pattern,
                path=path,
                file_pattern=file_pattern,
                recursive=recursive,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                invert_match=invert_match,
                context_lines=context_lines,
                max_matches=max_matches,
                include_line_numbers=include_line_numbers
            )

    async def _search_file(self, file_path: Path, pattern: Pattern[str], 
                          invert_match: bool, context_lines: int,
                          include_line_numbers: bool, exclude_comments: bool = False,
                          exclude_strings: bool = False) -> List[Dict[str, Any]]:
        """Enhanced file search with language-specific parsing."""
        matches: List[Dict[str, Any]] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception:
            return matches

        # Determine language from file extension
        ext = file_path.suffix.lower()
        if ext == '.py':
            language = 'python'
        elif ext in ['.js', '.jsx']:
            language = 'javascript'
        elif ext in ['.ts', '.tsx']:
            language = 'typescript'
        else:
            # Fall back to basic search for unknown languages
            return await super()._search_file(file_path, pattern, invert_match, 
                                            context_lines, include_line_numbers)

        # Parse code based on language
        if language == 'python':
            try:
                tree = ast.parse(content)
                # Get line ranges for different code elements
                comment_ranges = self._get_python_comment_ranges(content)
                string_ranges = self._get_python_string_ranges(tree)
                
                # Search through lines with context
                for i, line in enumerate(lines):
                    line_stripped = line.rstrip('\n\r')
                    
                    # Skip if line is in a comment or string if requested
                    if (exclude_comments and self._is_in_range(i + 1, comment_ranges) or
                        exclude_strings and self._is_in_range(i + 1, string_ranges)):
                        continue
                    
                    found_match = bool(pattern.search(line_stripped))
                    if found_match != invert_match:
                        match_info = self._create_match_info(file_path, i, line_stripped, 
                                                           lines, context_lines, include_line_numbers)
                        matches.append(match_info)
                        
            except SyntaxError:
                # Fall back to basic search if parsing fails
                return await super()._search_file(file_path, pattern, invert_match, 
                                                context_lines, include_line_numbers)
                
        else:  # JavaScript/TypeScript
            # Basic JS/TS parsing using regex
            comment_ranges = self._get_js_comment_ranges(content)
            string_ranges = self._get_js_string_ranges(content)
            
            for i, line in enumerate(lines):
                line_stripped = line.rstrip('\n\r')
                
                # Skip if line is in a comment or string if requested
                if (exclude_comments and self._is_in_range(i + 1, comment_ranges) or
                    exclude_strings and self._is_in_range(i + 1, string_ranges)):
                    continue
                
                found_match = bool(pattern.search(line_stripped))
                if found_match != invert_match:
                    match_info = self._create_match_info(file_path, i, line_stripped, 
                                                       lines, context_lines, include_line_numbers)
                    matches.append(match_info)
        
        return matches

    def _get_python_comment_ranges(self, content: str) -> List[tuple]:
        """Get line ranges for Python comments."""
        ranges = []
        for pattern in self._comment_patterns['python']:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start_line = content[:match.start()].count('\n') + 1
                end_line = content[:match.end()].count('\n') + 1
                ranges.append((start_line, end_line))
        return ranges

    def _get_python_string_ranges(self, tree: ast.AST) -> List[tuple]:
        """Get line ranges for Python string literals."""
        ranges = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Str, ast.JoinedStr)):
                ranges.append((node.lineno, node.end_lineno))
        return ranges

    def _get_js_comment_ranges(self, content: str) -> List[tuple]:
        """Get line ranges for JavaScript/TypeScript comments."""
        ranges = []
        for pattern in self._comment_patterns['javascript']:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start_line = content[:match.start()].count('\n') + 1
                end_line = content[:match.end()].count('\n') + 1
                ranges.append((start_line, end_line))
        return ranges

    def _get_js_string_ranges(self, content: str) -> List[tuple]:
        """Get line ranges for JavaScript/TypeScript string literals."""
        ranges = []
        for pattern in self._string_patterns['javascript']:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start_line = content[:match.start()].count('\n') + 1
                end_line = content[:match.end()].count('\n') + 1
                ranges.append((start_line, end_line))
        return ranges

    def _is_in_range(self, line_num: int, ranges: List[tuple]) -> bool:
        """Check if a line number falls within any of the given ranges."""
        return any(start <= line_num <= end for start, end in ranges)

    def _create_match_info(self, file_path: Path, line_num: int, line_text: str,
                          all_lines: List[str], context_lines: int,
                          include_line_numbers: bool) -> Dict[str, Any]:
        """Create a match info dictionary with context."""
        match_info = {
            "file": str(file_path),
            "line_num": line_num + 1,
            "text": line_text,
            "context": []
        }
        
        if context_lines > 0:
            start_line = max(0, line_num - context_lines)
            end_line = min(len(all_lines), line_num + context_lines + 1)
            
            for ctx_i in range(start_line, end_line):
                if ctx_i != line_num:
                    match_info["context"].append({
                        "line_num": ctx_i + 1,
                        "text": all_lines[ctx_i].rstrip('\n\r')
                    })
        
        return match_info
    
    async def _enhanced_search(self, **kwargs: Any) -> ToolResult:
        """Enhanced search with language-specific features."""
        try:
            pattern = kwargs.get('pattern')
            path = kwargs.get('path', '.')
            file_pattern = kwargs.get('file_pattern', '*')
            recursive = kwargs.get('recursive', True)
            case_sensitive = kwargs.get('case_sensitive', True)
            whole_word = kwargs.get('whole_word', False)
            invert_match = kwargs.get('invert_match', False)
            context_lines = kwargs.get('context_lines', 0)
            max_matches = kwargs.get('max_matches', 100)
            include_line_numbers = kwargs.get('include_line_numbers', True)
            language = kwargs.get('language')
            exclude_comments = kwargs.get('exclude_comments', False)
            exclude_strings = kwargs.get('exclude_strings', False)

            search_path = Path(path).resolve()
            
            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Search path does not exist: {path}"
                )

            # Compile regex pattern
            regex_flags = 0 if case_sensitive else re.IGNORECASE
            
            if whole_word:
                pattern = f"\\b{pattern}\\b"
            
            try:
                compiled_pattern = re.compile(pattern, regex_flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid regex pattern: {str(e)}"
                )

            # Find files to search
            files_to_search = []
            
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                files_to_search = self._find_files(search_path, file_pattern, recursive)

            # Apply language filter if specified
            if language:
                lang_extensions = {
                    'python': ['.py'],
                    'javascript': ['.js', '.jsx', '.mjs'],
                    'typescript': ['.ts', '.tsx'],
                    'java': ['.java'],
                    'go': ['.go'],
                    'rust': ['.rs'],
                    'c': ['.c', '.h'],
                    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h'],
                    'csharp': ['.cs'],
                    'ruby': ['.rb'],
                    'php': ['.php'],
                    'swift': ['.swift'],
                    'kotlin': ['.kt', '.kts'],
                    'scala': ['.scala'],
                    'r': ['.r', '.R'],
                    'julia': ['.jl'],
                    'perl': ['.pl', '.pm'],
                    'lua': ['.lua'],
                    'bash': ['.sh', '.bash'],
                    'powershell': ['.ps1'],
                    'sql': ['.sql'],
                    'html': ['.html', '.htm'],
                    'css': ['.css', '.scss', '.sass', '.less'],
                    'xml': ['.xml'],
                    'yaml': ['.yaml', '.yml'],
                    'json': ['.json'],
                    'markdown': ['.md', '.markdown'],
                }
                
                if language in lang_extensions:
                    extensions = lang_extensions[language]
                    files_to_search = [f for f in files_to_search if any(f.suffix.lower() == ext for ext in extensions)]

            # Search in files
            all_matches: List[Dict[str, Any]] = []
            files_searched = 0
            
            for file_path in files_to_search:
                try:
                    matches = await self._search_file(
                        file_path, compiled_pattern, invert_match, 
                        context_lines, include_line_numbers,
                        exclude_comments, exclude_strings
                    )
                    
                    if matches:
                        all_matches.extend(matches)
                        
                    files_searched += 1
                    
                    # Stop if we hit max matches
                    if len(all_matches) >= max_matches:
                        all_matches = all_matches[:max_matches]
                        break
                        
                except Exception as e:
                    # Skip files that can't be read
                    continue

            # Format output
            if not all_matches:
                output = f"No matches found for pattern: {pattern}"
                if language:
                    output += f" (language: {language})"
            else:
                output_lines = [
                    f"Found {len(all_matches)} matches in {files_searched} files:",
                    ""
                ]
                
                if language:
                    output_lines[0] += f" (language: {language})"
                
                current_file = None
                for match in all_matches:
                    if match["file"] != current_file:
                        current_file = match["file"]
                        relative_path = Path(current_file).relative_to(search_path.parent if search_path.is_file() else search_path)
                        output_lines.append(f"📄 {relative_path}:")
                    
                    if include_line_numbers:
                        output_lines.append(f"  {match['line_num']:4d}: {match['text']}")
                    else:
                        output_lines.append(f"  {match['text']}")
                    
                    # Add context lines if any
                    for context in match.get("context", []):
                        if include_line_numbers:
                            output_lines.append(f"  {context['line_num']:4d}| {context['text']}")
                        else:
                            output_lines.append(f"      | {context['text']}")

                if len(all_matches) >= max_matches:
                    output_lines.append(f"\n... truncated at {max_matches} matches")
                
                output = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": pattern,
                    "matches_found": len(all_matches),
                    "files_searched": files_searched,
                    "search_path": str(search_path),
                    "language": language,
                    "exclude_comments": exclude_comments,
                    "exclude_strings": exclude_strings,
                    "matches": all_matches[:50]  # Limit metadata size
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Enhanced search failed: {str(e)}"
            )