#!/usr/bin/env python3
"""Script to add Google-style docstrings to all public functions and classes."""

import ast
from pathlib import Path
from typing import List, Tuple


def needs_docstring(node) -> bool:
    """Check if a function or class node needs a docstring.

    Args:
        node: AST node to check.

    Returns:
        True if the node needs a docstring, False otherwise.
    """
    # Check if it's a public function/class (doesn't start with _)
    if (
        hasattr(node, "name")
        and node.name.startswith("_")
        and not node.name.startswith("__")
    ):
        return False

    # Check if it already has a docstring
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return False

    return True


def get_function_signature(node) -> str:
    """Extract function signature for documentation.

    Args:
        node: AST function node.

    Returns:
        String representation of function arguments.
    """
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    return ", ".join(args)


def find_missing_docstrings(file_path: Path) -> List[Tuple[str, int, str]]:
    """Find all functions and classes missing docstrings in a file.

    Args:
        file_path: Path to Python file to analyze.

    Returns:
        List of tuples (name, line_number, type) for items missing docstrings.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        missing = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if needs_docstring(node) and hasattr(node, "lineno"):
                    func_type = (
                        "async_function"
                        if isinstance(node, ast.AsyncFunctionDef)
                        else "function"
                    )
                    missing.append((node.name, node.lineno, func_type))
            elif isinstance(node, ast.ClassDef):
                if needs_docstring(node) and hasattr(node, "lineno"):
                    missing.append((node.name, node.lineno, "class"))

        return missing
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def scan_directory(directory: Path) -> None:  # noqa: C901
    """Scan directory for Python files missing docstrings.

    Args:
        directory: Root directory to scan.
    """
    all_missing = {}

    for py_file in directory.rglob("*.py"):
        # Skip test files and __pycache__
        if (
            "test" in py_file.parts
            or "__pycache__" in py_file.parts
            or "venv" in py_file.parts
            or ".venv" in py_file.parts
        ):
            continue

        missing = find_missing_docstrings(py_file)
        if missing:
            all_missing[py_file] = missing

    # Print summary
    total_missing = sum(len(items) for items in all_missing.values())
    print(f"\nTotal items missing docstrings: {total_missing}")
    print(f"Files with missing docstrings: {len(all_missing)}\n")

    # Group by module
    modules = {}
    for file_path, missing_items in all_missing.items():
        module = str(file_path).split("ocode_python/")[-1].split("/")[0]
        if module not in modules:
            modules[module] = []
        modules[module].extend([(file_path, item) for item in missing_items])

    # Print by module
    for module, items in sorted(modules.items()):
        print(f"\n{module.upper()} MODULE ({len(items)} items):")
        print("-" * 50)

        # Group by file
        by_file = {}
        for file_path, item in items:
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(item)

        for file_path, file_items in sorted(by_file.items()):
            rel_path = str(file_path).split("ocode_python/")[-1]
            print(f"\n  {rel_path}:")
            for name, line, item_type in sorted(file_items, key=lambda x: x[1]):
                print(f"    L{line:4d}: {item_type:14s} {name}")


if __name__ == "__main__":
    project_root = Path("/Users/jonathanhaas/ocode/ocode_python")
    scan_directory(project_root)
