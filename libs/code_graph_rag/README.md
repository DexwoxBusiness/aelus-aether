# code-graph-rag Library

**Extracted from:** https://github.com/vitali87/code-graph-rag  
**Version:** 0.1.0  
**Status:** ✅ Extracted (AAET-82)

Multi-language AST parsing and graph construction library for aelus-aether.

---

## Overview

This library provides:
- **Multi-language parsing** - Support for 9 languages (Python, JavaScript, TypeScript, Java, Go, Rust, Scala, C++, Lua)
- **AST-based analysis** - Using tree-sitter for accurate parsing
- **Type inference** - Infer types from code structure
- **Call graph analysis** - Track function calls and dependencies
- **Import resolution** - Resolve module imports and dependencies

---

## Supported Languages

| Language | Extensions | Tree-sitter Grammar |
|----------|-----------|---------------------|
| Python | `.py` | tree-sitter-python |
| JavaScript | `.js`, `.jsx` | tree-sitter-javascript |
| TypeScript | `.ts`, `.tsx` | tree-sitter-typescript |
| Java | `.java` | tree-sitter-java |
| Go | `.go` | tree-sitter-go |
| Rust | `.rs` | tree-sitter-rust |
| Scala | `.scala` | tree-sitter-scala |
| C++ | `.cpp`, `.cc`, `.h`, `.hpp` | tree-sitter-cpp |
| Lua | `.lua` | tree-sitter-lua |

---

## Installation

This library is bundled with aelus-aether. No separate installation needed.

**Dependencies:**
```bash
# Core dependencies
pip install tree-sitter

# Language grammars
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
pip install tree-sitter-java tree-sitter-go tree-sitter-rust
pip install tree-sitter-scala tree-sitter-cpp tree-sitter-lua

# Storage backends (AAET-84)
pip install asyncpg  # For PostgreSQL support
```

---

## Quick Start

### 1. Parse a File

```python
from libs.code_graph_rag.parsers.factory import ParserFactory

# Create parser for language
parser = ParserFactory.create("python")

# Parse file content
file_content = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

def main():
    result = hello("World")
    print(result)
"""

result = parser.parse(file_content, "example.py")

# Access parsed nodes
for node in result.nodes:
    print(f"{node.type}: {node.name} at line {node.start_line}")
```

### 2. Get Language from File Extension

```python
from libs.code_graph_rag.language_config import get_language_from_extension

language = get_language_from_extension(".py")  # Returns "python"
language = get_language_from_extension(".ts")  # Returns "typescript"
```

### 3. Build Graph (After AAET-84)

```python
from libs.code_graph_rag.graph_builder import GraphUpdater

# Note: GraphUpdater will be refactored in AAET-84 to use PostgreSQL
# Current version uses Memgraph (will be replaced)
```

---

## Directory Structure

```
libs/code_graph_rag/
├── __init__.py                      # Public API exports
├── README.md                        # This file
├── parsers/                         # Language parsers
│   ├── __init__.py
│   ├── factory.py                   # ParserFactory
│   ├── definition_processor.py     # Extract functions, classes
│   ├── call_processor.py           # Extract function calls
│   ├── import_processor.py         # Extract imports
│   ├── type_inference.py           # Type inference engine
│   ├── structure_processor.py      # Code structure analysis
│   ├── constants.py                # Parser constants
│   ├── utils.py                    # Common utilities
│   ├── python_utils.py             # Python-specific utils
│   ├── js_utils.py                 # JavaScript utils
│   ├── java_utils.py               # Java utils
│   ├── rust_utils.py               # Rust utils
│   ├── cpp_utils.py                # C++ utils
│   ├── lua_utils.py                # Lua utils
│   ├── js_type_inference.py        # JS type inference
│   ├── java_type_inference.py      # Java type inference
│   └── lua_type_inference.py       # Lua type inference
├── language_config.py              # Language definitions
├── schemas.py                      # Data models (ParsedNode, ParsedEdge)
├── parser_loader.py                # Parser initialization
└── graph_builder.py                # Graph construction (to be refactored)
```

---

## API Reference

### ParserFactory

```python
from libs.code_graph_rag.parsers.factory import ParserFactory

# Create parser
parser = ParserFactory.create(language: str)

# Parse file
result = parser.parse(content: str, file_path: str)
```

### GraphUpdater with Tenant Context (AAET-83)

