# Contributing to Aelus-Aether

Thank you for your interest in contributing to Aelus-Aether! This document provides guidelines and workflows for development.

## Table of Contents

- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)

## Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- Docker & Docker Compose
- Git

### Initial Setup

1. **Fork and clone the repository:**
```bash
git clone https://github.com/your-username/aelus-aether.git
cd aelus-aether
```

2. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"
```

3. **Install pre-commit hooks:**
```bash
pre-commit install
```

4. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your local configuration
```

5. **Start services:**
```bash
docker-compose up -d
```

6. **Run migrations:**
```bash
alembic upgrade head
```

7. **Verify setup:**
```bash
# Run tests
pytest

# Start API server
uvicorn app.main:app --reload

# Start Celery worker (in another terminal)
celery -A workers.celery_app worker --pool=solo --loglevel=info
```

## Development Workflow

### Branch Naming Convention

Use descriptive branch names following this pattern:
```
feature/AAET-XX-short-description
bugfix/AAET-XX-short-description
hotfix/AAET-XX-short-description
```

Examples:
- `feature/AAET-21-developer-documentation`
- `bugfix/AAET-19-fix-async-tests`
- `hotfix/AAET-87-celery-worker-crash`

### Development Cycle

1. **Create a feature branch:**
```bash
git checkout main
git pull origin main
git checkout -b feature/AAET-XX-description
```

