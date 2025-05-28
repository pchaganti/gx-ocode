#!/usr/bin/env python3
"""
Script to fix trailing whitespace and basic formatting issues.
"""

import os
import re
import sys
from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Fix whitespace issues in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix trailing whitespace
        lines = content.split("\n")
        fixed_lines = [line.rstrip() for line in lines]
        content = "\n".join(fixed_lines)

        # Ensure file ends with single newline
        if content and not content.endswith("\n"):
            content += "\n"

        # Fix multiple blank lines (max 2 consecutive)
        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        directory = Path.cwd() / "ocode_python"

    if not directory.exists():
        print(f"Directory not found: {directory}")
        return 1

    python_files = list(directory.rglob("*.py"))
    fixed_count = 0

    print(f"Fixing whitespace in {len(python_files)} Python files...")

    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue

        if fix_file(file_path):
            fixed_count += 1
            print(f"Fixed: {file_path}")

    print(f"Fixed {fixed_count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
