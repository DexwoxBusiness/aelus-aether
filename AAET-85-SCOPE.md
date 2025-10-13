# AAET-85: Convert code-graph-rag to Async Operations

## 📋 JIRA Story Details

**Title:** Convert code-graph-rag to Async Operations  
**Type:** Story  
**Status:** Backlog  
**Priority:** Medium  
**Estimated Effort:** 2 days

---

## 🎯 Objective

Convert synchronous file I/O and database operations in code-graph-rag to async/await pattern for compatibility with FastAPI and Celery async tasks.

---

## ✅ Acceptance Criteria (from JIRA)

1. **[ ] Convert file reading to `aiofiles`**
2. **[ ] Make `parse_file()` async**
3. **[ ] Make `build_from_ast()` async where needed**
4. **[ ] Make storage operations async**
5. **[ ] Update all callers to use `await`**
6. **[ ] Add asyncio event loop handling**
7. **[ ] Update tests to use `pytest-asyncio`**
8. **[ ] Verify performance with async operations**

---

## 🔧 Technical Implementation

### Before (Sync):
```python
def parse_file(self, file_path: str):
    with open(file_path, 'r') as f:
        content = f.read()
    return self._parse(content)
```

### After (Async):
```python
async def parse_file(self, file_path: str):
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    return self._parse(content)
```

---

## 📦 Dependencies to Add

1. **`aiofiles`** - Async file I/O
2. **`asyncpg`** - Async PostgreSQL (already added in AAET-84)
3. **`pytest-asyncio`** - Async test support

---

## ✅ Definition of Done

- [ ] All I/O operations are async
- [ ] FastAPI can call library without blocking
- [ ] Celery tasks work with async code
- [ ] Tests pass with async operations
- [ ] No blocking I/O in critical paths

---

## 🎯 EXACT SCOPE (No Scope Creep)

### What IS in scope:

1. **File I/O Operations**
   - Convert `open()` to `aiofiles.open()`
   - Make file reading async in parsers
   - Update `parse_file()` methods

2. **Parser Methods**
   - Make `parse_file()` async
   - Make `build_from_ast()` async where needed
   - Update parser factory methods

3. **Storage Operations**
   - Already async in AAET-84 (PostgresGraphStore)
   - Remove SyncGraphStoreWrapper
   - Make GraphUpdater.run() async

4. **Caller Updates**
   - Update all callers to use `await`
   - Add async event loop handling where needed

5. **Testing**
   - Add `pytest-asyncio`
   - Convert tests to async
   - Verify performance

### What is NOT in scope:

- ❌ New features
- ❌ Additional storage backends
- ❌ Performance optimizations beyond async conversion
- ❌ New parsers or language support
- ❌ API changes beyond async/await
- ❌ Database migrations (done in AAET-84)
- ❌ Security enhancements (done in AAET-84)
- ❌ Configuration changes (done in AAET-84)

---

## 📝 Files to Modify

### Core Files:
1. **`libs/code_graph_rag/parsers/base.py`** - Make parse_file() async
2. **`libs/code_graph_rag/parsers/python_parser.py`** - Update file I/O
3. **`libs/code_graph_rag/parsers/typescript_parser.py`** - Update file I/O
4. **`libs/code_graph_rag/parsers/java_parser.py`** - Update file I/O
5. **`libs/code_graph_rag/graph_builder.py`** - Make GraphUpdater.run() async
6. **`libs/code_graph_rag/storage/sync_wrapper.py`** - DELETE (no longer needed)

### Test Files:
7. **`tests/test_*.py`** - Convert to pytest-asyncio

### Dependencies:
8. **`requirements.txt`** or **`pyproject.toml`** - Add aiofiles, pytest-asyncio

---

## 🚀 Implementation Plan

### Phase 1: Dependencies
- [ ] Add `aiofiles` to requirements
- [ ] Add `pytest-asyncio` to dev requirements
- [ ] Verify `asyncpg` is already present (from AAET-84)

### Phase 2: Parser Base Classes
- [ ] Make `Parser.parse_file()` async in base class
- [ ] Update abstract methods to be async

### Phase 3: Concrete Parsers
- [ ] Convert PythonParser file I/O to aiofiles
- [ ] Convert TypeScriptParser file I/O to aiofiles
- [ ] Convert JavaParser file I/O to aiofiles
- [ ] Make `build_from_ast()` async where needed

### Phase 4: GraphUpdater
- [ ] Make `GraphUpdater.run()` async
- [ ] Remove SyncGraphStoreWrapper usage
- [ ] Use PostgresGraphStore directly (async)
- [ ] Update all internal method calls to use await

### Phase 5: Callers
- [ ] Update all callers to use `await`
- [ ] Add asyncio event loop handling where needed
- [ ] Update CLI scripts if any

### Phase 6: Tests
- [ ] Add pytest-asyncio markers
- [ ] Convert test functions to async
- [ ] Update test fixtures for async
- [ ] Verify all tests pass

### Phase 7: Cleanup
- [ ] Delete `sync_wrapper.py`
- [ ] Update documentation
- [ ] Update README examples to show async usage

---

## ⚠️ Breaking Changes

**This is a BREAKING CHANGE:**

### Before (AAET-84):
```python
# Sync usage with wrapper
updater = GraphUpdater(...)
updater.run()  # Synchronous
```

### After (AAET-85):
```python
# Async usage
updater = GraphUpdater(...)
await updater.run()  # Asynchronous
```

**Migration Guide Required:**
- Document how to update existing code
- Provide examples for FastAPI integration
- Provide examples for Celery integration

---

## 🔗 Related Stories

- **AAET-84** (Complete) - Created async storage interface (PostgresGraphStore)
- **AAET-85** (This Story) - Convert parsers and GraphUpdater to async
- **AAET-86** (Future) - Parser service wrapper (will use async code)

---

## 📊 Success Metrics

- [ ] All file I/O uses aiofiles
- [ ] All storage operations are async (no SyncWrapper)
- [ ] All tests pass with pytest-asyncio
- [ ] No blocking I/O in critical paths
- [ ] FastAPI integration works without blocking
- [ ] Celery tasks work with async code

---

## 🎯 Reviewer Checklist

To avoid scope creep, reviewer should verify:

1. ✅ Only file I/O converted to aiofiles (no new features)
2. ✅ Only existing methods made async (no new methods)
3. ✅ Only existing tests converted (no new test scenarios)
4. ✅ No new storage backends added
5. ✅ No performance optimizations beyond async
6. ✅ No new dependencies beyond aiofiles and pytest-asyncio
7. ✅ Documentation updated for async usage only

---

## 📝 Notes

- This builds on AAET-84's async storage interface
- Removes the temporary SyncGraphStoreWrapper
- Enables non-blocking FastAPI and Celery integration
- All changes are internal - no new features added
