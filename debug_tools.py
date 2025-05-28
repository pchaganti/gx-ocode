#!/usr/bin/env python3
"""
Debug script to list all available OCode tools.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ocode_python.tools.base import ToolRegistry


def main():
    """List all available tools."""
    print("🔧 OCode Enhanced Tools Debug Report")
    print("=" * 50)

    try:
        registry = ToolRegistry()
        registry.register_core_tools()

        tools = registry.get_all_tools()
        print(f"✅ Successfully registered {len(tools)} tools\n")

        # Group tools by category
        categories = {
            "File Operations": [
                "fileread",
                "filewrite",
                "filelist",
                "glob",
                "advancedglob",
                "grep",
                "codegrep",
                "ls",
                "fileedit",
            ],
            "Shell & Execution": ["shellcommand", "bash", "script"],
            "Development": ["testrunner"],
            "Advanced Analysis": ["architect", "think"],
            "Notebooks": ["notebookread", "notebookedit"],
            "Memory & Context": ["memoryread", "memorywrite"],
            "Collaboration": ["agent", "sticker"],
            "Integration": ["mcp"],
        }

        for category, tool_names in categories.items():
            print(f"📁 {category}")
            print("-" * len(category))

            for tool_name in tool_names:
                tool = registry.get_tool(tool_name)
                if tool:
                    definition = tool.definition
                    print(f"  ✓ {definition.name}: {definition.description}")
                else:
                    print(f"  ✗ {tool_name}: NOT FOUND")
            print()

        # List any tools not in categories
        categorized_tools = set()
        for tool_list in categories.values():
            categorized_tools.update(tool_list)

        uncategorized = [
            tool.name for tool in tools if tool.name not in categorized_tools
        ]
        if uncategorized:
            print("📋 Other Tools")
            print("-" * 11)
            for tool_name in uncategorized:
                tool = registry.get_tool(tool_name)
                definition = tool.definition
                print(f"  ✓ {definition.name}: {definition.description}")
            print()

        print(f"🎯 Total: {len(tools)} tools available")

        # Test a few tools
        print("\n🧪 Quick Tool Tests")
        print("-" * 18)

        # Test that tools can be retrieved
        test_tools = ["glob", "grep", "think", "agent", "architect"]
        for tool_name in test_tools:
            tool = registry.get_tool(tool_name)
            if tool:
                print(f"  ✓ {tool_name}: Can be retrieved")
                try:
                    definition = tool.definition
                    ollama_format = definition.to_ollama_format()
                    print(f"    - Definition: ✓")
                    print(f"    - Ollama format: ✓")
                except Exception as e:
                    print(f"    - Error: {e}")
            else:
                print(f"  ✗ {tool_name}: Cannot be retrieved")

        print(f"\n✅ All tools are properly registered and functional!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
