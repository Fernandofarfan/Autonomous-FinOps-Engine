"""Tests para los modelos de dominio Pydantic del FinOps Engine."""

import pytest
from pydantic import ValidationError
from foundation.models import IdleResource


class TestIdleResourceModel:

    def test_create_valid_resource(self, sample_disk):
        """Un recurso válido se crea sin errores."""
        assert sample_disk.resource_id == "test-disk-001"
        assert sample_disk.resource_type == "google_compute_disk"
        assert sample_disk.estimated_monthly_cost_usd == 4.00
        assert sample_disk.age_days == 45
        assert sample_disk.labels == {"env": "dev"}

    def test_defaults_are_applied(self):
        """Los campos opcionales tienen defaults correctos."""
        r = IdleResource(
            resource_id="minimal-resource",
            resource_type="google_compute_disk",
            project_id="proj",
            zone_or_region="us-central1-a",
            reason="Test reason",
        )
        assert r.estimated_monthly_cost_usd == 0.0
        assert r.age_days is None
        assert r.labels == {}

    def test_missing_required_field_raises_validation_error(self):
        """Faltar un campo requerido debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            IdleResource(
                resource_type="google_compute_disk",
                project_id="proj",
                zone_or_region="us-central1-a",
                reason="Test",
                # resource_id faltante
            )

    def test_model_dump_serializes_correctly(self, sample_disk):
        """model_dump() retorna un diccionario con los campos esperados."""
        data = sample_disk.model_dump()
        assert data["resource_id"] == "test-disk-001"
        assert data["estimated_monthly_cost_usd"] == 4.00
        assert isinstance(data["labels"], dict)

    def test_model_copy_with_update(self, sample_disk):
        """model_copy(update=...) genera una nueva instancia actualizada."""
        updated = sample_disk.model_copy(update={"estimated_monthly_cost_usd": 99.99})
        assert updated.estimated_monthly_cost_usd == 99.99
        assert sample_disk.estimated_monthly_cost_usd == 4.00  # Original sin cambios

    def test_negative_cost_is_accepted(self):
        """Pydantic no restringe valores negativos — documentar comportamiento esperado."""
        r = IdleResource(
            resource_id="r1",
            resource_type="google_compute_disk",
            project_id="p",
            zone_or_region="z",
            reason="test",
            estimated_monthly_cost_usd=-1.0,
        )
        assert r.estimated_monthly_cost_usd == -1.0

    def test_all_resource_types(self):
        """Se pueden crear recursos de todos los tipos soportados."""
        types = [
            "google_compute_disk",
            "google_compute_address",
            "google_compute_instance",
            "google_compute_snapshot",
            "google_storage_bucket",
            "google_compute_firewall",
        ]
        for rtype in types:
            r = IdleResource(
                resource_id=f"test-{rtype}",
                resource_type=rtype,
                project_id="proj",
                zone_or_region="us-central1",
                reason="test",
            )
            assert r.resource_type == rtype
