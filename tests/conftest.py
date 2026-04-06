"""Fixtures compartidas para los tests del FinOps Engine."""

import pytest
from foundation.models import IdleResource


@pytest.fixture
def sample_disk() -> IdleResource:
    return IdleResource(
        resource_id="test-disk-001",
        resource_type="google_compute_disk",
        project_id="test-project",
        zone_or_region="us-central1-a",
        reason="Unattached persistent disk",
        estimated_monthly_cost_usd=4.00,
        age_days=45,
        labels={"env": "dev"},
    )


@pytest.fixture
def sample_ip() -> IdleResource:
    return IdleResource(
        resource_id="test-ip-001",
        resource_type="google_compute_address",
        project_id="test-project",
        zone_or_region="us-central1",
        reason="Unused external static IP",
        estimated_monthly_cost_usd=7.20,
    )


@pytest.fixture
def sample_instance() -> IdleResource:
    return IdleResource(
        resource_id="test-vm-001",
        resource_type="google_compute_instance",
        project_id="test-project",
        zone_or_region="us-east1-b",
        reason="VM TERMINATED hace 30 días",
        estimated_monthly_cost_usd=2.00,
        age_days=30,
    )


@pytest.fixture
def sample_snapshot() -> IdleResource:
    return IdleResource(
        resource_id="test-snap-001",
        resource_type="google_compute_snapshot",
        project_id="test-project",
        zone_or_region="global",
        reason="Snapshot obsoleto (90 días)",
        estimated_monthly_cost_usd=2.50,
        age_days=90,
    )


@pytest.fixture
def all_resources(sample_disk, sample_ip, sample_instance, sample_snapshot):
    return [sample_disk, sample_ip, sample_instance, sample_snapshot]
