#!/usr/bin/env python3
"""
Simple linting script for OCode.
Checks common Python issues without external dependencies.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


class SimpleLinter:
    """Simple Python linter."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def check_file(self, file_path: Path) -> None:
        """Check a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check syntax
            try:
                ast.parse(content)
            except SyntaxError as e:
                self.errors.append(f"{file_path}:{e.lineno}: Syntax error: {e.msg}")
                return
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check line length (max 88 for black compatibility)
                if len(line) > 88:
                    self.warnings.append(f"{file_path}:{i}: Line too long ({len(line)} > 88)")
                
                # Check for trailing whitespace
                if line.endswith(' ') or line.endswith('\t'):
                    self.warnings.append(f"{file_path}:{i}: Trailing whitespace")
                
                # Check for common issues
                if 'import *' in line:
                    self.warnings.append(f"{file_path}:{i}: Star import used")
                
                # Check for bare except
                if re.match(r'\s*except\s*:', line):
                    self.warnings.append(f"{file_path}:{i}: Bare except clause")
        
        except Exception as e:
            self.errors.append(f"{file_path}: Failed to read file: {e}")
    
    def check_imports(self, file_path: Path) -> None:
        """Check for unused imports (basic check)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find imports
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
                    for alias in node.names:
                        imports.append(alias.name)
            
            # Check if imports are used (very basic check)
            for imp in imports:
                if imp not in ['__future__'] and imp not in content.replace(f'import {imp}', ''):
                    continue  # Skip complex unused import detection for now
        
        except Exception:
            pass  # Skip import checking on errors
    
    def run(self, directory: Path) -> int:
        """Run linter on directory."""
        python_files = list(directory.rglob("*.py"))
        
        print(f"Checking {len(python_files)} Python files...")
        
        for file_path in python_files:
            # Skip test files and __pycache__
            if '__pycache__' in str(file_path) or '.pytest_cache' in str(file_path):
                continue
            
            self.check_file(file_path)
        
        # Report results
        if self.errors:
            print(f"\n❌ {len(self.errors)} errors found:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} warnings found:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ No issues found!")
            return 0
        
        return 1 if self.errors else 0


def main():
    """Main function."""
    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        directory = Path.cwd() / "ocode_python"
    
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return 1
    
    linter = SimpleLinter()
    return linter.run(directory)


if __name__ == "__main__":
    sys.exit(main())