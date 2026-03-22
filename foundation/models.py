from dataclasses import dataclass

@dataclass
class IdleResource:
    """Modelo de dominio para un recurso ocioso en GCP."""
    resource_id: str
    resource_type: str
    project_id: str
    zone_or_region: str
    reason: str
