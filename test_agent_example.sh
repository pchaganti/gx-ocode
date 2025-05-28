#!/bin/bash

# OCode Agent Testing Examples
# Run these one at a time to test the AgentTool

echo "🤖 Testing OCode AgentTool Capabilities"
echo "======================================"
echo ""

echo "1. Creating a coder agent:"
echo "Command: ocode -p 'Create a coder agent to help with implementation tasks'"
echo ""

echo "2. Creating multiple specialized agents:"
echo "Command: ocode -p 'Create three agents: a coder for implementation, a tester for quality assurance, and a reviewer for code analysis'"
echo ""

echo "3. Delegating a complex task:"
echo "Command: ocode -p 'Create a coder agent and delegate the task: implement error handling improvements in the file_tools.py module with proper logging and user-friendly error messages'"
echo ""

echo "4. Multi-agent coordination:"
echo "Command: ocode -p 'Create a documenter agent and assign it to write comprehensive API documentation for all the memory management tools (MemoryReadTool and MemoryWriteTool)'"
echo ""

echo "5. Checking agent status:"
echo "Command: ocode -p 'Show me all my active agents, their current tasks, and completion status'"
echo ""

echo "6. Advanced agent workflow:"
echo "Command: ocode -p 'I want to improve the ThinkTool. Create a reviewer agent to analyze the current implementation, a coder agent to implement improvements, and a tester agent to create comprehensive tests. Coordinate all three agents.'"
echo ""

echo "7. Agent results and cleanup:"
echo "Command: ocode -p 'Get results from all completed agent tasks and terminate any idle agents'"
echo ""

echo "Run these commands one by one to fully test the AgentTool!"
echo "Each command will exercise different aspects of agent creation, delegation, and management."