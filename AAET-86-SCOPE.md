# AAET-86: Build Parser Service Wrapper - SCOPE DOCUMENT

## 🎯 CRITICAL: This Story Has TWO Parts

**Part 1:** Complete AAET-83 deferred work (tenant_id in data layer)  
**Part 2:** Create ParserService wrapper (service layer)

---

## 📋 JIRA Requirements

**Title:** Build Parser Service Wrapper  
**Estimated Effort:** 4 days (3 original + 1 for AAET-83 completion)

### Acceptance Criteria (13 items):

#### From AAET-83 (Deferred Work) - 4 items:
1. ✅ Add tenant_id to all node dictionaries during parsing
2. ✅ Add tenant_id to all edge dictionaries during parsing
3. ✅ Modify processor methods to inject tenant context into parsed data
4. ✅ Ensure all generated nodes include tenant_id and repo_id

#### Parser Service (Original Scope) - 9 items:
5. ✅ Create `services/ingestion/parser_service.py`
6. ✅ Implement `ParserService` class
7. ✅ Add method `parse_file(tenant_id, repo_id, file_path, content, language)`
8. ✅ Add error handling and retry logic
9. ✅ Add metrics collection (parse time, node count)
10. ✅ Add logging with tenant context
11. ✅ Support all 9 languages from code-graph-rag
12. ✅ Add validation for tenant quotas
13. ✅ Write unit tests

---

## ⚠️ CRITICAL SCOPE CLARIFICATION

### What AAET-83 Did (Infrastructure Only):
```python
# GraphUpdater accepts tenant_id parameter
class GraphUpdater:
    def __init__(self, tenant_id: str, repo_id: str, store: GraphStoreInterface, ...):
        self.tenant_id = tenant_id  # ✅ Stored in instance
        self.repo_id = repo_id      # ✅ Stored in instance
```

### What AAET-83 Did NOT Do (Deferred to AAET-86):
```python
# Processors DO NOT inject tenant_id into node/edge dictionaries yet
node = {
    'tenant_id': self.tenant_id,  # ❌ NOT IMPLEMENTED YET
    'repo_id': self.repo_id,      # ❌ NOT IMPLEMENTED YET
    'type': 'Function',
    'name': function_name,
}
```

**This is the work we need to complete in Part 1 of AAET-86!**

---

## 🎯 EXACT SCOPE (No Scope Creep)

### PART 1: Complete AAET-83 Deferred Work

**What IS in scope:**
1. ✅ Modify `DefinitionProcessor` to inject `tenant_id` and `repo_id` into node dictionaries
2. ✅ Modify `StructureProcessor` to inject `tenant_id` and `repo_id` into node dictionaries
3. ✅ Modify `CallProcessor` to inject `tenant_id` and `repo_id` into edge dictionaries
4. ✅ Modify `ImportProcessor` to inject `tenant_id` and `repo_id` into edge dictionaries
5. ✅ Ensure all `ensure_node_batch()` calls include tenant context in properties
6. ✅ Ensure all `ensure_relationship_batch()` calls include tenant context in properties

**What is NOT in scope:**
- ❌ Changing processor constructors (they already receive tenant_id from GraphUpdater)
- ❌ Modifying GraphUpdater (already done in AAET-83)
- ❌ Modifying storage layer (already done in AAET-84/85)
- ❌ New processor methods
- ❌ New validation logic

### PART 2: Create ParserService Wrapper

