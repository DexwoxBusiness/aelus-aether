from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Concatenate, ParamSpec, Protocol

from sqlalchemy import select

from app.core.database import get_db
from app.models.tenant import Tenant
from app.utils.quota import quota_service
from workers.celery_app import celery_app


class CeleryTaskProto(Protocol):
    name: str
    request: Any


P = ParamSpec("P")


def typed_task(
    *dargs: Any, **dkwargs: Any
) -> Callable[
    [Callable[Concatenate[CeleryTaskProto, P], Awaitable[Any]]],
    Callable[Concatenate[CeleryTaskProto, P], Awaitable[Any]],
]:
    return celery_app.task(*dargs, **dkwargs)  # type: ignore[no-any-return]


@typed_task(bind=True)
async def snapshot_tenant_usage(self: CeleryTaskProto, tenant_id: str) -> dict[str, Any]:
    """Snapshot current Redis usage into tenants.settings.usage_snapshot."""
    usage = await quota_service.get_usage(tenant_id)

    # Persist into Postgres settings
    async for db in get_db():  # get_db is async generator
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"status": "not_found", "tenant_id": tenant_id}
        settings = tenant.settings or {}
        settings["usage_snapshot"] = {
            "at": datetime.now(UTC).isoformat(),
            **usage,
        }
        tenant.settings = settings
        await db.flush()
        await db.commit()
        return {"status": "ok", "tenant_id": tenant_id, "usage": usage}
    # Fallback return to satisfy type checker
    return {"status": "error", "tenant_id": tenant_id, "reason": "no-db-session"}


@typed_task(bind=True)
async def snapshot_all_tenants(self: CeleryTaskProto) -> dict[str, Any]:
    """Snapshot usage for all tenants."""
    count = 0
    async for db in get_db():
        result = await db.execute(select(Tenant.id))
        ids = [str(r[0]) for r in result.fetchall()]
        for tid in ids:
            # Use celery_app.send_task to avoid mypy issues with apply_async
            celery_app.send_task("workers.tasks.quota.snapshot_tenant_usage", args=[tid])
            count += 1
        return {"status": "queued", "tenants": count}
    # Fallback return to satisfy type checker
    return {"status": "queued", "tenants": 0}
