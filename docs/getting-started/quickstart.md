# OCode Quickstart Guide

Get up and running with OCode in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Ollama installed and running
- 8GB RAM recommended
- Unix-like system (Linux, macOS, WSL)

## Installation

### 1. Install OCode

```bash
# Using pip (recommended)
pip install ocode-ai

# Or from source
git clone https://github.com/haasonsaas/ocode.git
cd ocode
pip install -e .
```

### 2. Verify Installation

```bash
# Check installation
ocode --help

# Check version
ocode --version
```

### 3. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull recommended model
ollama pull MFDoom/deepseek-coder-v2-tool-calling:latest
```

## Your First OCode Session

### 1. Initialize a Project

```bash
# Navigate to your project
cd my-project

# Initialize OCode
ocode init

# This creates:
# .ocode/
#   ├── settings.json    # Configuration
#   ├── memory/          # Persistent storage
#   └── commands/        # Custom commands
```

### 2. Basic Usage

```bash
# Ask about your project
ocode -p "What is this project about?"

# List files
ocode -p "Show me all Python files in this project"

# Read a specific file
ocode -p "Read the main.py file and explain what it does"

# Make changes
ocode -p "Add proper error handling to the process_data function"
```

### 3. Interactive Mode

```bash
# Start interactive session
ocode

# In the session:
ocode> What files are in the src directory?
ocode> Read config.json and explain the settings
ocode> Create a new test file for the user module
ocode> /exit
```

## Essential Commands

### File Operations

```bash
# Read files
ocode -p "Show me the contents of README.md"

# Create files
ocode -p "Create a new Python script called data_processor.py with basic structure"

# Edit files
ocode -p "Fix the import statements in main.py"

# Find files
ocode -p "Find all test files in the project"
```

### Code Analysis

```bash
# Understand code
ocode -p "Explain how the authentication system works"

# Find issues
ocode -p "Check for potential bugs in the payment module"

# Suggest improvements
ocode -p "How can I optimize the database queries?"
```

### Development Tasks

```bash
# Write tests
ocode -p "Create unit tests for the Calculator class"

# Add documentation
ocode -p "Add docstrings to all functions in utils.py"

# Refactor code
ocode -p "Refactor the process_order function to be more modular"
```

## Working with Tools

OCode provides specialized tools for different tasks:

### File Tools
```bash
# Search content
ocode -p "Find all files containing 'TODO'"

# Compare files
ocode -p "Show the differences between config.dev.json and config.prod.json"

# Bulk operations
ocode -p "Add copyright header to all Python files"
```

### System Tools
```bash
# Run commands (if enabled)
ocode -p "Run the test suite and show me the results"

# Check environment
ocode -p "What environment variables are set?"

# Monitor processes
ocode -p "Show me running Python processes"
```

### Development Tools
```bash
# Git operations
ocode -p "What changes have I made since the last commit?"

# Code analysis
ocode -p "Analyze the architecture of this project"

# Dependency check
ocode -p "List all Python dependencies and their versions"
```

## Configuration Basics

### Quick Configuration

Edit `.ocode/settings.json`:

```json
{
  "model": "llama3:8b",
  "permissions": {
    "allow_file_read": true,
    "allow_file_write": true,
    "allow_shell_exec": false,
    "allowed_paths": ["."]
  }
}
```

### Common Settings

```bash
# Change model
export OCODE_MODEL="codellama:13b"

# Enable verbose mode
export OCODE_VERBOSE="true"

# Set custom Ollama host
export OLLAMA_HOST="http://gpu-server:11434"
```

## Best Practices

### 1. Be Specific
```bash
# ❌ Too vague
ocode -p "Fix the bug"

# ✅ Specific
ocode -p "Fix the KeyError in user_auth.py line 45 when email is None"
```

### 2. Provide Context
```bash
# ❌ Missing context
ocode -p "Write a function"

# ✅ With context
ocode -p "Write a function to validate email addresses using regex in validators.py"
```

### 3. Verify Changes
```bash
# Make changes
ocode -p "Update the database connection to use connection pooling"

# Verify
ocode -p "Show me the changes you made to database.py"
```

### 4. Use Appropriate Tools
```bash
# ❌ Using bash for everything
ocode -p "Use bash to read all files"

# ✅ Using specific tools
ocode -p "Find all Python files and check for syntax errors"
```

## Common Workflows

### Code Review
```bash
# 1. See what changed
ocode -p "What files have been modified recently?"

# 2. Review changes
ocode -p "Review the changes in auth.py and suggest improvements"

# 3. Apply suggestions
ocode -p "Apply the security improvements to auth.py"
```

### Bug Fixing
```bash
# 1. Understand the error
ocode -p "Explain this error: TypeError: unsupported operand type(s)"

# 2. Find the source
ocode -p "Find where calculate_total is called with wrong types"

# 3. Fix the issue
ocode -p "Fix the type error in calculate_total function"
```

### Adding Features
```bash
# 1. Plan the feature
ocode -p "I need to add email notifications. What's the best approach?"

# 2. Implement
ocode -p "Create an email notification service in services/email.py"

# 3. Test
ocode -p "Write tests for the email notification service"
```

## Troubleshooting

### OCode Command Not Found
```bash
# Check installation
pip show ocode-ai

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Use different port
export OLLAMA_HOST="http://localhost:8080"
```

### Permission Denied
```bash
# Check configuration
cat .ocode/settings.json

# Update allowed paths
ocode config --set permissions.allowed_paths="[\".\"]"
```

### Model Not Found
```bash
# List available models
ollama list

# Pull model
ollama pull llama3:8b

# Use available model
ocode --model llama3:8b -p "Hello"
```

## Next Steps

1. **Explore Tools**: Learn about all [available tools](../user-guide/tool-reference/overview.md)
2. **Configure**: Customize your [configuration](../user-guide/configuration.md)
3. **Advanced Usage**: Check out [workflows](../user-guide/workflows.md)
4. **Integrate**: Set up [IDE integration](../advanced/integrations.md)

## Getting Help

```bash
# Built-in help
ocode -p "What can you do?"
ocode -p "How do I use the grep tool?"

# Documentation
ocode -p "Show me examples of file operations"

# Community
# Visit: https://github.com/haasonsaas/ocode/discussions
```

## Quick Reference Card

| Task | Command |
|------|---------|
| Read file | `ocode -p "Read main.py"` |
| Create file | `ocode -p "Create test.py with a hello world function"` |
| Edit file | `ocode -p "Fix the typo in README.md"` |
| Find files | `ocode -p "Find all .json files"` |
| Search content | `ocode -p "Search for TODO comments"` |
| Git status | `ocode -p "What changes have I made?"` |
| Run tests | `ocode -p "Run the test suite"` |
| Get help | `ocode -p "How do I use OCode?"` |

Start with simple tasks and gradually explore more advanced features. OCode is designed to understand natural language, so just describe what you want to accomplish!