**What IS in scope:**
1. ✅ Create `services/ingestion/` directory structure
2. ✅ Create `parser_service.py` with `ParserService` class
3. ✅ Implement `parse_repository()` method (wraps GraphUpdater.run())
4. ✅ Add error handling with proper exceptions
5. ✅ Add metrics collection (parse time, node count, error count)
6. ✅ Add structured logging with tenant context
7. ✅ Support all 9 languages (Python, TypeScript, JavaScript, Java, Go, Ruby, PHP, Rust, C#)
8. ✅ Add tenant quota validation (placeholder for now)
9. ✅ Write unit tests for service layer

**What is NOT in scope:**
- ❌ Actual metrics backend integration (use placeholder)
- ❌ Actual quota enforcement (use placeholder validation)
- ❌ Retry logic (simple error handling only)
- ❌ Celery task integration (separate story)
- ❌ FastAPI endpoint integration (separate story)
- ❌ New parsers or language support
- ❌ Performance optimizations
- ❌ Caching mechanisms

---

## 📝 Files to Create/Modify

### PART 1: Tenant Context in Data Layer

**Files to Modify (4 files):**
1. `libs/code_graph_rag/parsers/definition_processor.py`
   - Inject `tenant_id` and `repo_id` into all node dictionaries

2. `libs/code_graph_rag/parsers/structure_processor.py`
   - Inject `tenant_id` and `repo_id` into all node dictionaries

3. `libs/code_graph_rag/parsers/call_processor.py`
   - Inject `tenant_id` and `repo_id` into all edge dictionaries

4. `libs/code_graph_rag/parsers/import_processor.py`
   - Inject `tenant_id` and `repo_id` into all edge dictionaries

### PART 2: Service Layer

**Files to Create (3 files):**
5. `services/__init__.py` - Package marker
6. `services/ingestion/__init__.py` - Package marker
7. `services/ingestion/parser_service.py` - Main service class

**Files to Create (Tests - 1 file):**
8. `tests/services/test_parser_service.py` - Unit tests

---

## 🚀 Implementation Plan (2 Parts, 7 Phases)

### PART 1: Complete AAET-83 Deferred Work (2 days)

#### Phase 1: DefinitionProcessor (4 hours)
- [ ] Inject `tenant_id` and `repo_id` into all node dictionaries
- [ ] Update all `ensure_node_batch()` calls
- [ ] Test with sample Python file

#### Phase 2: StructureProcessor (2 hours)
- [ ] Inject `tenant_id` and `repo_id` into all node dictionaries
- [ ] Update all `ensure_node_batch()` calls
- [ ] Test with sample file

#### Phase 3: CallProcessor (2 hours)
- [ ] Inject `tenant_id` and `repo_id` into all edge dictionaries
- [ ] Update all `ensure_relationship_batch()` calls
- [ ] Test with sample file

#### Phase 4: ImportProcessor (2 hours)
- [ ] Inject `tenant_id` and `repo_id` into all edge dictionaries
- [ ] Update all `ensure_relationship_batch()` calls
- [ ] Test with sample file

### PART 2: Create ParserService Wrapper (2 days)

#### Phase 5: Service Structure (2 hours)
- [ ] Create directory structure
- [ ] Create `ParserService` class skeleton
- [ ] Add basic error handling

#### Phase 6: Service Implementation (4 hours)
- [ ] Implement `parse_repository()` method
- [ ] Add metrics collection (placeholder)
- [ ] Add structured logging
- [ ] Add quota validation (placeholder)

#### Phase 7: Tests & Documentation (2 hours)
- [ ] Write unit tests
- [ ] Add docstrings
- [ ] Create usage examples
- [ ] Update README

---

## 🔧 Technical Implementation

### PART 1: Tenant Context in Data Layer

**Before (AAET-83 - Infrastructure only):**
```python
class DefinitionProcessor:
    def __init__(self, ingestor, tenant_id, repo_id, ...):
        self.tenant_id = tenant_id  # ✅ Stored but not used in data
        self.repo_id = repo_id

    def process_function(self, node, file_path):
        # Create node WITHOUT tenant context
        self.ingestor.ensure_node_batch("Function", {
            "name": node.name,
            "qualified_name": qname,
            # ❌ No tenant_id or repo_id
        })
```

**After (AAET-86 Part 1 - Data layer complete):**
```python
class DefinitionProcessor:
    def __init__(self, ingestor, tenant_id, repo_id, ...):
        self.tenant_id = tenant_id
        self.repo_id = repo_id

    def process_function(self, node, file_path):
        # Create node WITH tenant context
        self.ingestor.ensure_node_batch("Function", {
            "tenant_id": self.tenant_id,      # ✅ Added
            "repo_id": self.repo_id,          # ✅ Added
            "name": node.name,
            "qualified_name": qname,
        })
```

### PART 2: Service Layer

**New Service Class:**
```python
# services/ingestion/parser_service.py
from libs.code_graph_rag.graph_builder import GraphUpdater
from libs.code_graph_rag.storage import PostgresGraphStore
import logging
import time

logger = logging.getLogger(__name__)

class ParserService:
    """Service layer for code parsing with tenant context and metrics."""

    def __init__(self, store: PostgresGraphStore):
        self.store = store

    async def parse_repository(
        self,
        tenant_id: str,
        repo_id: str,
        repo_path: str,
    ) -> dict:
        """Parse a repository and return metrics.

        Args:
            tenant_id: Tenant identifier
            repo_id: Repository identifier
            repo_path: Path to repository

        Returns:
            dict with keys: nodes_created, edges_created, parse_time_seconds

        Raises:
            ValueError: If tenant_id or repo_id invalid
            StorageError: If database operation fails
        """
        start_time = time.time()

        # Validate inputs
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not repo_id or not repo_id.strip():
            raise ValueError("repo_id is required")

        logger.info(
            f"Starting repository parse",
            extra={"tenant_id": tenant_id, "repo_id": repo_id}
        )

        try:
            # Set tenant context
            self.store.set_tenant_id(tenant_id)

            # Create GraphUpdater
            updater = GraphUpdater(
                tenant_id=tenant_id,
                repo_id=repo_id,
                store=self.store,
                repo_path=Path(repo_path),
                parsers=self._get_parsers(),
                queries=self._get_queries(),
            )

            # Run parsing (tenant_id flows to all nodes/edges)
            await updater.run()

            # Calculate metrics
            parse_time = time.time() - start_time

            # TODO: Get actual counts from storage
            metrics = {
                "nodes_created": 0,  # Placeholder
                "edges_created": 0,  # Placeholder
                "parse_time_seconds": parse_time,
            }

            logger.info(
                f"Repository parse complete",
                extra={"tenant_id": tenant_id, "repo_id": repo_id, **metrics}
            )

            return metrics

        except Exception as e:
            logger.error(
                f"Repository parse failed: {e}",
                extra={"tenant_id": tenant_id, "repo_id": repo_id},
                exc_info=True
            )
            raise

    def _get_parsers(self) -> dict:
        """Get parser configuration for all supported languages."""
        # TODO: Load from config
        return {}

    def _get_queries(self) -> dict:
        """Get query configuration for parsers."""
        # TODO: Load from config
        return {}
```

---

## ✅ Definition of Done

### PART 1: Tenant Context in Data Layer
- [ ] All node dictionaries include `tenant_id` and `repo_id`
- [ ] All edge dictionaries include `tenant_id` and `repo_id`
- [ ] All processors inject tenant context
- [ ] Manual test shows tenant_id in database

### PART 2: Service Layer
- [ ] `ParserService` class created
- [ ] `parse_repository()` method implemented
- [ ] Error handling with proper exceptions
- [ ] Structured logging with tenant context
- [ ] Metrics collection (placeholder)
- [ ] Quota validation (placeholder)
- [ ] Unit tests pass
- [ ] Documentation complete

---

## ⚠️ Breaking Changes

**None** - This is additive work only:
- Part 1 adds fields to existing dictionaries (backward compatible)
- Part 2 creates new service layer (no existing code affected)

---

## 🔗 Dependencies

- **AAET-83** ✅ Complete - GraphUpdater accepts tenant_id
- **AAET-84** ✅ Complete - PostgresGraphStore available
- **AAET-85** ✅ Complete - Async operations available

---

## 📊 Success Metrics

- [ ] All nodes in database have `tenant_id` and `repo_id`
- [ ] All edges in database have `tenant_id` and `repo_id`
- [ ] ParserService successfully wraps GraphUpdater
- [ ] Metrics are collected and logged
- [ ] Errors are properly handled and logged
- [ ] Tests cover happy path and error cases

---

## 🎯 Reviewer Checklist (No Scope Creep)

### PART 1: Tenant Context
1. ✅ Only adds `tenant_id` and `repo_id` to existing dictionaries
2. ✅ No new processor methods added
3. ✅ No changes to processor constructors
4. ✅ No changes to GraphUpdater
5. ✅ No changes to storage layer

### PART 2: Service Layer
1. ✅ Only creates new service layer (no existing code modified)
2. ✅ Only wraps existing GraphUpdater (no new parsing logic)
3. ✅ Only adds logging and metrics (no new features)
4. ✅ Quota validation is placeholder only
5. ✅ Metrics backend is placeholder only
6. ✅ No Celery or FastAPI integration

---

## 📝 Summary

**PART 1:** Complete deferred work from AAET-83 - inject tenant_id into data  
**PART 2:** Create service layer wrapper with logging and metrics  
**Total Effort:** 4 days  
**Scope Creep Risk:** LOW (clearly defined, no new features)

**Ready to implement!** 🚀
