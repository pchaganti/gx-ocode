#!/usr/bin/env python3
"""
Simple script to list all OCode tools for user verification.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ocode_python.tools.base import ToolRegistry


def main():
    """List all tools in a format similar to what OCode should show."""
    registry = ToolRegistry()
    registry.register_core_tools()

    tools = registry.get_all_tools()

    print(f"OCode has access to {len(tools)} tools:\n")

    # Sort tools by name for consistent output
    sorted_tools = sorted(tools, key=lambda t: t.definition.name)

    for i, tool in enumerate(sorted_tools, 1):
        definition = tool.definition
        print(f"{i:2d}. **{definition.name}**: {definition.description}")

    print(f"\nTotal: {len(tools)} tools available for use!")


if __name__ == "__main__":
    main()
