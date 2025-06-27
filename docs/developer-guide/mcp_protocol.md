# Model Context Protocol (MCP) Developer Guide

## Overview

The Model Context Protocol (MCP) is a powerful framework that enables specialized AI agents to run as standalone servers, providing tools, resources, and prompts to the main OCode engine. This architecture allows for:

- **Modular Design**: Specialized agents can be developed and deployed independently
- **Scalability**: Agents can run on different machines or processes
- **Reusability**: MCP servers can be shared across different AI applications
- **Security**: Controlled access through authentication and resource isolation

## Vision

MCP transforms OCode from a monolithic AI assistant into a distributed system of specialized agents. Imagine having:

- A **Database Specialist** agent that understands SQL optimization
- A **Frontend Expert** agent specialized in React and CSS
- A **Security Auditor** agent focused on vulnerability detection
- A **Performance Optimizer** agent for code optimization

Each specialist runs as an MCP server, and the main OCode engine can discover and delegate tasks to these specialists as needed.

## Architecture

```
┌─────────────────┐     JSON-RPC 2.0    ┌──────────────────┐
│   OCode Engine  │◄───────────────────►│   MCP Server 1   │
│                 │                      │ (DB Specialist)  │
│  Orchestrates   │                      └──────────────────┘
│  requests and   │     JSON-RPC 2.0    ┌──────────────────┐
│  coordinates    │◄───────────────────►│   MCP Server 2   │
│  responses      │                      │ (Frontend Expert)│
└─────────────────┘                      └──────────────────┘
```

## Core Concepts

### 1. Resources
Resources expose data that can be read by the AI. They are identified by URIs and return content without side effects.

```python
# Example: Expose project configuration
@mcp.resource("config://project/settings")
async def get_project_settings():
    return {
        "name": "MyProject",
        "version": "1.0.0",
        "dependencies": ["react", "typescript"]
    }
```

### 2. Tools
Tools provide executable functionality that can perform actions or computations.

```python
# Example: Database query tool
@mcp.tool()
async def execute_query(query: str, database: str) -> Dict[str, Any]:
    """Execute a SQL query on the specified database."""
    # Implementation here
    return {"rows": results, "affected": count}
```

### 3. Prompts
Prompts are reusable templates that help structure interactions with the AI.

```python
# Example: Code review prompt
@mcp.prompt(title="Security Review")
def security_review_prompt(code: str, language: str) -> str:
    return f"""
    Please perform a security review of this {language} code:

    ```{language}
    {code}
    ```

    Focus on:
    - Input validation
    - Authentication/authorization
    - Data exposure
    - Injection vulnerabilities
    """
```

## Creating a Specialist Agent

Here's a step-by-step tutorial for creating a new MCP specialist agent:

### Step 1: Create the Agent File

Create a new file `database_specialist.py`:

