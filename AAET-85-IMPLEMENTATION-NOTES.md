# AAET-85 Implementation Notes

## Progress: Phase 4 - GraphUpdater Async Conversion

### ✅ Completed

1. **GraphUpdater.__init__()** - Simplified to PostgreSQL-only
   - Removed MemgraphIngestor import
   - Changed parameter from `ingestor: MemgraphIngestor | GraphStoreInterface` to `store: GraphStoreInterface`
   - Removed dual interface logic

2. **GraphUpdater.run()** - Made async
   - Changed `def run()` to `async def run()`
   - Replaced `self.ingestor.ensure_node_batch()` with `await self.store.insert_nodes()`
   - Added `await` to all processor method calls
   - Removed `self.ingestor.flush_all()` (not needed with async PostgreSQL)

3. **GraphUpdater._process_files()** - Made async
   - Changed `def _process_files()` to `async def _process_files()`
   - Added `await` to all processor calls

4. **GraphUpdater._process_function_calls()** - Made async
   - Changed `def _process_function_calls()` to `async def _process_function_calls()`
   - Added `await` to processor calls

### ⚠️ Remaining Work

All processor methods need to be made async. This is a large change affecting:

#### Processors to Convert:

1. **StructureProcessor**
   - `identify_structure()` → `async def`
   - `process_generic_file()` → `async def`

2. **DefinitionProcessor**
   - `process_file()` → `async def` (needs aiofiles for file I/O)
   - `process_dependencies()` → `async def` (needs aiofiles)
   - `process_all_method_overrides()` → `async def`

3. **CallProcessor**
   - `process_calls_in_file()` → `async def`

4. **ImportProcessor**
   - Methods that read files → `async def` with aiofiles

### 📝 File I/O Conversion Strategy

#### Files with `open()` calls:

1. **`definition_processor.py`** (5 occurrences)
   - `_parse_requirements_txt()` - Line 256
   - `_parse_package_json()` - Line 270
   - `_parse_go_mod()` - Line 310
   - `_parse_gemfile()` - Line 339
   - `_parse_composer_json()` - Line 357

2. **`import_processor.py`** (3 occurrences)
   - `_load_stdlib_cache()` - Line 110
   - `_save_stdlib_cache()` - Line 126
   - Subprocess call - Line 1368 (not file I/O)

#### Conversion Pattern:

**Before:**
```python
with open(filepath, encoding="utf-8") as f:
    content = f.read()
```

**After:**
```python
import aiofiles

async with aiofiles.open(filepath, encoding="utf-8") as f:
    content = await f.read()
```

### 🎯 Next Steps

1. **Convert DefinitionProcessor file I/O methods**
   - Make `_parse_requirements_txt()` async
   - Make `_parse_package_json()` async
   - Make `_parse_go_mod()` async
   - Make `_parse_gemfile()` async
   - Make `_parse_composer_json()` async
   - Make `process_file()` async
   - Make `process_dependencies()` async

2. **Convert ImportProcessor file I/O methods**
   - Make `_load_stdlib_cache()` async
   - Make `_save_stdlib_cache()` async

3. **Convert all processor public methods to async**
   - Update method signatures
   - Add `await` to all file I/O calls
   - Add `await` to all storage calls

4. **Update ProcessorFactory**
   - May need to handle async processor creation

5. **Update tests**
   - Add `pytest-asyncio` markers
   - Convert test functions to async
   - Update fixtures

### ⚠️ Breaking Changes

**This is a BREAKING CHANGE** - All public methods become async:

```python
# Before
updater = GraphUpdater(tenant_id, repo_id, store, ...)
updater.run()

# After
updater = GraphUpdater(tenant_id, repo_id, store, ...)
await updater.run()
```

### 📊 Estimated Remaining Work

- **Definition Processor:** 2-3 hours (many file I/O methods)
- **Import Processor:** 1 hour
- **Structure Processor:** 1 hour
- **Call Processor:** 30 minutes
- **Tests:** 1-2 hours
- **Documentation:** 30 minutes

**Total:** ~6-8 hours remaining

### 🚀 Approach

Given the size of this change, we should:

1. ✅ **Commit current progress** (GraphUpdater async)
2. **Convert processors one by one** (definition → import → structure → call)
3. **Test incrementally** after each processor
4. **Update documentation** as we go

This ensures we can track progress and catch issues early.
