"""Tests para TerraformGenerator — generación de archivos .tf con Jinja2."""

import os
import tempfile
import pytest
from remediation.generator import TerraformGenerator
from foundation.models import IdleResource

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "remediation", "templates")


@pytest.fixture
def generator(tmp_path) -> TerraformGenerator:
    """Instancia del generador con directorio temporal de salida."""
    return TerraformGenerator(template_dir=TEMPLATES_DIR, output_dir=str(tmp_path))


@pytest.fixture
def mixed_resources() -> list:
    return [
        IdleResource(
            resource_id="test-disk-001",
            resource_type="google_compute_disk",
            project_id="test-project",
            zone_or_region="us-central1-a",
            reason="Unattached disk",
            estimated_monthly_cost_usd=4.00,
        ),
        IdleResource(
            resource_id="test-ip-001",
            resource_type="google_compute_address",
            project_id="test-project",
            zone_or_region="us-central1",
            reason="Unused IP",
            estimated_monthly_cost_usd=7.20,
        ),
    ]


class TestTerraformGenerator:

    def test_creates_output_directory(self):
        """El generador crea el directorio de salida si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "nonexistent", "output")
            gen = TerraformGenerator(template_dir=TEMPLATES_DIR, output_dir=out)
            assert os.path.exists(out)

    def test_generates_three_tf_files(self, generator, mixed_resources, tmp_path):
        """Se generan main.tf, variables.tf y outputs.tf."""
        generator.generate(mixed_resources)
        assert (tmp_path / "main.tf").exists()
        assert (tmp_path / "variables.tf").exists()
        assert (tmp_path / "outputs.tf").exists()

    def test_skips_generation_on_empty_list(self, generator, tmp_path):
        """No genera archivos si no hay recursos ociosos."""
        generator.generate([])
        assert not (tmp_path / "main.tf").exists()

    def test_main_tf_contains_required_providers(self, generator, mixed_resources, tmp_path):
        """main.tf debe contener el bloque terraform { required_providers }."""
        generator.generate(mixed_resources)
        content = (tmp_path / "main.tf").read_text(encoding="utf-8")
        assert "required_providers" in content
        assert "hashicorp/google" in content

    def test_main_tf_contains_disk_resource(self, generator, mixed_resources, tmp_path):
        """main.tf debe incluir el bloque resource para el disco."""
        generator.generate(mixed_resources)
        content = (tmp_path / "main.tf").read_text(encoding="utf-8")
        assert "google_compute_disk" in content
        assert "test-disk-001" in content

    def test_main_tf_contains_import_block(self, generator, mixed_resources, tmp_path):
        """main.tf debe contener bloques import { } para Terraform 1.5+."""
        generator.generate(mixed_resources)
        content = (tmp_path / "main.tf").read_text(encoding="utf-8")
        assert "import {" in content

    def test_main_tf_contains_ip_resource(self, generator, mixed_resources, tmp_path):
        """main.tf debe incluir el bloque resource para la IP."""
        generator.generate(mixed_resources)
        content = (tmp_path / "main.tf").read_text(encoding="utf-8")
        assert "google_compute_address" in content
        assert "test-ip-001" in content

    def test_variables_tf_has_project_variable(self, generator, mixed_resources, tmp_path):
        """variables.tf debe definir la variable project_id."""
        generator.generate(mixed_resources)
        content = (tmp_path / "variables.tf").read_text(encoding="utf-8")
        assert 'variable "project_id"' in content

    def test_outputs_tf_has_total_output(self, generator, mixed_resources, tmp_path):
        """outputs.tf debe incluir el output de total de recursos."""
        generator.generate(mixed_resources)
        content = (tmp_path / "outputs.tf").read_text(encoding="utf-8")
        assert "total_idle_resources" in content

    def test_outputs_tf_has_cost_output(self, generator, mixed_resources, tmp_path):
        """outputs.tf debe incluir el output de costo mensual total."""
        generator.generate(mixed_resources)
        content = (tmp_path / "outputs.tf").read_text(encoding="utf-8")
        assert "total_estimated_monthly_waste_usd" in content

    def test_resource_ids_with_hyphens_are_sanitized(self, generator, tmp_path):
        """IDs con guiones se convierten a guiones bajos en los nombres de recursos."""
        r = IdleResource(
            resource_id="my-disk-with-hyphens",
            resource_type="google_compute_disk",
            project_id="proj",
            zone_or_region="us-central1-a",
            reason="Test",
            estimated_monthly_cost_usd=2.0,
        )
        generator.generate([r])
        content = (tmp_path / "main.tf").read_text(encoding="utf-8")
        assert "my_disk_with_hyphens" in content
