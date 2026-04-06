from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class EngineConfig(BaseSettings):
    """
    Configuración centralizada del Autonomous FinOps Engine.
    Todos los valores se leen desde variables de entorno o un archivo .env.
    """

    # --- GCP Identity ---
    gcp_project_id: str = Field(
        default="my-finops-project",
        alias="GCP_PROJECT_ID",
        description="ID del proyecto GCP a auditar."
    )
    gcp_zone: Optional[str] = Field(
        default=None,
        alias="GCP_ZONE",
        description="Zona específica a escanear. Si es None, se escanean todas las zonas del proyecto."
    )
    gcp_region: Optional[str] = Field(
        default=None,
        alias="GCP_REGION",
        description="Región específica a escanear. Si es None, se escanean todas las regiones."
    )

    # --- Modos de Ejecución ---
    demo_mode: bool = Field(
        default=False,
        alias="DEMO_MODE",
        description="Si True, retorna datos ficticios sin conectarse a GCP."
    )
    auto_apply: bool = Field(
        default=False,
        alias="AUTO_APPLY",
        description="Si True, ejecuta `terraform apply -auto-approve` automáticamente. ¡PELIGROSO!"
    )

    # --- Thresholds de detección ---
    max_disk_age_days: int = Field(
        default=30,
        alias="MAX_DISK_AGE_DAYS",
        description="Días sin uso para considerar un disco como ocioso."
    )
    max_snapshot_age_days: int = Field(
        default=60,
        alias="MAX_SNAPSHOT_AGE_DAYS",
        description="Edad en días para considerar un snapshot como obsoleto."
    )
    max_stopped_instance_days: int = Field(
        default=14,
        alias="MAX_STOPPED_INSTANCE_DAYS",
        description="Días en estado TERMINATED para marcar una VM como candidata a remediación."
    )

    # --- Costos estimados por tipo de recurso (USD/mes) ---
    cost_per_unattached_disk_gb_month: float = Field(
        default=0.04,
        description="Costo estimado por GB/mes de disco desconectado (HDD)."
    )
    cost_per_unused_ip_month: float = Field(
        default=7.20,
        description="Costo mensual fijo de una IP estática no utilizada en GCP."
    )

    model_config = {"env_file": ".env", "populate_by_name": True, "extra": "ignore"}


# Instancia global — importable desde cualquier módulo
config = EngineConfig()
