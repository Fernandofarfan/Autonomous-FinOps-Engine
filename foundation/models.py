from pydantic import BaseModel, Field
from typing import Optional, Dict


class IdleResource(BaseModel):
    """Modelo de dominio para un recurso ocioso en GCP, validado con Pydantic."""
    
    resource_id: str = Field(..., description="Identificador único del recurso en GCP.")
    resource_type: str = Field(..., description="Tipo de recurso Terraform (e.g. google_compute_disk).")
    project_id: str = Field(..., description="ID del proyecto GCP donde reside el recurso.")
    zone_or_region: str = Field(..., description="Zona o región donde reside el recurso.")
    reason: str = Field(..., description="Motivo por el cual se considera ocioso o desperdiciado.")
    
    # Campos enriquecidos opcionales
    estimated_monthly_cost_usd: float = Field(
        default=0.0,
        description="Costo mensual estimado en USD que genera este recurso."
    )
    age_days: Optional[int] = Field(
        default=None,
        description="Antigüedad del recurso en días desde su creación."
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels/etiquetas GCP asociadas al recurso para contexto."
    )
