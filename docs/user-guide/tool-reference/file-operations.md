# File Operations Tools

This guide covers all file operation tools available in OCode.

## file_read

Read the contents of a file with line numbers.

### Parameters
- `path` (string, required): Absolute path to the file to read
- `start_line` (integer, optional): Line number to start reading from (default: 1)
- `end_line` (integer, optional): Line number to stop reading at (default: end of file)

### Returns
- File contents with line numbers in the format: `line_number | content`

### Examples
```bash
# Read entire file
ocode -p "Read the contents of /path/to/file.py"

# Read specific lines
ocode -p "Read lines 10-20 of main.py"

# Read from line 50 to end
ocode -p "Show me the code starting from line 50 in utils.py"
```

### Security
- Only files within allowed paths can be read
- Binary files are detected and handled appropriately
- Large files may be truncated for performance

## file_write

Create a new file or overwrite an existing file.

### Parameters
- `path` (string, required): Absolute path where to write the file
- `content` (string, required): Content to write to the file

### Returns
- Success confirmation with file path
- Error message if write fails

### Examples
```bash
# Create a new file
ocode -p "Create a file called test.py with a hello world function"

# Overwrite existing file
ocode -p "Replace the contents of config.json with the updated configuration"

# Create file in subdirectory
ocode -p "Create src/components/Button.tsx with a React button component"
```

### Security
- Requires write permissions in settings
- Cannot write outside allowed paths
- Overwrites require confirmation in interactive mode

## file_edit

Make precise edits to existing files by replacing specific text.

### Parameters
- `path` (string, required): Path to the file to edit
- `old_text` (string, required): Exact text to find and replace
- `new_text` (string, required): Text to replace with
- `occurrence` (integer, optional): Which occurrence to replace (default: all)

### Returns
- Success with number of replacements made
- Error if old_text not found or file doesn't exist

### Examples
```bash
# Replace a function
ocode -p "In main.py, replace the calculate function with an optimized version"

# Fix a typo
ocode -p "Fix the typo 'recieve' to 'receive' in all Python files"

# Update import statement
ocode -p "Change 'from old_module import func' to 'from new_module import func'"
```

### Best Practices
- Use exact text matches including whitespace
- For complex edits, use multiple sequential edits
- Verify changes with file_read after editing

## file_ops

Perform file operations: copy, move, or remove files.

### Parameters
- `operation` (string, required): One of "copy", "move", or "remove"
- `source` (string, required): Source file path
- `destination` (string, optional): Destination path (required for copy/move)

### Returns
- Success confirmation with operation details
- Error if operation fails

### Examples
```bash
# Copy a file
ocode -p "Copy config.example.json to config.json"

# Move/rename a file
ocode -p "Rename old_module.py to new_module.py"

# Remove a file
ocode -p "Delete the temporary test_output.txt file"

# Copy to different directory
ocode -p "Copy src/template.py to tests/test_template.py"
```

### Security
- Remove operations require confirmation
- Cannot operate on system files
- Preserves file permissions when copying

## find

Search for files by name pattern in a directory tree.

### Parameters
- `pattern` (string, required): Name pattern to search for (supports wildcards)
- `path` (string, optional): Starting directory (default: current directory)
- `type` (string, optional): Filter by type - "f" for files, "d" for directories

### Returns
- List of matching file paths
- Empty list if no matches found

### Examples
```bash
# Find all Python files
ocode -p "Find all *.py files in the project"

# Find specific filename
ocode -p "Find all files named config.json"

# Find in specific directory
ocode -p "Find all *.test.js files in the src directory"

# Find directories
ocode -p "Find all directories named __pycache__"
```

### Performance Tips
- Use specific starting paths to limit search scope
- Combine with grep for content-based filtering
- Results are sorted by modification time

## glob

Match files using glob patterns (faster than find for simple patterns).

### Parameters
- `pattern` (string, required): Glob pattern (e.g., "**/*.py", "src/**/test_*.js")
- `root` (string, optional): Root directory to search from

### Returns
- List of matching file paths
- Sorted by modification time (newest first)

### Examples
```bash
# All Python files recursively
ocode -p "Get all **/*.py files"

# Test files in src
ocode -p "Find src/**/test_*.js files"

# All JSON config files
ocode -p "List all **/*config*.json files"

# Direct children only
ocode -p "Show me all *.md files in the docs folder (not recursive)"
```

### Glob Pattern Syntax
- `*`: Match any characters except path separator
- `**`: Match any characters including path separators
- `?`: Match single character
- `[abc]`: Match any character in brackets
- `[!abc]`: Match any character not in brackets

## ls

List directory contents with detailed information.

### Parameters
- `path` (string, optional): Directory path to list (default: current directory)
- `all` (boolean, optional): Include hidden files (default: false)
- `long` (boolean, optional): Show detailed information (default: false)

### Returns
- List of files and directories
- With sizes, permissions, and modification times if long format

### Examples
```bash
# List current directory
ocode -p "List all files in the current directory"

# List with details
ocode -p "Show detailed listing of the src directory"

# Include hidden files
ocode -p "List all files including hidden ones in the home directory"

# List specific directory
ocode -p "What files are in /tmp?"
```

### Output Format
- Regular format: Simple file/directory names
- Long format: Permissions, size, modified date, name
- Directories shown with trailing slash
- Symbolic links shown with arrow to target

## Best Practices for File Operations

### 1. Path Handling
- Always use absolute paths when possible
- Verify paths exist before operations
- Handle both files and directories appropriately

### 2. Error Recovery
- Check if files exist before reading/editing
- Have fallback plans for failed operations
- Log operations for debugging

### 3. Performance
- Use glob for simple patterns instead of find
- Read only necessary lines from large files
- Batch operations when possible

### 4. Safety
- Always backup before bulk operations
- Test patterns with ls/find before applying changes
- Use confirmation prompts for destructive operations

## Common Workflows

### Refactoring
```bash
# 1. Find all files to change
ocode -p "Find all files importing old_module"

# 2. Update imports
ocode -p "In each file, replace 'from old_module' with 'from new_module'"

# 3. Rename the module
ocode -p "Rename old_module.py to new_module.py"
```

### Backup and Restore
```bash
# Create backup
ocode -p "Copy important.conf to important.conf.backup"

# Make changes
ocode -p "Edit important.conf to update the database connection"

# Restore if needed
ocode -p "Copy important.conf.backup back to important.conf"
```

### Bulk Operations
```bash
# Find all test files
ocode -p "Find all test_*.py files"

# Add common import to all
ocode -p "Add 'import pytest' to the top of each test file"

# Verify changes
ocode -p "Show the first 5 lines of each test file"
```

## Troubleshooting

### Permission Denied
- Check `.ocode/settings.json` for allowed paths
- Ensure file permissions allow the operation
- Run with appropriate user privileges

### File Not Found
- Verify the path is correct
- Check for typos in filenames
- Ensure file hasn't been moved/deleted

### Pattern Not Matching
- Test patterns with ls or find first
- Escape special characters in patterns
- Use quotes around complex patterns

## Related Tools
- [Text Processing](text-processing.md) - Process file contents
- [Development Tools](development-tools.md) - Version control operations
- [System Operations](system-operations.md) - System-level file operations
