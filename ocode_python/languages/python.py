"""
Python language analyzer using AST.
"""

import ast
from pathlib import Path
from typing import List, Optional

from .base import (
    AnalysisResult,
    Import,
    LanguageAnalyzer,
    Symbol,
    SymbolType,
    language_registry,
)


def safe_unparse(node: ast.AST) -> str:
    """Safely unparse AST node, handling version compatibility.

    Uses ast.unparse on Python 3.9+, falls back to class name on older versions.

    Args:
        node: AST node to unparse.

    Returns:
        String representation of the node.
    """
    try:
        if hasattr(ast, "unparse"):
            result = ast.unparse(node)
            return str(result)
        else:
            # Fallback for Python < 3.9 - simple string representation
            return str(node.__class__.__name__)
    except Exception:
        return "<unknown>"


class PythonAnalyzer(LanguageAnalyzer):
    """Python language analyzer using AST parsing."""

    @property
    def file_extensions(self) -> List[str]:
        """File extensions handled by this analyzer.

        Returns:
            List of Python file extensions.
        """
        return [".py", ".pyw", ".pyi"]

    @property
    def comment_patterns(self) -> List[str]:
        """Comment patterns for Python.

        Returns:
            List containing the hash comment pattern.
        """
        return ["#"]

    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """Parse Python file using AST.

        Extracts symbols, imports, metrics, and dependencies from Python source.
        Handles syntax errors gracefully.

        Args:
            file_path: Path to the Python file.
            content: File content to parse.

        Returns:
            AnalysisResult with extracted information.
        """
        symbols = []
        imports = []
        syntax_errors = []

        try:
            tree = ast.parse(content, filename=str(file_path))

            # Extract symbols and imports
            visitor = PythonASTVisitor()
            visitor.visit(tree)

            symbols = visitor.symbols
            imports = visitor.imports

        except SyntaxError as e:
            syntax_errors.append(
                {
                    "message": str(e),
                    "line": e.lineno,
                    "column": e.offset,
                    "type": "syntax_error",
                }
            )
        except Exception as e:
            syntax_errors.append(
                {
                    "message": f"Parse error: {str(e)}",
                    "line": 0,
                    "column": 0,
                    "type": "parse_error",
                }
            )

        # Calculate metrics
        metrics = self.calculate_metrics(content, symbols)

        # Resolve dependencies
        dependencies = self.resolve_dependencies(imports, file_path.parent)

        return AnalysisResult(
            file_path=file_path,
            language="python",
            symbols=symbols,
            imports=imports,
            metrics=metrics,
            dependencies=dependencies,
            syntax_errors=syntax_errors,
        )

    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols using AST.

        Args:
            content: Python source code.

        Returns:
            List of Symbol objects found in the code.
        """
        try:
            tree = ast.parse(content)
            visitor = PythonASTVisitor()
            visitor.visit(tree)
            return visitor.symbols
        except Exception:
            return []

    def extract_imports(self, content: str) -> List[Import]:
        """Extract imports using AST.

        Args:
            content: Python source code.

        Returns:
            List of Import objects found in the code.
        """
        try:
            tree = ast.parse(content)
            visitor = PythonASTVisitor()
            visitor.visit(tree)
            return visitor.imports
        except Exception:
            return []


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python symbols and imports."""

    def __init__(self):
        """Initialize AST visitor.

        Sets up empty lists for symbols and imports, and tracking
        variables for current class and scope.
        """
        self.symbols: List[Symbol] = []
        self.imports: List[Import] = []
        self.current_class: Optional[str] = None
        self.scope_stack: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition.

        Extracts function information including parameters, return type,
        docstring, decorators, and visibility.

        Args:
            node: AST FunctionDef node.
        """
        # Determine if this is a method or function
        symbol_type = SymbolType.METHOD if self.current_class else SymbolType.FUNCTION

        # Get scope
        scope = ".".join(self.scope_stack) if self.scope_stack else None

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param = {"name": arg.arg}
            if arg.annotation:
                param["type"] = safe_unparse(arg.annotation)
            parameters.append(param)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = safe_unparse(node.returns)

        # Extract docstring
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(safe_unparse(decorator))

        # Determine visibility
        visibility = "private" if node.name.startswith("_") else "public"

        symbol = Symbol(
            name=node.name,
            type=symbol_type,
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno,
            end_column=node.end_col_offset,
            scope=scope,
            visibility=visibility,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            decorators=decorators if decorators else None,
        )

        self.symbols.append(symbol)

        # Visit children with updated scope
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition.

        Similar to regular functions but for async def statements.

        Args:
            node: AST AsyncFunctionDef node.
        """
        # Handle async function like regular function
        scope = ".".join(self.scope_stack) if self.scope_stack else ""

        # Extract parameters
        params = []
        for arg in node.args.args:
            param_info = {"name": arg.arg}
            if arg.annotation:
                param_info["type"] = safe_unparse(arg.annotation)
            params.append(param_info)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = safe_unparse(node.returns)

        # Extract docstring
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            if isinstance(node.body[0].value.value, str):
                docstring = node.body[0].value.value

        # Extract decorators
        decorators = (
            [safe_unparse(dec) for dec in node.decorator_list]
            if node.decorator_list
            else None
        )

        symbol = Symbol(
            name=node.name,
            type=SymbolType.FUNCTION,
            line=node.lineno,
            column=node.col_offset,
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
            scope=scope,
            parameters=params if params else None,
            return_type=return_type,
            docstring=docstring,
            decorators=decorators,
        )

        self.symbols.append(symbol)

        # Enter function scope
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition.

        Extracts class information including docstring, decorators,
        and tracks class context for method definitions.

        Args:
            node: AST ClassDef node.
        """
        # Get scope
        scope = ".".join(self.scope_stack) if self.scope_stack else None

        # Extract docstring
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(safe_unparse(decorator))

        # Determine visibility
        visibility = "private" if node.name.startswith("_") else "public"

        symbol = Symbol(
            name=node.name,
            type=SymbolType.CLASS,
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno,
            end_column=node.end_col_offset,
            scope=scope,
            visibility=visibility,
            docstring=docstring,
            decorators=decorators if decorators else None,
        )

        self.symbols.append(symbol)

        # Visit children with updated scope and class context
        old_class = self.current_class
        self.current_class = node.name
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
        self.current_class = old_class

    def visit_Assign(self, node: ast.Assign):
        """Visit assignment (for module-level variables).

        Only processes module-level assignments, detecting constants
        (all uppercase) and regular variables.

        Args:
            node: AST Assign node.
        """
        # Only handle module-level assignments (not inside functions/classes)
        if not self.scope_stack:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Determine if it's a constant (all uppercase)
                    symbol_type = (
                        SymbolType.CONSTANT
                        if target.id.isupper()
                        else SymbolType.VARIABLE
                    )
                    visibility = "private" if target.id.startswith("_") else "public"

                    symbol = Symbol(
                        name=target.id,
                        type=symbol_type,
                        line=node.lineno,
                        column=node.col_offset,
                        end_line=node.end_lineno,
                        end_column=node.end_col_offset,
                        visibility=visibility,
                    )

                    self.symbols.append(symbol)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit annotated assignment.

        Handles type-annotated assignments at module level.

        Args:
            node: AST AnnAssign node.
        """
        # Only handle module-level assignments
        if not self.scope_stack and isinstance(node.target, ast.Name):
            symbol_type = (
                SymbolType.CONSTANT if node.target.id.isupper() else SymbolType.VARIABLE
            )
            visibility = "private" if node.target.id.startswith("_") else "public"

            # Get type annotation
            return_type = safe_unparse(node.annotation) if node.annotation else None

            symbol = Symbol(
                name=node.target.id,
                type=symbol_type,
                line=node.lineno,
                column=node.col_offset,
                end_line=node.end_lineno,
                end_column=node.end_col_offset,
                visibility=visibility,
                return_type=return_type,
            )

            self.symbols.append(symbol)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Visit import statement.

        Handles 'import module' statements.

        Args:
            node: AST Import node.
        """
        for alias in node.names:
            import_obj = Import(module=alias.name, alias=alias.asname, line=node.lineno)
            self.imports.append(import_obj)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statement.

        Handles 'from module import item' statements, including
        relative imports.

        Args:
            node: AST ImportFrom node.
        """
        module = node.module or ""
        level = node.level or 0
        is_relative = level > 0

        # Handle "from . import" or "from .. import"
        if is_relative:
            module = "." * level + module

        items = []
        for alias in node.names:
            items.append(alias.name)

        import_obj = Import(
            module=module, items=items, line=node.lineno, is_relative=is_relative
        )
        self.imports.append(import_obj)

        self.generic_visit(node)


# Register the Python analyzer
python_analyzer = PythonAnalyzer()
language_registry.register(python_analyzer)
