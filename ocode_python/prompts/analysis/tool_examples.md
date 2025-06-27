Query: "List files in the current directory"
Response: {"should_use_tools": true, "suggested_tools": ["ls"], "reasoning": "Direct file system interaction required", "context_complexity": "simple"}

Query: "Show me the first 5 lines of README.md"
Response: {"should_use_tools": true, "suggested_tools": ["head"], "reasoning": "Reading specific file content", "context_complexity": "simple"}

Query: "Find all Python files in the project"
Response: {"should_use_tools": true, "suggested_tools": ["find"], "reasoning": "Filesystem search operation", "context_complexity": "simple"}

Query: "Remember my email is john@example.com"
Response: {"should_use_tools": true, "suggested_tools": ["memory_write"], "reasoning": "Store personal information", "context_complexity": "simple"}

Query: "Download data from https://api.example.com"
Response: {"should_use_tools": true, "suggested_tools": ["curl"], "reasoning": "External HTTP request needed", "context_complexity": "simple"}

Query: "Analyze the architecture of THIS codebase"
Response: {"should_use_tools": true, "suggested_tools": ["architect", "find"], "reasoning": "Project-specific code analysis", "context_complexity": "full"}

Query: "What is Python and how does it work?"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General programming language explanation", "context_complexity": "simple"}

Query: "Explain object-oriented programming"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General programming concept explanation", "context_complexity": "simple"}

Query: "What are the differences between REST and GraphQL?"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General technology comparison", "context_complexity": "simple"}

Query: "How do I implement a binary search algorithm?"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General algorithm explanation", "context_complexity": "simple"}

Query: "What are Python best practices for error handling?"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General best practices question", "context_complexity": "simple"}

Query: "When should I use async/await in Python?"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General usage guidance question", "context_complexity": "simple"}

Query: "Explain how machine learning works"
Response: {"should_use_tools": false, "suggested_tools": [], "reasoning": "General ML concept explanation", "context_complexity": "simple"}