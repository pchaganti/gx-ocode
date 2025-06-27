#!/usr/bin/env python3
"""
Test script for the new theming system.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ocode_python.ui.theme import theme_manager, get_themed_console
from ocode_python.ui.components import (
    ThemedPanel, StatusIndicator, ThemeSelector, 
    ConversationRenderer, ThemedSyntax
)

def test_themes():
    """Test basic theme functionality."""
    print("=== Testing Theme System ===\n")
    
    console = get_themed_console()
    
    # Test current theme
    active = theme_manager.get_active_theme()
    console.print(f"Active theme: {active.name} ({active.type.value})")
    
    # Test themed panels
    console.print(ThemedPanel.info("This is an info panel", "ℹ️ Information"))
    console.print(ThemedPanel.success("This is a success panel", "✅ Success"))
    console.print(ThemedPanel.warning("This is a warning panel", "⚠️ Warning"))
    console.print(ThemedPanel.error("This is an error panel", "❌ Error"))
    
    # Test status indicators
    console.print(StatusIndicator.loading("Processing..."))
    console.print(StatusIndicator.success("Task completed"))
    console.print(StatusIndicator.warning("Be careful"))
    console.print(StatusIndicator.error("Something went wrong"))
    console.print(StatusIndicator.info("Additional information"))
    
    # Test syntax highlighting
    code_sample = '''def greet(name: str) -> str:
    """Return a greeting message."""
    # This is a comment
    return f"Hello, {name}!"

result = greet("World")
print(result)'''
    
    syntax = ThemedSyntax.create(code_sample, "python", line_numbers=True)
    console.print(ThemedPanel.create(syntax, title="🐍 Python Code Sample"))
    
    # Test conversation renderer
    renderer = ConversationRenderer(console)
    renderer.render_user_message("How do I implement a binary search?")
    renderer.render_ai_message("I'll help you implement binary search. Here's a Python implementation:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```")
    renderer.render_tool_call("search_tool", {"query": "binary search algorithms", "max_results": 5})

def test_theme_switching():
    """Test switching between themes."""
    print("\n=== Testing Theme Switching ===\n")
    
    console = get_themed_console()
    
    # List available themes
    themes = theme_manager.list_themes()
    console.print(f"Available themes: {len(themes)}")
    
    for theme in themes[:3]:  # Test first 3 themes
        console.print(f"\n--- Testing theme: {theme.name} ---")
        theme_manager.set_active_theme(theme.name)
        
        # Get new console with updated theme
        test_console = get_themed_console()
        test_console.print(ThemedPanel.info(
            f"This is the {theme.name} theme\nType: {theme.type.value}\nDescription: {theme.description}",
            title=f"🎨 {theme.name.title()} Theme"
        ))

if __name__ == "__main__":
    try:
        test_themes()
        test_theme_switching()
        print("\n✅ All theming tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()