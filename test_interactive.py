"""Interactive test script for bash tool functionality."""

import asyncio

from ocode_python.tools.bash_tool import BashTool


async def test_interactive_command():
    bash_tool = BashTool()

    # Test 1: Simple interactive command (read input)
    print("\nTest 1: Simple interactive command")
    result = await bash_tool.execute(
        command="read -p 'Enter your name: ' name && echo 'Hello, $name!'",
        interactive=True,
        timeout=30,
    )
    print(f"Output: {result.output}")
    print(f"Success: {result.success}")
    if result.metadata:
        print(f"Return code: {result.metadata.get('return_code')}")
    if result.error:
        print(f"Error: {result.error}")

    # Test 2: Command with timeout
    print("\nTest 2: Command with timeout")
    result = await bash_tool.execute(
        command="sleep 2 && read -p 'This should timeout: ' input",
        interactive=True,
        timeout=1,
    )
    print(f"Output: {result.output}")
    print(f"Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")

    # Test 3: Multi-step interactive command
    print("\nTest 3: Multi-step interactive command")
    result = await bash_tool.execute(
        command="""
        echo "Step 1: Enter a number"
        read number
        echo "Step 2: Enter your name"
        read name
        echo "You entered: $number and $name"
        """,
        interactive=True,
        timeout=30,
    )
    print(f"Output: {result.output}")
    print(f"Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")

    # Test 4: Interactive command with automated input
    print("\nTest 4: Interactive command with automated input")
    result = await bash_tool.execute(
        command="read -p 'Enter your favorite color: ' color && echo 'Color: $color'",
        interactive=True,
        timeout=10,
        input_data="blue\n",
    )
    print(f"Output: {result.output}")
    print(f"Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_interactive_command())
