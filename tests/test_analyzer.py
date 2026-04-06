"""Tests para ResourceAnalyzer — consolidación y generación de reportes."""

import pytest
from foundation.analyzer import ResourceAnalyzer
from foundation.models import IdleResource


class TestResourceAnalyzer:

    def test_starts_empty(self):
        """El analizador comienza sin recursos."""
        analyzer = ResourceAnalyzer()
        assert len(analyzer.idle_resources) == 0

    def test_add_resources_accumulates(self, all_resources):
        """add_resources() acumula correctamente múltiples llamadas."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources(all_resources[:2])
        analyzer.add_resources(all_resources[2:])
        assert len(analyzer.idle_resources) == 4

    def test_generate_report_returns_list(self, all_resources):
        """generate_report() retorna una lista de IdleResource."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources(all_resources)
        report = analyzer.generate_report()
        assert isinstance(report, list)
        assert all(isinstance(r, IdleResource) for r in report)

    def test_cost_enrichment_applied(self):
        """Recursos con costo 0.0 reciben costo estimado por tipo."""
        analyzer = ResourceAnalyzer()
        r = IdleResource(
            resource_id="no-cost-disk",
            resource_type="google_compute_disk",
            project_id="proj",
            zone_or_region="us-central1-a",
            reason="Test",
            estimated_monthly_cost_usd=0.0,  # Sin costo
        )
        analyzer.add_resources([r])
        report = analyzer.generate_report()
        # El analizador debería enriquecer el costo
        assert report[0].estimated_monthly_cost_usd > 0.0

    def test_existing_cost_not_overridden(self, sample_disk):
        """Recursos con costo ya definido no son anulados por el enriquecimiento."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources([sample_disk])  # sample_disk.cost = 4.00
        report = analyzer.generate_report()
        assert report[0].estimated_monthly_cost_usd == 4.00

    def test_generate_summary_structure(self, all_resources):
        """generate_summary() retorna todas las claves esperadas."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources(all_resources)
        summary = analyzer.generate_summary()

        assert "total_idle_resources" in summary
        assert "total_estimated_monthly_cost_usd" in summary
        assert "breakdown_by_type" in summary
        assert "breakdown_by_project" in summary

    def test_generate_summary_total_count(self, all_resources):
        """El total en summary coincide con resources agregados."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources(all_resources)
        summary = analyzer.generate_summary()
        assert summary["total_idle_resources"] == len(all_resources)

    def test_generate_summary_total_cost(self, all_resources):
        """El costo total en summary es la suma de todos los recursos enriquecidos."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources(all_resources)
        summary = analyzer.generate_summary()
        assert summary["total_estimated_monthly_cost_usd"] > 0.0

    def test_summary_breakdown_by_type(self, sample_disk, sample_ip):
        """El breakdown por tipo cuenta correctamente."""
        analyzer = ResourceAnalyzer()
        analyzer.add_resources([sample_disk, sample_ip])
        summary = analyzer.generate_summary()
        bt = summary["breakdown_by_type"]
        assert "google_compute_disk" in bt
        assert "google_compute_address" in bt
        assert bt["google_compute_disk"]["count"] == 1
        assert bt["google_compute_address"]["count"] == 1

    def test_empty_analyzer_generates_empty_report(self):
        """Un analizador vacío genera reporte y summary vacíos."""
        analyzer = ResourceAnalyzer()
        assert analyzer.generate_report() == []
        summary = analyzer.generate_summary()
        assert summary["total_idle_resources"] == 0
        assert summary["total_estimated_monthly_cost_usd"] == 0.0
