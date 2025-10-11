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
pip install tree-sitter
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
pip install tree-sitter-java tree-sitter-go tree-sitter-rust
pip install tree-sitter-scala tree-sitter-cpp tree-sitter-lua
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

### ParsedNode (with Tenant Context)

```python
from libs.code_graph_rag.schemas import ParsedNode, NodeType
from uuid import UUID

# Create a node with tenant context (AAET-83)
node = ParsedNode(
    tenant_id=UUID("12345678-1234-1234-1234-123456789012"),  # Required
    repo_id=UUID("87654321-4321-4321-4321-210987654321"),    # Required
    node_type=NodeType.FUNCTION,
    name="hello",
    qualified_name="module.hello",
    file_path="src/module.py",
    start_line=1,
    end_line=3,
    source_code="def hello(): pass",
    signature="def hello() -> None",
    docstring="Function docstring",
    language="python",
)
```

### ParsedEdge (with Tenant Context)

```python
from libs.code_graph_rag.schemas import ParsedEdge, EdgeType
from uuid import UUID

# Create an edge with tenant context (AAET-83)
edge = ParsedEdge(
    tenant_id=UUID("12345678-1234-1234-1234-123456789012"),  # Required
    from_node="module.main",
    to_node="module.hello",
    edge_type=EdgeType.CALLS,
)
```

### ParsedFile (Complete Example)

```python
from libs.code_graph_rag.schemas import ParsedFile, ParsedNode, ParsedEdge, NodeType, EdgeType
from uuid import UUID

# Parse result with tenant context
parsed_file = ParsedFile(
    tenant_id=UUID("12345678-1234-1234-1234-123456789012"),
    repo_id=UUID("87654321-4321-4321-4321-210987654321"),
    file_path="src/module.py",
    language="python",
    nodes=[
        ParsedNode(
            tenant_id=UUID("12345678-1234-1234-1234-123456789012"),
            repo_id=UUID("87654321-4321-4321-4321-210987654321"),
            node_type=NodeType.FUNCTION,
            name="hello",
            qualified_name="module.hello",
            file_path="src/module.py",
            start_line=1,
            end_line=3,
        )
    ],
    edges=[
        ParsedEdge(
            tenant_id=UUID("12345678-1234-1234-1234-123456789012"),
            from_node="module.main",
            to_node="module.hello",
            edge_type=EdgeType.CALLS,
        )
    ],
)
```

---

## Roadmap

### ✅ AAET-82: Extract Library
- [x] Copy parsers directory
- [x] Copy language_config.py
- [x] Copy schemas.py
- [x] Rename graph_updater.py → graph_builder.py
- [x] Create __init__.py with exports
- [x] Add README.md

### ✅ AAET-83: Add Tenant Context (Complete)
- [x] Add tenant_id to all nodes/edges
- [x] Add repo_id for multi-repo support
- [x] Update schemas with tenant fields
- [x] Add NodeType and EdgeType enums
- [x] Create ParsedNode, ParsedEdge, ParsedFile models
- [x] Add UUID format validation
- [x] Enforce strict schema validation

**Note:** This story adds **schema-level** tenant context only. Actual parser integration 
with these schemas happens in **AAET-86 (Parser Service Wrapper)**.

### 🚧 AAET-84: Abstract Storage Interface (Next)
- [ ] Remove Memgraph dependency
- [ ] Create GraphStoreInterface
- [ ] Implement PostgresGraphStore
- [ ] Update graph_builder.py

### 🚧 AAET-85: Convert to Async
- [ ] Make parse methods async
- [ ] Add aiofiles for file reading
- [ ] Update all I/O operations

### 🚧 AAET-86: Parser Service Wrapper
- [ ] Create ParserService class
- [ ] **Integrate parsers with tenant-aware schemas** ← Parser integration happens here
- [ ] Accept tenant_id/repo_id in service methods
- [ ] Convert parser output to ParsedNode/ParsedEdge/ParsedFile
- [ ] Use GraphStoreInterface to persist parsed data

**Note:** This is where the actual parser integration with tenant context happens. 
AAET-83 only created the schemas; AAET-86 makes parsers use them.

---

## Known Limitations (To Be Fixed)

1. **Memgraph Dependency** - graph_builder.py currently uses Memgraph
   - **Fix:** AAET-84 will replace with PostgreSQL
   
2. ~~**No Tenant Isolation**~~ - ✅ **FIXED in AAET-83**
   - tenant_id and repo_id now required in all schemas
   - ParsedNode, ParsedEdge, ParsedFile all support multi-tenancy
   
3. **Synchronous Operations** - All operations are blocking
   - **Fix:** AAET-85 will convert to async
   
4. **External Tool Dependencies** - Some parsers call external tools
   - **Fix:** Will be made optional in future refactoring
   
5. **Parser Integration** - Parsers don't yet use new schemas
   - **Fix:** Will be integrated in **AAET-86 (Parser Service Wrapper)**
   - AAET-83 only added schemas; AAET-86 will make parsers use them

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
