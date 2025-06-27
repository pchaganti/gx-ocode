USE TOOLS (should_use_tools: true) when the query:
- Requests interaction with files, directories, or filesystem
- Needs to execute system commands or check system state
- Requires downloading data from external sources
- Asks to store or retrieve information from memory
- Involves analyzing or modifying code in the current project
- Needs to perform git operations
- Requests text processing on specific files

DO NOT USE TOOLS (should_use_tools: false) when the query:
- Asks for general programming concepts or language explanations
- Requests theoretical knowledge or definitions
- Seeks best practices, patterns, or general advice
- Asks "what is", "how does", "why", "when to use" about general topics
- Requests explanations of algorithms, data structures, or concepts
- Asks for comparisons between technologies or approaches
- Seeks tutorials or learning guidance