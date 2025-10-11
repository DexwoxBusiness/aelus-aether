"""Repository management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryResponse

router = APIRouter()


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """
    Create a new repository.
    
    Registers a repository for ingestion and tracking.
    """
    # Check if repository already exists for this tenant
    result = await db.execute(
        select(Repository).where(
            Repository.tenant_id == repo_data.tenant_id,
            Repository.name == repo_data.name,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{repo_data.name}' already exists for this tenant",
        )
    
    # Create repository
    repository = Repository(
        tenant_id=repo_data.tenant_id,
        name=repo_data.name,
        git_url=repo_data.git_url,
        branch=repo_data.branch or "main",
        repo_type=repo_data.repo_type,
        framework=repo_data.framework,
        language=repo_data.language,
        metadata=repo_data.metadata or {},
    )
    
    db.add(repository)
    await db.flush()
    await db.refresh(repository)
    
    return repository


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Get repository by ID."""
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    
    return repository


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
    tenant_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Repository]:
    """List repositories, optionally filtered by tenant."""
    query = select(Repository)
    
    if tenant_id:
        query = query.where(Repository.tenant_id == tenant_id)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())