```python
#!/usr/bin/env python3
"""Database Specialist MCP Server - Expert in SQL and database operations."""

import asyncio
import logging
from typing import Dict, Any, List
import sqlparse  # SQL parsing library

from ocode_python.mcp.server import MCPServer
from ocode_python.mcp.protocol import MCPResource, MCPTool, MCPPrompt

logger = logging.getLogger(__name__)


class DatabaseSpecialist:
    """Database specialist agent with SQL expertise."""

    def __init__(self):
        self.server = MCPServer(
            name="Database Specialist",
            version="1.0.0",
            description="Expert in SQL optimization, schema design, and database operations"
        )
        self._register_capabilities()

    def _register_capabilities(self):
        """Register all capabilities of this specialist."""
        self._register_resources()
        self._register_tools()
        self._register_prompts()

    def _register_resources(self):
        """Register available resources."""
        # Resource: Database best practices
        self.server.add_resource(MCPResource(
            uri="db://best-practices/indexing",
            name="Indexing Best Practices",
            description="Guidelines for optimal database indexing",
            mime_type="text/markdown"
        ))

        # Resource: Common SQL patterns
        self.server.add_resource(MCPResource(
            uri="db://patterns/queries",
            name="SQL Query Patterns",
            description="Common SQL query patterns and optimizations",
            mime_type="text/markdown"
        ))

    def _register_tools(self):
        """Register available tools."""
        # Tool: SQL formatter
        self.server.add_tool(MCPTool(
            name="format_sql",
            description="Format and beautify SQL queries",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to format"
                    },
                    "dialect": {
                        "type": "string",
                        "enum": ["mysql", "postgresql", "sqlite"],
                        "default": "postgresql"
                    }
                },
                "required": ["query"]
            }
        ))

        # Tool: Query optimizer
        self.server.add_tool(MCPTool(
            name="optimize_query",
            description="Analyze and optimize SQL queries",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to optimize"
                    },
                    "schema": {
                        "type": "object",
                        "description": "Database schema information"
                    }
                },
                "required": ["query"]
            }
        ))

        # Tool: Schema analyzer
        self.server.add_tool(MCPTool(
            name="analyze_schema",
            description="Analyze database schema for improvements",
            input_schema={
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "object",
                        "description": "Database schema to analyze"
                    }
                },
                "required": ["schema"]
            }
        ))

    def _register_prompts(self):
        """Register available prompts."""
        # Prompt: Query optimization
        self.server.add_prompt(MCPPrompt(
            name="optimize_database",
            description="Guide for database optimization",
            arguments=[
                {
                    "name": "current_schema",
                    "description": "Current database schema",
                    "required": True
                },
                {
                    "name": "performance_issues",
                    "description": "Observed performance issues",
                    "required": False
                }
            ]
        ))

    async def format_sql(self, query: str, dialect: str = "postgresql") -> Dict[str, Any]:
        """Format SQL query implementation."""
        try:
            formatted = sqlparse.format(
                query,
                reindent=True,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=False
            )
            return {
                "success": True,
                "formatted_query": formatted,
                "line_count": len(formatted.splitlines())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def optimize_query(self, query: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze and suggest query optimizations."""
        suggestions = []

        # Parse the query
        parsed = sqlparse.parse(query)[0]

        # Check for SELECT *
        if "SELECT *" in query.upper():
            suggestions.append({
                "type": "performance",
                "severity": "medium",
                "suggestion": "Avoid SELECT *, specify only needed columns"
            })

        # Check for missing WHERE clause in UPDATE/DELETE
        if parsed.get_type() in ('UPDATE', 'DELETE') and 'WHERE' not in query.upper():
            suggestions.append({
                "type": "safety",
                "severity": "high",
                "suggestion": "Add WHERE clause to avoid updating/deleting all rows"
            })

        # Check for JOIN without indexes (if schema provided)
        if schema and 'JOIN' in query.upper():
            # Analyze join conditions and check indexes
            suggestions.append({
                "type": "performance",
                "severity": "medium",
                "suggestion": "Ensure JOIN columns are indexed"
            })

        return {
            "original_query": query,
            "suggestions": suggestions,
            "optimized_query": query  # In real implementation, generate optimized version
        }

    async def analyze_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze database schema for improvements."""
        recommendations = []

        # Check for tables without primary keys
        for table_name, table_info in schema.get("tables", {}).items():
            if not table_info.get("primary_key"):
                recommendations.append({
                    "table": table_name,
                    "issue": "Missing primary key",
                    "recommendation": "Add a primary key for data integrity and performance"
                })

        # Check for missing indexes on foreign keys
        # Check for appropriate data types
        # Check for normalization issues

        return {
            "schema_score": 85,  # Overall schema health score
            "recommendations": recommendations
        }

    async def start(self, host: str = "localhost", port: int = 8765):
        """Start the MCP server."""
        # Set up tool handlers
        self.server.set_tool_handler("format_sql", self.format_sql)
        self.server.set_tool_handler("optimize_query", self.optimize_query)
        self.server.set_tool_handler("analyze_schema", self.analyze_schema)

        # Set up resource handlers
        self.server.set_resource_handler("db://best-practices/indexing",
            lambda: "# Indexing Best Practices\n\n1. Index columns used in WHERE...\n")
        self.server.set_resource_handler("db://patterns/queries",
            lambda: "# Common SQL Patterns\n\n## Pagination\n```sql\n...\n")

        # Start server
        await self.server.start(host, port)
        logger.info(f"Database Specialist running on {host}:{port}")


async def main():
    specialist = DatabaseSpecialist()
    await specialist.start()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down Database Specialist")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### Step 2: Configure Authentication

Add token-based authentication to your specialist:

```python
# In the DatabaseSpecialist.__init__ method:
self.server = MCPServer(
    name="Database Specialist",
    version="1.0.0",
    description="Expert in SQL optimization",
    auth_token=os.environ.get("MCP_AUTH_TOKEN", "your-secret-token")
)
```

### Step 3: Register with OCode

Add your specialist to OCode's MCP configuration:

```python
# In ocode_python/config.py or similar:
MCP_SERVERS = {
    "database_specialist": {
        "host": "localhost",
        "port": 8765,
        "token": "your-secret-token",
        "capabilities": ["tools", "resources", "prompts"],
        "description": "Database and SQL expert"
    }
}
```

### Step 4: Start the Specialist

```bash
# Start the specialist server
python database_specialist.py

# Or with environment variable for token
MCP_AUTH_TOKEN=your-secret-token python database_specialist.py
```

### Step 5: Use from OCode

The main engine can now discover and use your specialist:

```python
# In OCode engine:
async def handle_database_query(query: str):
    # Discover database specialist
    specialist = await mcp_manager.get_server("database_specialist")

    # Format the query
    result = await specialist.call_tool("format_sql", {
        "query": query,
        "dialect": "postgresql"
    })

    # Get optimization suggestions
    optimization = await specialist.call_tool("optimize_query", {
        "query": result["formatted_query"]
    })

    return optimization
```

## Security Model

### Authentication

MCP uses token-based authentication to ensure only authorized clients can connect:

