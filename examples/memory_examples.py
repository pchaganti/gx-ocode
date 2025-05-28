#!/usr/bin/env python3
"""
OCode Memory System Examples

This file demonstrates various ways to use the OCode memory system,
both through direct tool usage and intelligent LLM-driven interactions.

Make sure you have the function calling model installed:
    ollama pull MFDoom/deepseek-coder-v2-tool-calling:latest
"""

import asyncio
import json
from pathlib import Path

from ocode_python.core.engine import OCodeEngine
from ocode_python.tools.memory_tools import MemoryReadTool, MemoryWriteTool


async def example_direct_memory_usage():
    """Example: Direct memory tool usage without LLM."""
    print("=" * 60)
    print("Direct Memory Tool Usage")
    print("=" * 60)

    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # Example 1: Store user profile
    print("📝 Storing user profile...")
    user_profile = {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "role": "Developer",
        "team": "Backend",
        "preferences": {
            "language": "Python",
            "framework": "FastAPI",
            "editor": "VSCode",
        },
    }

    result = await write_tool.execute(
        memory_type="persistent",
        operation="set",
        key="user_profile",
        value=user_profile,
        category="profile",
    )
    print(f"✅ {result.output}")

    # Example 2: Store project settings
    print("\n🔧 Storing project settings...")
    project_settings = {
        "project_name": "awesome-api",
        "version": "1.2.0",
        "database": "postgresql",
        "cache": "redis",
        "deployment": "docker",
    }

    result = await write_tool.execute(
        memory_type="persistent",
        operation="set",
        key="project_settings",
        value=project_settings,
        category="config",
    )
    print(f"✅ {result.output}")

    # Example 3: Maintain task list
    print("\n📋 Adding tasks...")
    tasks = [
        {"id": 1, "title": "Implement user authentication", "status": "in-progress"},
        {"id": 2, "title": "Add rate limiting", "status": "pending"},
        {"id": 3, "title": "Write API documentation", "status": "pending"},
    ]

    for task in tasks:
        result = await write_tool.execute(
            memory_type="session",
            operation="append",
            key="current_tasks",
            value=task,
            category="tasks",
        )
        print(f"  ✅ Added task: {task['title']}")

    # Example 4: Read everything back
    print("\n📖 Reading stored data...")

    # Read user profile
    result = await read_tool.execute(
        memory_type="persistent", key="user_profile", format="detailed"
    )
    print(f"User Profile:\n{result.output}")

    # Read all persistent data
    result = await read_tool.execute(memory_type="persistent", format="summary")
    print(f"\nAll Persistent Data:\n{result.output}")


async def example_llm_driven_memory():
    """Example: LLM-driven intelligent memory usage."""
    print("\n" + "=" * 60)
    print("LLM-Driven Intelligent Memory Usage")
    print("=" * 60)

    # Initialize engine with function calling model
    engine = OCodeEngine(
        model="MFDoom/deepseek-coder-v2-tool-calling:latest",
        verbose=True,  # Show the decision making process
    )

    print("🤖 Example 1: Natural language memory storage")
    print("-" * 40)

    # Natural language commands
    queries = [
        "Remember my favorite programming language is Rust",
        "Save that my current project is a web scraper",
        "Store my API key as abc123def456 in credentials",
        "Remember I'm working on machine learning with PyTorch",
    ]

    for query in queries:
        print(f"\n💬 User: {query}")
        print("🤖 Assistant:", end=" ")

        response_parts = []
        async for chunk in engine.process(query):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)
        print()  # New line after response

    print("\n🤖 Example 2: Natural language memory retrieval")
    print("-" * 40)

    # Retrieval queries
    retrieval_queries = [
        "What's my favorite programming language?",
        "What project am I working on?",
        "Show me everything in my memory",
        "What credentials do I have stored?",
    ]

    for query in retrieval_queries:
        print(f"\n💬 User: {query}")
        print("🤖 Assistant:", end=" ")

        async for chunk in engine.process(query):
            print(chunk, end="", flush=True)
        print()  # New line after response


