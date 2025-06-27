
# Product & Engineering Spec: Code Knowledge Graph

**Status:** Proposed | **Authors:** Gemini Architect | **Version:** 1.0

## 1. Overview

This document specifies the design and implementation of the **Code Knowledge Graph (CKG)**. This system will move the agent's understanding of a user's codebase from a flat, text-based view to a deep, semantic, and structured representation. By parsing code into an Abstract Syntax Tree (AST) and constructing a graph of its entities and relationships, the agent will be able to reason about architecture, data flow, and code structure, dramatically improving the quality and accuracy of its analysis and generation.

This is a foundational investment in the agent's "vision," enabling it to see code as a senior developer does.

## 2. Product Requirements

### 2.1. Vision & Goal

Currently, the agent reads files as plain text. It lacks a true understanding of the code's structure. A developer doesn't just see text; they see functions, classes, and the relationships between them. The CKG will give the agent this same level of insight. When a user asks, *"Where is user authentication handled?"*, the agent should be able to answer by traversing a graph of function calls, not just by running a text search for the word "auth".

### 2.2. User Stories

*   **As a developer,** when I ask the agent to refactor a piece of code, I want it to automatically identify all the call sites and update them correctly, so I don't have to manually hunt them down.
*   **As a developer,** when I ask about the impact of changing a function, I want the agent to provide a clear summary of the dependent classes and methods, so I can understand the full scope of my change.
*   **As a developer,** I want the agent to be able to answer architectural questions like *"What services does this controller depend on?"* with precision.

### 2.3. Requirements & Success Criteria

*   **REQ-CKG-01:** The system MUST be able to parse Python files into an Abstract Syntax Tree (AST).
*   **REQ-CKG-02:** The system MUST extract key entities (nodes) and relationships (edges) from the AST to build a graph representation of the code.
*   **REQ-CKG-03:** The graph MUST be stored persistently and updated incrementally as files change.
*   **REQ-CKG-04:** The `Engine` MUST be able to query the CKG to retrieve contextually relevant sub-graphs for a given user query.
*   **Success Criteria:** Given a multi-file Python project, the system can successfully build a graph. When queried about a specific function, it can return a sub-graph correctly identifying its direct callers and the functions it calls.

## 3. Technical Architecture & Design

This feature introduces a new, persistent background service (`GraphBuilderService`) and a query interface for the `Engine`.

### 3.1. The Graph Data Model

The graph will consist of nodes representing code entities and edges representing their relationships. This model will be defined in `ocode_python/knowledge/graph_model.py`.

*   **Node Types (Enum):**
    *   `MODULE` (a file)
    *   `CLASS`
    *   `FUNCTION`
    *   `PARAMETER`
    *   `VARIABLE`

*   **Node Properties (Base class):**
    *   `id`: A unique identifier (e.g., `file.py:MyClass.my_func`)
    *   `name`: The name of the entity (e.g., `my_func`)
    *   `node_type`: From the enum above.
    *   `file_path`: The absolute path to the source file.
    *   `start_line`, `end_line`: Location in the source file.

*   **Edge Types (Enum):**
    *   `IMPORTS` (Module -> Class/Function)
    *   `DEFINES` (Module/Class -> Function/Class)
    *   `CALLS` (Function -> Function)
    *   `INHERITS_FROM` (Class -> Class)
    *   `HAS_PARAMETER` (Function -> Parameter)
    *   `RETURNS` (Function -> Class/Variable) - *Note: May require type inference.* 

### 3.2. New Service: `GraphBuilderService`

This is the core of the CKG. It runs as a persistent background process.

*   **Location:** `ocode_python/knowledge/builder.py`
*   **Responsibilities:**
    1.  **File Monitoring:** Watch the project directory for file changes (`.py` files initially).
    2.  **AST Parsing:** When a file is created or modified, read its content and parse it using Python's built-in `ast` module.
    3.  **Graph Population:** Traverse the AST using a custom `ast.NodeVisitor`. For each relevant AST node (e.g., `ast.FunctionDef`, `ast.Call`, `ast.Import`), create or update the corresponding nodes and edges in the graph.
    4.  **Persistence:** Periodically save the graph to disk.