1. **Server Side**: Each MCP server is configured with an authentication token
2. **Client Side**: The OCode engine must provide the correct token when connecting
3. **Token Storage**: Use environment variables or secure configuration files
4. **Token Rotation**: Implement periodic token rotation for production systems

### Implementation:

```python
# Server configuration
class SecureMCPServer(MCPServer):
    def __init__(self, name: str, auth_token: str):
        super().__init__(name)
        self.auth_token = auth_token

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Verify token
        provided_token = params.get("auth_token")
        if provided_token != self.auth_token:
            raise ValueError("Authentication failed: Invalid token")

        # Continue with normal initialization
        return await super().handle_initialize(params)
```

### Resource Isolation

- Each MCP server runs in its own process
- Limited access to system resources
- Sandboxed execution environment recommended
- Use Docker containers for additional isolation

## Best Practices

### 1. Single Responsibility
Each MCP server should focus on one domain of expertise.

### 2. Stateless Operations
Tools should be stateless when possible. Use resources for persistent data.

### 3. Error Handling
Always return structured errors that help the AI understand what went wrong:

```python
{
    "success": False,
    "error": {
        "type": "ValidationError",
        "message": "Invalid SQL syntax",
        "details": "Unexpected token at position 42",
        "suggestion": "Check for missing semicolon"
    }
}
```

### 4. Performance
- Cache resource responses when appropriate
- Implement pagination for large results
- Use async operations for I/O-bound tasks

### 5. Documentation
Every tool, resource, and prompt should have clear descriptions:

```python
MCPTool(
    name="analyze_performance",
    description="Analyze query performance and suggest optimizations. "
                "Requires query execution plan and table statistics.",
    input_schema={...}
)
```

## Advanced Topics

### Dynamic Tool Registration

Register tools based on runtime conditions:

```python
async def register_dynamic_tools(self):
    if self.has_postgresql():
        self.server.add_tool(postgresql_specific_tool)
    if self.has_mysql():
        self.server.add_tool(mysql_specific_tool)
```

### Progress Tracking

For long-running operations:

```python
async def analyze_large_schema(self, schema: Dict, ctx: Context):
    tables = schema.get("tables", {})
    total = len(tables)

    for i, (table_name, table_info) in enumerate(tables.items()):
        await ctx.report_progress(i, total, f"Analyzing {table_name}")
        # Perform analysis
        await asyncio.sleep(0.1)  # Simulate work
```

### Streaming Responses

For real-time feedback:

```python
async def stream_analysis(self, query: str) -> AsyncIterator[str]:
    yield "Starting analysis...\n"
    yield "Parsing query structure...\n"
    # ... more analysis steps
    yield "Analysis complete!\n"
```

## Testing Your MCP Server

Create comprehensive tests:

```python
import pytest
from database_specialist import DatabaseSpecialist

@pytest.mark.asyncio
async def test_format_sql():
    specialist = DatabaseSpecialist()
    result = await specialist.format_sql("select * from users where id=1")

    assert result["success"] is True
    assert "SELECT" in result["formatted_query"]
    assert result["line_count"] > 0

@pytest.mark.asyncio
async def test_authentication():
    server = SecureMCPServer("Test", auth_token="test-token")

    # Should fail with wrong token
    with pytest.raises(ValueError):
        await server.handle_initialize({"auth_token": "wrong-token"})

    # Should succeed with correct token
    result = await server.handle_initialize({"auth_token": "test-token"})
    assert "capabilities" in result
```

## Deployment

### Local Development
```bash
# Start with logging
python -m ocode_python.mcp.specialists.database \
    --host localhost \
    --port 8765 \
    --log-level DEBUG
```

### Production
```bash
# Using systemd service
[Unit]
Description=OCode Database Specialist MCP Server
After=network.target

[Service]
Type=simple
User=ocode
Environment="MCP_AUTH_TOKEN=/run/secrets/mcp_token"
ExecStart=/usr/bin/python -m ocode_python.mcp.specialists.database
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8765
CMD ["python", "-m", "ocode_python.mcp.specialists.database"]
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if the server is running
   - Verify host and port configuration
   - Check firewall settings

2. **Authentication Failed**
   - Verify tokens match between client and server
   - Check token environment variables
   - Ensure tokens are properly escaped

3. **Tool Not Found**
   - Verify tool registration
   - Check tool name spelling
   - Ensure capabilities include "tools"

4. **Timeout Errors**
   - Increase timeout settings
   - Check for blocking operations
   - Implement proper async patterns

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Future Enhancements

1. **Service Discovery**: Automatic discovery of available MCP servers
2. **Load Balancing**: Distribute requests across multiple instances
3. **Caching Layer**: Intelligent caching of resource and tool responses
4. **Metrics Collection**: Performance and usage metrics
5. **Plugin System**: Dynamic loading of specialist modules

## Conclusion

The Model Context Protocol transforms OCode into a powerful, distributed AI system. By creating specialized agents as MCP servers, we can:

- Build domain-specific expertise
- Scale horizontally
- Maintain clean separation of concerns
- Enable community contributions

Start building your own specialists today and expand OCode's capabilities!