2. **Make your changes:**
   - Write code following our [Code Standards](#code-standards)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks:**
```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run tests
pytest

# Check coverage
pytest --cov=app --cov-report=html
```

4. **Commit your changes:**
```bash
git add .
git commit -m "feat(AAET-XX): Add feature description"
```

5. **Push and create PR:**
```bash
git push origin feature/AAET-XX-description
# Create pull request on GitHub
```

## Code Standards

### Python Style Guide

We follow **PEP 8** with some modifications enforced by **Ruff**:

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Sorted and grouped (isort)

### Code Formatting

All code is automatically formatted using **Ruff**:

```bash
# Format code
ruff format .

# Check formatting
ruff format --check .
```

### Linting

We use **Ruff** for linting:

```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Type Hints

- **Required** for all public functions and methods
- Use `typing` module for complex types
- Run `mypy` for type checking:

```bash
mypy app/ services/ workers/
```

### Docstrings

All public functions, classes, and modules must have docstrings:

```python
def parse_repository(repo_path: Path, language: str) -> ParseResult:
    """Parse a repository and extract code graph.

    Args:
        repo_path: Path to the repository
        language: Programming language (python, typescript, etc.)

    Returns:
        ParseResult containing nodes, edges, and metadata

    Raises:
        RepositoryParseError: If parsing fails
        TenantValidationError: If tenant context is invalid
    """
    pass
```

### Import Organization

Imports should be organized in this order:
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from pathlib import Path
from typing import Any

# Third-party
import pytest
from fastapi import FastAPI
from sqlalchemy import select

# Local
from app.models.tenant import Tenant
from app.core.database import get_db
```

## Testing Guidelines

### Test Structure

Tests are organized by type:
- `tests/` - Unit and integration tests
- `tests/services/` - Service layer tests
- `tests/workers/` - Celery task tests
- `tests/api/` - API endpoint tests

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_fast_function():
    """Unit test - no external dependencies."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_operation(db_session):
    """Integration test - requires database."""
    pass

@pytest.mark.slow
def test_large_dataset():
    """Slow test - may take >5 seconds."""
    pass
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# With coverage
pytest --cov=app --cov-report=html

# Specific file
pytest tests/test_logging.py -v

# Specific test
pytest tests/test_logging.py::test_structured_logging -v
```

### Test Fixtures

Use provided fixtures for common test scenarios:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant(db_session, factories):
    """Example using database and factory fixtures."""
    # Create test data
    tenant = await factories.create_tenant(name="Test Corp")

    # Assertions
    assert tenant.id is not None
    assert tenant.name == "Test Corp"
```

Available fixtures:
- `db_session` - Async database session with automatic rollback
- `redis_client` - Redis client with automatic cleanup
- `client` - FastAPI TestClient
- `factories` - Test data factories
- `sample_tenant_data` - Sample tenant data dict
- `sample_repository_data` - Sample repository data dict

### Writing Good Tests

1. **Test one thing at a time**
2. **Use descriptive test names**
3. **Follow AAA pattern** (Arrange, Act, Assert)
4. **Clean up resources** (use fixtures)
5. **Mock external dependencies**

Example:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_creation_with_valid_data(db_session, factories):
    """Test that repository is created successfully with valid data."""
    # Arrange
    tenant = await factories.create_tenant()
    repo_data = {
        "name": "test-repo",
        "git_url": "https://github.com/test/repo",
        "language": "python"
    }

    # Act
    repository = await factories.create_repository(tenant=tenant, **repo_data)

    # Assert
    assert repository.id is not None
    assert repository.name == "test-repo"
    assert repository.tenant_id == tenant.id
```

## Git Workflow

### Commit Messages

Follow **Conventional Commits** specification:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(AAET-21): Add developer documentation
fix(AAET-19): Fix async test fixtures
docs: Update README with new setup instructions
test(parser): Add tests for TypeScript parser
refactor(storage): Simplify PostgreSQL connection handling
```

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch (if used)
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Urgent production fixes

### Keeping Your Branch Updated

```bash
# Update main
git checkout main
git pull origin main

# Rebase your feature branch
git checkout feature/AAET-XX-description
git rebase main

# Force push (if already pushed)
git push origin feature/AAET-XX-description --force-with-lease
```

## Pull Request Process

### Before Creating a PR

1. ✅ All tests pass locally
2. ✅ Code is formatted and linted
3. ✅ Documentation is updated
4. ✅ Commit messages follow convention
5. ✅ Branch is up to date with main

### PR Title

Use the same format as commit messages:
```
feat(AAET-21): Add developer documentation
```

### PR Description Template

```markdown
## Description
Brief description of changes

## JIRA Ticket
AAET-XX

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings
```

### PR Size Guidelines

- **Small**: < 200 lines changed (preferred)
- **Medium**: 200-500 lines changed
- **Large**: > 500 lines changed (consider splitting)

Large PRs should be split into smaller, logical commits.

## Code Review Guidelines

### For Authors

1. **Self-review** your code before requesting review
2. **Provide context** in PR description
3. **Respond promptly** to review comments
4. **Be open** to feedback and suggestions
5. **Update tests** based on review feedback

### For Reviewers

1. **Be respectful** and constructive
2. **Focus on** logic, design, and maintainability
3. **Ask questions** rather than making demands
4. **Approve** when satisfied or request changes
5. **Test locally** for complex changes

### Review Checklist

- [ ] Code follows project standards
- [ ] Tests are comprehensive
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] Logging is adequate

## Common Development Tasks

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/schemas/`
2. Add endpoint in `app/api/v1/`
3. Add tests in `tests/api/`
4. Update API documentation

### Adding a New Database Model

1. Create model in `app/models/`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration file
4. Test migration: `alembic upgrade head`
5. Add factory in `tests/factories.py`
6. Add tests

### Adding a New Celery Task

1. Define task in `workers/tasks/`
2. Add retry logic and error handling
3. Add tests in `tests/workers/`
4. Update worker documentation

### Debugging Tips

**Database Issues:**
```bash
# Check current migration
alembic current

# View migration history
alembic history --verbose

# Reset database (WARNING: destroys data)
make db-reset
```

**Redis Issues:**
```bash
# Connect to Redis CLI
docker exec -it aelus-redis redis-cli

# Check keys
KEYS *

# Flush database
FLUSHDB
```

**Celery Issues:**
```bash
# Check worker status
celery -A workers.celery_app inspect active

# Purge all tasks
celery -A workers.celery_app purge

# Check task status
celery -A workers.celery_app inspect stats
```

## Getting Help

- **Documentation**: Check `docs/` directory
- **JIRA**: Create a ticket for bugs or feature requests
- **Code Comments**: Look for inline documentation
- **Tests**: Check test files for usage examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
