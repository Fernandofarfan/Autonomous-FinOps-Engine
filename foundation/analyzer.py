import json
from typing import List
from foundation.models import IdleResource
from foundation.logger import get_logger

logger = get_logger(__name__)

class ResourceAnalyzer:
    """
    Recibe los datos de los escáneres y formatea un reporte JSON
    con los recursos ociosos detectados y el ID de los mismos.
    """
    
    def __init__(self) -> None:
        self.idle_resources: List[IdleResource] = []
        
    def add_resources(self, resources: List[IdleResource]) -> None:
        self.idle_resources.extend(resources)
        logger.info(f"Agregados {len(resources)} recursos para análisis (Total: {len(self.idle_resources)}).")
        
    def generate_report(self) -> str:
        """Genera un reporte JSON estructurado de los recursos despilfarrados."""
        logger.info("Generando reporte de recursos ociosos...")
        report_data = [
            {
                "id": res.resource_id,
                "type": res.resource_type,
                "project": res.project_id,
                "location": res.zone_or_region,
                "reason": res.reason
            }
            for res in self.idle_resources
        ]
        return json.dumps({"idle_resources": report_data}, indent=4)