### 3.3. Storage Layer

We will implement a tiered storage strategy to balance simplicity with future scalability.

*   **Location:** `ocode_python/knowledge/storage.py`
*   **Phase 1 (Initial Implementation):**
    *   Use the `networkx` library. It provides a rich in-memory graph data structure.
    *   The graph will be serialized to a file (e.g., using `pickle` or `networkx`'s own JSON/GraphML formats) in the `.ocode/` directory.
    *   The `GraphBuilderService` will load this file on startup and save it periodically.
*   **Phase 2 (Future):**
    *   Abstract the storage layer behind a `GraphStorage` interface.
    *   Implement a new backend that uses a dedicated graph database like **Neo4j** or **Memgraph**. This will be necessary for handling very large codebases and performing more complex queries efficiently.

### 3.4. Query Interface & Engine Integration

The `Engine` needs a way to leverage the CKG.

*   **Location:** `ocode_python/knowledge/querier.py`
*   **Class:** `GraphQuerier`
*   **Key Methods:**
    *   `__init__(self, storage: GraphStorage)`: Takes a storage backend.
    *   `async def get_context_for_query(self, query: str, symbols: List[str]) -> str:`: This is the primary interface for the `Engine`.
        1.  It identifies key entities in the user's query (e.g., function names).
        2.  It finds the corresponding nodes in the graph.
        3.  It performs a graph traversal (e.g., a 2-hop neighborhood search) to find all related nodes.
        4.  It serializes this sub-graph into a human-readable text format to be included in the LLM prompt.

*   **Engine Modification:**
    *   The `ContextManager` will be updated. In addition to reading raw file content, it will now also call the `GraphQuerier`.
    *   The context provided to the LLM will be enriched with the structured, semantic information from the graph, e.g.:
        ```
        <file_content path="service.py">...</file_content>
        <code_graph_context>
        Function `process_payment` in `service.py`:
        - CALLS the function `charge_card` in `stripe_client.py`
        - IS CALLED BY the function `POST /payment` in `api.py`
        </code_graph_context>
        ```

## 4. Implementation Plan (For Agent Execution)

*   **Phase 1: Model & Storage**
    1.  Create the `ocode_python/knowledge/` directory.
    2.  Implement the graph data model (nodes, edges) in `graph_model.py`.
    3.  Implement the initial `networkx`-based storage layer in `storage.py`.
    4.  Write unit tests for the model and storage layers.

*   **Phase 2: The Graph Builder Service**
    1.  Implement the `GraphBuilderService` in `builder.py`.
    2.  Focus on the `ast.NodeVisitor` logic to correctly parse Python files and populate the graph.
    3.  Write integration tests that feed it a sample Python file and verify that the resulting graph in the storage layer is correct.

*   **Phase 3: The Query Interface**
    1.  Implement the `GraphQuerier` class in `querier.py`.
    2.  Focus on the traversal and serialization logic.
    3.  Write integration tests that load a pre-built graph and ensure the querier returns the correct sub-graph for various queries.

*   **Phase 4: Engine Integration**
    1.  Modify the `ContextManager` to use the `GraphQuerier`.
    2.  Update the prompt-building logic to include the new `code_graph_context` section.
    3.  Perform E2E testing to confirm that the agent's responses are more accurate and context-aware when answering questions about code structure.

## 5. Future Work

*   **Support for More Languages:** Extend the AST parser to handle JavaScript/TypeScript, Java, etc., using libraries like `tree-sitter`.
*   **Type Inference:** Enhance the graph builder to perform basic type inference to strengthen the graph's relational links.
*   **Visualizer:** Create a simple web-based tool to visualize the generated knowledge graph for a project.
