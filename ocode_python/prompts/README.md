# Modular Prompt System

This directory contains the modular prompt system for OCode, designed to be highly extensible and maintainable.

## Architecture

### 1. Static Components (`system/` and `analysis/`)
- **Markdown files** containing prompt components
- Easy to edit and version control
- Loaded and cached at runtime

### 2. Dynamic Repository (`prompt_repository.py`)
- **SQLite database** for storing thousands of examples
- Performance tracking and optimization
- Version control for prompt evolution
- A/B testing support

### 3. Prompt Composer (`prompt_composer.py`)
- Assembles prompts from modular components
- Supports dynamic example selection
- Adaptive prompt building based on query type
- Caching for performance

## Directory Structure

```
prompts/
├── system/                 # Core system prompt components
│   ├── role.md            # AI role definition
│   ├── core_capabilities.md
│   ├── task_analysis_framework.md
│   ├── workflow_patterns.md
│   ├── response_strategies.md
│   ├── error_handling.md
│   ├── output_guidelines.md
│   └── thinking_framework.md
├── analysis/              # Analysis prompt components
│   ├── decision_criteria.md
│   ├── tool_usage_criteria.md
│   ├── tool_categories.md
│   ├── tool_examples.md
│   └── thinking_questions.md
├── data/                  # Repository data (when enabled)
│   └── examples.db       # SQLite database
├── prompt_composer.py     # Main composition logic
├── prompt_repository.py   # Dynamic storage system
└── README.md

```

## Usage

### Basic Usage (Static Components)

```python
from ocode_python.prompts.prompt_composer import PromptComposer

# Initialize composer
composer = PromptComposer()

# Build full system prompt
system_prompt = composer.build_system_prompt(
    tool_descriptions="List of available tools..."
)

# Build minimal prompt for simple queries
minimal_prompt = composer.build_minimal_prompt(
    tool_descriptions="List of available tools..."
)

# Build analysis prompt
analysis_prompt = composer.build_analysis_prompt(
    query="User query here",
    tool_names=["file_read", "file_write", ...]
)
```

### Advanced Usage (With Repository)

```python
# Enable repository for dynamic examples
composer = PromptComposer(use_repository=True)

# Add examples to repository
from ocode_python.prompts.prompt_repository import PromptRepository, PromptExample

repo = composer.repository
example = PromptExample(
    id="",
    query="show all Python files",
    response={"should_use_tools": True, "suggested_tools": ["find"]},
    category="tool_use",
    tags=["file_ops", "python"]
)
repo.example_store.add_example(example)

# Build prompt with dynamic examples
analysis_prompt = composer.build_analysis_prompt_dynamic(
    query="find JavaScript files",
    tool_names=tool_names,
    use_dynamic_examples=True
)
```

## Extending the System

### Adding New Components

1. Create a new markdown file in the appropriate directory
2. Reference it in the prompt composer:

```python
# In prompt_composer.py
new_content = self.load_component("new_component", "system")
sections.append(f"<new_section>\n{new_content}\n</new_section>")
```

### Adding Examples at Scale

```python
# Import from JSON
with open("examples.json") as f:
    examples_data = json.load(f)
    
for data in examples_data:
    example = PromptExample(**data)
    repo.example_store.add_example(example)

# Or programmatically generate
for i in range(1000):
    example = generate_example(i)  # Your generation logic
    repo.example_store.add_example(example)
```

### Custom Selection Strategies

```python
class CustomExampleStore(ExampleStore):
    def search_similar(self, query: str, limit: int = 5) -> List[PromptExample]:
        # Implement custom similarity logic
        # e.g., using embeddings, semantic search, etc.
        pass
```

## Performance Considerations

1. **Caching**: Components are cached in memory after first load
2. **Database Indexing**: Repository uses indexes for fast retrieval
3. **Lazy Loading**: Examples are loaded only when needed
4. **Batch Operations**: Repository supports batch inserts

## Future Enhancements

1. **Embedding-based Similarity**: Use vector embeddings for better example matching
2. **Multi-language Support**: Store prompts in multiple languages
3. **Prompt Templates**: Support for complex prompt templates with variables
4. **Analytics Dashboard**: Track prompt performance and optimize automatically
5. **Version Control Integration**: Git-based tracking of prompt evolution