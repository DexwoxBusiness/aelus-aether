import uuid

import pytest

from app.utils.namespace import NamespaceComponents, parse_namespace, validate_namespace_for_tenant


def test_parse_namespace_valid_code():
    tenant_id = uuid.uuid4()
    ns = f"{tenant_id}:org-1/repo_1:main:code"
    comp = parse_namespace(ns)
    assert isinstance(comp, NamespaceComponents)
    assert comp.tenant_id == tenant_id
    assert comp.org == "org-1"
    assert comp.repo == "repo_1"
    assert comp.branch == "main"
    assert comp.type == "code"


def test_parse_namespace_valid_docs():
    tenant_id = uuid.uuid4()
    ns = f"{tenant_id}:org/repo:feature/x-1:docs"
    comp = parse_namespace(ns)
    assert comp.type == "docs"


def test_parse_namespace_invalid_format():
    with pytest.raises(ValueError):
        parse_namespace("bad-format")


def test_parse_namespace_invalid_type():
    tenant_id = uuid.uuid4()
    with pytest.raises(ValueError):
        parse_namespace(f"{tenant_id}:org/repo:main:invalid")


def test_validate_namespace_tenant_match():
    tenant_id = uuid.uuid4()
    ns = f"{tenant_id}:org/repo:dev:stories"
    comp = validate_namespace_for_tenant(ns, tenant_id)
    assert comp.tenant_id == tenant_id


def test_validate_namespace_tenant_mismatch():
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    ns = f"{t1}:org/repo:dev:code"
    with pytest.raises(PermissionError):
        validate_namespace_for_tenant(ns, t2)
