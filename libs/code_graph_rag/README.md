# code-graph-rag Library

This directory will contain the extracted code-graph-rag library components.

## Extraction Status

- [ ] **AAET-82:** Extract library components
  - [ ] Copy `parsers/` directory
  - [ ] Copy `language_config.py`
  - [ ] Copy `schemas.py`
  - [ ] Refactor `graph_updater.py` → `graph_builder.py`

## Next Steps

1. Run AAET-82 to extract the library
2. Add tenant context (AAET-83)
3. Abstract storage interface (AAET-84)
4. Convert to async (AAET-85)

## Usage (After Extraction)

```python
from libs.code_graph_rag.parsers import ParserFactory
from libs.code_graph_rag.graph_builder import GraphBuilder

# Parse a file
parser = ParserFactory.create("python")
ast_result = parser.parse(file_content, file_path)

# Build graph
graph_builder = GraphBuilder(tenant_id="...", repo_id="...")
nodes, edges = graph_builder.build_from_ast(ast_result)
```

## Directory Structure (Target)

```
libs/code_graph_rag/
├── __init__.py
├── parsers/
│   ├── __init__.py
│   ├── definition_processor.py
│   ├── call_processor.py
│   ├── type_inference.py
│   └── ... (18 files total)
├── graph_builder.py
├── language_config.py
├── schemas.py
└── storage_interface.py (NEW)
```
