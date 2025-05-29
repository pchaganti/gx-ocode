# OCode Tool Reference

OCode provides a comprehensive set of tools for various development tasks. This guide covers all available tools, their parameters, and usage examples.

## Tool Categories

### 1. File Operations
- **file_read**: Read file contents with line numbers
- **file_write**: Create or overwrite files
- **file_edit**: Make precise edits to existing files
- **file_ops**: Copy, move, or remove files
- **find**: Search for files by name pattern
- **glob**: Match files using glob patterns
- **ls**: List directory contents

### 2. Text Processing
- **grep**: Search file contents with regex
- **head**: Display first lines of files
- **tail**: Display last lines of files
- **wc**: Count lines, words, and characters
- **diff**: Compare files or strings
- **sort**: Sort lines in files
- **uniq**: Filter unique lines

### 3. Data Processing
- **json_yaml**: Parse and manipulate JSON/YAML data
- **jq**: JSONPath queries on data

### 4. System Operations
- **bash**: Execute shell commands
- **env**: Manage environment variables
- **which**: Find command locations
- **ping**: Network connectivity testing
- **process**: Monitor system processes

### 5. Development Tools
- **git_status**: Check repository status
- **git_diff**: View uncommitted changes
- **git_commit**: Create commits
- **test_runner**: Execute test suites
- **notebook_read**: Read Jupyter notebooks
- **notebook_edit**: Modify Jupyter notebooks

### 6. Analysis Tools
- **architect**: Analyze project architecture
- **think**: Extended reasoning for complex tasks
- **sticker**: Apply quick fixes and transformations

### 7. Memory and Session
- **memory_read**: Retrieve stored information
- **memory_write**: Store information persistently

### 8. Integration Tools
- **mcp**: Model Context Protocol operations
- **curl**: HTTP requests and API calls
- **agent**: Delegate tasks to specialized agents

## Common Parameters

Most tools share common parameter patterns:

- **Path parameters**: Use absolute paths or paths relative to project root
- **Pattern parameters**: Support regex or glob patterns
- **Output formats**: Many tools support different output formats (text, json, etc.)
- **Confirmation**: Dangerous operations require explicit confirmation

## Error Handling

All tools return a standardized result structure:
```json
{
  "success": true/false,
  "output": "Result content",
  "error": "Error message if failed"
}
```

## Security Considerations

Tools respect the security configuration in `.ocode/settings.json`:
- File operations are restricted to allowed paths
- Shell commands are validated against security patterns
- Dangerous operations require confirmation

## Best Practices

1. **Use specific tools**: Prefer specialized tools over general bash commands
2. **Check permissions**: Ensure you have necessary permissions before operations
3. **Validate inputs**: Always validate paths and patterns before use
4. **Handle errors**: Check tool results and handle failures gracefully
5. **Use appropriate tools**: Choose the right tool for each task

## Getting Help

To see available tools and their descriptions:
```
ocode -p "What tools can you use?"
```

For detailed help on a specific tool:
```
ocode -p "How do I use the grep tool?"
```

## Next Steps

- [File Operations Guide](file-operations.md)
- [Text Processing Guide](text-processing.md)
- [Data Processing Guide](data-processing.md)
- [System Operations Guide](system-operations.md)
- [Development Tools Guide](development-tools.md)