```python
from libs.code_graph_rag.graph_builder import GraphUpdater
from pathlib import Path

# Create GraphUpdater with tenant context
updater = GraphUpdater(
    tenant_id="tenant-123",  # Required
    repo_id="repo-456",      # Required
    ingestor=ingestor,
    repo_path=Path("/path/to/repo"),
    parsers=parsers,
    queries=queries,
)

# Tenant context infrastructure is ready
# Actual node/edge dictionary updates will be completed in AAET-86
updater.run()
```

### GraphStoreInterface (AAET-84)

```python
from libs.code_graph_rag.storage import GraphStoreInterface, PostgresGraphStore

# Create PostgreSQL store
store = PostgresGraphStore("postgresql://user:pass@localhost/dbname")
await store.connect()

# Insert nodes
nodes = [
    {
        "tenant_id": "tenant-123",
        "repo_id": "repo-456",
        "type": "Function",
        "name": "hello",
        "qualified_name": "module.hello",
        "file_path": "module.py",
    }
]
await store.insert_nodes("tenant-123", nodes)

# Insert edges
edges = [
    {
        "tenant_id": "tenant-123",
        "from_node": "module.main",
        "to_node": "module.hello",
        "type": "CALLS",
    }
]
await store.insert_edges("tenant-123", edges)

# Query graph
results = await store.query_graph(
    "tenant-123",
    "SELECT * FROM code_nodes WHERE tenant_id = $1",
    {"tenant_id": "tenant-123"}
)

# Get neighbors
neighbors = await store.get_neighbors(
    "tenant-123",
    "module.main",
    edge_type="CALLS",
    direction="outgoing"
)

# Clean up
await store.close()
```

**Supported Backends:**
- ✅ PostgreSQL (via `PostgresGraphStore`)
- 🚧 Memgraph (legacy, to be deprecated)

---

## Roadmap

### ✅ AAET-82: Extract Library
- [x] Copy parsers directory
- [x] Copy language_config.py
- [x] Copy schemas.py
- [x] Rename graph_updater.py → graph_builder.py
- [x] Create __init__.py with exports
- [x] Add README.md

### ✅ AAET-83: Add Tenant Context Infrastructure
- [x] Add tenant_id parameter to GraphUpdater
- [x] Add repo_id parameter for multi-repo support
- [x] Update ProcessorFactory to accept tenant context
- [x] Add validation for tenant_id/repo_id
- [x] Update tests

### 🔵 AAET-84: Abstract Storage Interface (Current)
- [x] Create GraphStoreInterface abstract base class
- [x] Implement PostgresGraphStore
- [x] Add SQL migration for PostgreSQL tables
- [x] Add storage tests
- [x] Update documentation
- [ ] Refactor GraphUpdater to use interface
- [ ] Add configuration for backend selection
- [ ] Support both Memgraph and Postgres backends

### 🚧 AAET-85: Convert to Async (Next)
- [ ] Make parse methods async
- [ ] Add aiofiles for file reading
- [ ] Update all I/O operations

### 🚧 AAET-86: Parser Service Wrapper
- [ ] Create ParserService class
- [ ] Add tenant_id to node/edge dictionaries (from AAET-83)
- [ ] Add error handling and metrics
- [ ] Support all 9 languages

---

## Known Limitations (To Be Fixed)

1. **Memgraph Dependency** - graph_builder.py currently uses Memgraph
   - **Fix:** AAET-84 will replace with PostgreSQL
   
2. ~~**No Tenant Isolation**~~ - ✅ **FIXED in AAET-83**
   - tenant_id and repo_id now required in GraphUpdater
   - Validation rejects operations without tenant context
   
3. **Synchronous Operations** - All operations are blocking
   - **Fix:** AAET-85 will convert to async
   
4. **External Tool Dependencies** - Some parsers call external tools
   - **Fix:** Will be made optional in future refactoring
   
5. **Node/Edge Dictionary Updates** - Tenant context not yet added to dictionaries
   - **Fix:** Will be added in **AAET-86 (Parser Service Wrapper)**
   - AAET-83 added infrastructure; AAET-86 will add to actual node/edge dicts

---

## Contributing

This library is extracted from the open-source code-graph-rag project.

**Upstream:** https://github.com/vitali87/code-graph-rag

Changes made for aelus-aether:
- Extracted as standalone library
- Will add tenant context (AAET-83)
- Will replace Memgraph with PostgreSQL (AAET-84)
- Will convert to async (AAET-85)

---

## License

MIT License (inherited from code-graph-rag)

---

**Status:** ✅ AAET-83 Complete - Tenant Context Added  
**Next:** AAET-84 - Abstract Storage Interface
