# Git Workflow for Aelus-Aether

## Initial Setup

### 1. Initialize Git Repository

```bash
cd aelus-aether

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "feat: Phase 1 - FastAPI scaffolding with database models

- Setup FastAPI application with async support
- Create database models (Tenant, Repository, CodeNode, CodeEdge, CodeEmbedding)
- Implement basic API endpoints (tenants, repositories)
- Add Docker Compose for PostgreSQL + Redis
- Configure environment and settings
- Add tests and documentation

Implements: AAET-81 (EPIC-6 Phase 1)
Related: AAET-82 (pending - library extraction)"
```

### 2. Create Remote Repository

```bash
# On GitHub/GitLab, create a new repository: aelus-aether

# Add remote
git remote add origin <your-repo-url>

# Push to main
git branch -M main
git push -u origin main
```

---

## Branch Strategy

### Main Branches

- **`main`** - Production-ready code
- **`develop`** - Integration branch for features

### Feature Branches

Format: `feature/AAET-XX-short-description`

Examples:
- `feature/AAET-82-extract-library`
- `feature/AAET-83-add-tenant-context`
- `feature/AAET-86-parser-service`

---

## Workflow for Each JIRA Story

### Step 1: Create Feature Branch

```bash
# Ensure you're on develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/AAET-82-extract-library
```

### Step 2: Make Changes

```bash
# Work on your feature
# Make commits as you go

git add <files>
git commit -m "feat(AAET-82): extract parsers from code-graph-rag

- Copy parsers directory
- Copy language_config.py
- Add __init__.py files"
```

### Step 3: Push to Remote

```bash
# Push feature branch
git push -u origin feature/AAET-82-extract-library
```

### Step 4: Create Pull Request

1. Go to GitHub/GitLab
2. Create PR from `feature/AAET-82-extract-library` → `develop`
3. Title: `[AAET-82] Extract code-graph-rag as Library`
4. Description:
   ```markdown
   ## JIRA Story
   [AAET-82](link-to-jira)

   ## Changes
   - Extracted parsers from code-graph-rag
   - Added library structure in libs/code_graph_rag/
   - Updated documentation

   ## Testing
   - [ ] All tests pass
   - [ ] Parsers import correctly
   - [ ] No breaking changes

   ## Checklist
   - [ ] Code follows style guide
   - [ ] Tests added/updated
   - [ ] Documentation updated
   ```

### Step 5: Review and Merge

```bash
# After PR approval, merge to develop
# Then delete feature branch

git checkout develop
git pull origin develop
git branch -d feature/AAET-82-extract-library
```

---

## Commit Message Convention

Format: `<type>(<scope>): <subject>`

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Code style changes (formatting)
- **refactor**: Code refactoring
- **test**: Adding/updating tests
- **chore**: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(AAET-86): add parser service wrapper"

# Bug fix
git commit -m "fix(database): correct tenant isolation query"

# Documentation
git commit -m "docs: update setup guide with Docker instructions"

# Refactor
git commit -m "refactor(AAET-84): abstract storage interface"

# Test
git commit -m "test(AAET-88): add integration tests for parsers"
```

---

## Phase 1: Initial Push

### Current State

```bash
# Check status
git status

# Should show:
# - pyproject.toml
# - app/ directory
# - libs/ directory
# - tests/ directory
# - docker-compose.yaml
# - README.md, SETUP.md, etc.
```

### Push to Git

```bash
# Stage all files
git add .

# Commit
git commit -m "feat: Phase 1 - FastAPI scaffolding complete

## What's Included

### Application Structure
- FastAPI app with async support
- Database models (SQLAlchemy + pgvector)
- API endpoints (tenants, repositories, ingestion, retrieval)
- Pydantic schemas for validation

### Database
- PostgreSQL 15 + pgvector support
- Multi-tenant models with RLS
- Code graph models (nodes, edges, embeddings)

### Infrastructure
- Docker Compose (PostgreSQL + Redis)
- Environment configuration
- Makefile for common tasks

### Documentation
- README.md with quick start
- SETUP.md with detailed instructions
- API documentation (Swagger/ReDoc)

### Testing
- Basic API tests
- Test configuration

## Implementation Status

✅ Completed:
- AAET-81 Phase 1 scaffolding
- Database schema design
- API endpoint structure
- Docker setup

🚧 Next Steps:
- AAET-82: Extract code-graph-rag library
- AAET-83: Add tenant context
- AAET-84: Abstract storage interface

## How to Run

\`\`\`bash
make setup  # Install deps + start Docker
make run    # Start API server
\`\`\`

See SETUP.md for detailed instructions.

Implements: AAET-81 (EPIC-6 Phase 1)
Related: Architecture documented in ../AELUS_AETHER_ARCHITECTURE.md"

# Push to remote
git push -u origin main
```

---

## Next Branch: Library Extraction

```bash
# Create branch for AAET-82
git checkout -b feature/AAET-82-extract-library

# Work on extraction
# (Copy files from ../codebase_rag/)

# Commit and push
git add libs/code_graph_rag/
git commit -m "feat(AAET-82): extract code-graph-rag parsers

- Copy parsers directory (18 files)
- Copy language_config.py
- Copy schemas.py
- Add library structure
- Update documentation

Story: AAET-82"

git push -u origin feature/AAET-82-extract-library
```

---

## Useful Git Commands

### Check Status

```bash
git status                    # Current changes
git log --oneline -10         # Recent commits
git branch -a                 # All branches
```

### Sync with Remote

```bash
git fetch origin              # Fetch changes
git pull origin develop       # Pull latest develop
git rebase origin/develop     # Rebase on develop
```

### Undo Changes

```bash
git checkout -- <file>        # Discard changes
git reset HEAD <file>         # Unstage file
git reset --soft HEAD~1       # Undo last commit (keep changes)
git reset --hard HEAD~1       # Undo last commit (discard changes)
```

### View Changes

```bash
git diff                      # Unstaged changes
git diff --staged             # Staged changes
git diff main..develop        # Compare branches
```

---

## Release Process (Future)

### When Ready for Production

```bash
# Merge develop to main
git checkout main
git merge develop

# Tag release
git tag -a v0.1.0 -m "Release v0.1.0 - Phase 1 Complete"
git push origin main --tags
```

---

## .gitignore Highlights

Already configured to ignore:
- `__pycache__/`, `*.pyc`
- `.env`, `.env.local`
- `venv/`, `.venv/`
- `.pytest_cache/`, `.mypy_cache/`
- Database files
- IDE files

---

**Ready to push!** 🚀

Run these commands to get started:

```bash
cd aelus-aether
git init
git add .
git commit -m "feat: Phase 1 - FastAPI scaffolding complete"
# Add your remote and push
```
