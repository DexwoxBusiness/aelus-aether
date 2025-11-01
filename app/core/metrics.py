from __future__ import annotations

from prometheus_client import Counter, Gauge

# Per-tenant quota-related metrics for billing (AAET-27)
api_calls_total = Counter(
    "tenant_api_calls_total",
    "Total API calls per tenant",
    labelnames=("tenant_id", "endpoint", "operation"),
)

vector_count_total = Counter(
    "tenant_vectors_total",
    "Total vectors created per tenant",
    labelnames=("tenant_id",),
)

storage_bytes_total = Gauge(
    "tenant_storage_bytes_total",
    "Current storage bytes used per tenant (point-in-time measurement)",
    labelnames=("tenant_id",),
)

embedding_tokens_total = Counter(
    "tenant_embedding_tokens_total",
    "Total embedding tokens consumed per tenant",
    labelnames=("tenant_id", "operation"),
)