async def example_advanced_memory_patterns():
    """Example: Advanced memory usage patterns."""
    print("\n" + "=" * 60)
    print("Advanced Memory Patterns")
    print("=" * 60)

    write_tool = MemoryWriteTool()
    read_tool = MemoryReadTool()

    # Pattern 1: Hierarchical data organization
    print("📁 Pattern 1: Hierarchical Organization")
    print("-" * 40)

    # Store configuration by environment
    environments = ["development", "staging", "production"]
    for env in environments:
        config = {
            "database_url": f"{env}-db.example.com",
            "api_url": f"api-{env}.example.com",
            "debug": env == "development",
            "log_level": "DEBUG" if env == "development" else "INFO",
        }

        result = await write_tool.execute(
            memory_type="persistent",
            operation="set",
            key=f"config_{env}",
            value=config,
            category="environments",
        )
        print(f"  ✅ Stored {env} config")

    # Pattern 2: Versioned data
    print("\n📈 Pattern 2: Versioned Data")
    print("-" * 40)

    # Store multiple versions of a schema
    schema_versions = [
        {"version": "1.0", "fields": ["id", "name", "email"]},
        {"version": "1.1", "fields": ["id", "name", "email", "created_at"]},
        {
            "version": "2.0",
            "fields": ["id", "name", "email", "created_at", "updated_at", "status"],
        },
    ]

    for schema in schema_versions:
        result = await write_tool.execute(
            memory_type="persistent",
            operation="append",
            key="schema_history",
            value=schema,
            category="schemas",
        )
        print(f"  ✅ Added schema version {schema['version']}")

    # Pattern 3: Temporary session data with cleanup
    print("\n🧹 Pattern 3: Session Data Management")
    print("-" * 40)

    # Store temporary data for current session
    temp_data = [
        {"type": "debug_info", "data": "Current debugging session X"},
        {"type": "temp_files", "data": ["/tmp/debug.log", "/tmp/output.json"]},
        {"type": "active_connections", "data": ["db_conn_1", "redis_conn_1"]},
    ]

    for item in temp_data:
        result = await write_tool.execute(
            memory_type="session",
            operation="set",
            key=item["type"],
            value=item["data"],
            category="temporary",
        )
        print(f"  ✅ Stored temporary {item['type']}")

    # Pattern 4: Smart querying
    print("\n🔍 Pattern 4: Smart Querying")
    print("-" * 40)

    # Query by category
    result = await read_tool.execute(memory_type="persistent", category="environments")
    print(f"Environment configs:\n{result.output}")

    # Query specific version data
    result = await read_tool.execute(
        memory_type="persistent", key="schema_history", format="detailed"
    )
    print(f"\nSchema history:\n{result.output}")


async def example_practical_workflows():
    """Example: Practical development workflows."""
    print("\n" + "=" * 60)
    print("Practical Development Workflows")
    print("=" * 60)

    engine = OCodeEngine(
        model="MFDoom/deepseek-coder-v2-tool-calling:latest",
        verbose=False,  # Less verbose for cleaner output
    )

    print("🚀 Workflow 1: Project Setup")
    print("-" * 30)

    # Project initialization workflow
    setup_commands = [
        "Remember this is a FastAPI project with PostgreSQL database",
        "Store my database URL as postgresql://user:pass@localhost/mydb",
        "Save that I'm using Poetry for dependency management",
        "Remember the main API port is 8000",
    ]

    for cmd in setup_commands:
        print(f"💬 {cmd}")
        async for chunk in engine.process(cmd):
            pass  # Just execute, don't print for cleaner output
        print("  ✅ Stored")

    print("\n📊 Workflow 2: Development Session")
    print("-" * 30)

    # Development session tracking
    dev_commands = [
        "Remember I'm currently working on user authentication endpoints",
        "Store that I found a bug in the login validation logic",
        "Save my current Git branch as feature/auth-improvements",
        "Remember to review the password hashing implementation",
    ]

    for cmd in dev_commands:
        print(f"💬 {cmd}")
        async for chunk in engine.process(cmd):
            pass
        print("  ✅ Noted")

    print("\n📝 Workflow 3: Session Summary")
    print("-" * 30)

    # Get session summary
    print("💬 What did I work on today?")
    async for chunk in engine.process(
        "What did I work on today? Show me my session notes."
    ):
        print(chunk, end="", flush=True)
    print()


def cli_examples():
    """CLI usage examples."""
    print("\n" + "=" * 60)
    print("CLI Usage Examples")
    print("=" * 60)

    examples = [
        {
            "description": "Store personal information",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -p "Remember my name is John Smith"',
        },
        {
            "description": "Store project details",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -p "Save that this is a React project with TypeScript"',
        },
        {
            "description": "Store API credentials (be careful!)",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -p "Store my GitHub token as ghp_example123"',
        },
        {
            "description": "Retrieve stored information",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -p "What\'s my name?"',
        },
        {
            "description": "Show all stored data",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -p "Show me everything in my memory"',
        },
        {
            "description": "Verbose mode (see decision process)",
            "command": 'ocode -m MFDoom/deepseek-coder-v2-tool-calling:latest -v -p "Remember my favorite color"',
        },
    ]

    for example in examples:
        print(f"📝 {example['description']}:")
        print(f"   {example['command']}")
        print()


async def main():
    """Run all examples."""
    print("🎯 OCode Memory System Examples")
    print("🤖 Make sure you have the function calling model installed:")
    print("   ollama pull MFDoom/deepseek-coder-v2-tool-calling:latest")
    print()

    try:
        # Run examples
        await example_direct_memory_usage()
        await example_llm_driven_memory()
        await example_advanced_memory_patterns()
        await example_practical_workflows()

        # Show CLI examples
        cli_examples()

        print("✅ All examples completed successfully!")
        print("\n💡 Try these examples yourself:")
        print("   python examples/memory_examples.py")
        print("   python -m pytest tests/test_memory_system.py -v")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        print("💡 Make sure you have:")
        print("   1. Ollama installed and running")
        print(
            "   2. The function calling model: MFDoom/deepseek-coder-v2-tool-calling:latest"
        )
        print("   3. OCode properly installed")


if __name__ == "__main__":
    """Run examples when executed directly."""
    asyncio.run(main())
