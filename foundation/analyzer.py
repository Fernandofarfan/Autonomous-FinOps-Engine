from typing import List, Dict, Any
from foundation.models import IdleResource
from foundation.logger import get_logger

logger = get_logger(__name__)

# Costos mensuales estimados por tipo de recurso (USD)
_COST_MAP: Dict[str, float] = {
    "google_compute_disk": 4.00,       # ~100GB HDD desconectado
    "google_compute_address": 7.20,    # IP estática sin usar
    "google_compute_instance": 50.00,  # VM pequeña detenida (n1-standard-1)
    "google_compute_snapshot": 2.50,   # Snapshot ~100GB
    "google_storage_bucket": 3.00,     # Bucket vacío/inactivo
}


class ResourceAnalyzer:
    """
    Consolida los hallazgos de todos los escáneres, calcula costos estimados
    y genera reportes estructurados. Opera directamente con objetos de dominio
    (List[IdleResource]) sin serialización JSON innecesaria.
    """

    def __init__(self) -> None:
        self.idle_resources: List[IdleResource] = []

    def add_resources(self, resources: List[IdleResource]) -> None:
        """Agrega recursos al pool de análisis."""
        self.idle_resources.extend(resources)
        logger.info(
            f"Agregados {len(resources)} recursos para análisis "
            f"(Total acumulado: {len(self.idle_resources)})."
        )

    def generate_report(self) -> List[IdleResource]:
        """
        Retorna la lista consolidada de recursos ociosos detectados,
        enriquecida con costos estimados donde no se hayan asignado aún.
        """
        logger.info("Generando reporte de recursos ociosos...")
        enriched: List[IdleResource] = []
        for res in self.idle_resources:
            if res.estimated_monthly_cost_usd == 0.0:
                estimated = _COST_MAP.get(res.resource_type, 1.0)
                enriched.append(res.model_copy(update={"estimated_monthly_cost_usd": estimated}))
            else:
                enriched.append(res)
        return enriched

    def generate_summary(self) -> Dict[str, Any]:
        """
        Genera un diccionario con estadísticas de alto nivel del hallazgo:
        - Total de recursos ociosos.
        - Costo mensual estimado total.
        - Breakdown por tipo de recurso.
        - Breakdown por proyecto.
        """
        resources = self.generate_report()
        total_cost = sum(r.estimated_monthly_cost_usd for r in resources)

        by_type: Dict[str, Dict[str, Any]] = {}
        for r in resources:
            entry = by_type.setdefault(r.resource_type, {"count": 0, "cost_usd": 0.0})
            entry["count"] += 1
            entry["cost_usd"] += r.estimated_monthly_cost_usd

        by_project: Dict[str, int] = {}
        for r in resources:
            by_project[r.project_id] = by_project.get(r.project_id, 0) + 1

        summary = {
            "total_idle_resources": len(resources),
            "total_estimated_monthly_cost_usd": round(total_cost, 2),
            "breakdown_by_type": by_type,
            "breakdown_by_project": by_project,
        }

        logger.info(
            f"Resumen financiero: {len(resources)} recursos ociosos | "
            f"Costo total estimado: ${total_cost:.2f}/mes"
        )
        return summary
