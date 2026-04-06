import os
from datetime import datetime, timezone
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from foundation.models import IdleResource
from foundation.exceptions import ScannerError
from foundation.logger import get_logger

logger = get_logger(__name__)

_BUCKET_COST_PER_GB_MONTH = 0.020  # Standard Storage en us/eu
_INACTIVE_BUCKET_BASE_COST = 3.0   # Estimado para bucket inactivo de ~150GB


class StorageScanner:
    """
    Escanea Cloud Storage en busca de desperdicios:
    - Buckets vacíos (sin objetos).
    - Buckets con sin actividad reciente según metadata de objetos.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

        if not self.demo_mode:
            try:
                from google.cloud import storage as gcs
                self.storage_client = gcs.Client(project=project_id)
                logger.info(f"StorageScanner inicializado → Project: {project_id}")
            except Exception as e:
                logger.error(f"Fallo al inicializar StorageScanner: {e}")
                raise ScannerError(f"Error de inicialización en StorageScanner: {e}")
        else:
            logger.info(f"StorageScanner inicializado en MODO DEMO → Project: {project_id}")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_empty_buckets(self) -> List[IdleResource]:
        """
        Detecta buckets de Cloud Storage que están completamente vacíos.
        Un bucket vacío en GCP no genera costo de almacenamiento, pero sí
        puede indicar recursos olvidados y configuraciones innecesarias.
        """
        logger.info("Escaneando buckets de Cloud Storage vacíos o inactivos...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-empty-bucket-logs",
                    resource_type="google_storage_bucket",
                    project_id=self.project_id,
                    zone_or_region="us-central1",
                    reason="Bucket de Cloud Storage completamente vacío (DEMO)",
                    estimated_monthly_cost_usd=0.0,
                ),
                IdleResource(
                    resource_id="demo-inactive-bucket-backups",
                    resource_type="google_storage_bucket",
                    project_id=self.project_id,
                    zone_or_region="us-east1",
                    reason="Bucket sin actividad en más de 90 días (DEMO)",
                    estimated_monthly_cost_usd=_INACTIVE_BUCKET_BASE_COST,
                    age_days=95,
                ),
            ]

        empty_buckets: List[IdleResource] = []
        _INACTIVITY_THRESHOLD_DAYS = 90

        try:
            buckets = list(self.storage_client.list_buckets(project=self.project_id))
            logger.info(f"Total de buckets encontrados: {len(buckets)}")

            for bucket in buckets:
                blobs = list(bucket.list_blobs(max_results=1))
                location = (bucket.location or "unknown").lower()

                if not blobs:
                    logger.info(f"Bucket vacío detectado: {bucket.name}")
                    empty_buckets.append(
                        IdleResource(
                            resource_id=bucket.name,
                            resource_type="google_storage_bucket",
                            project_id=self.project_id,
                            zone_or_region=location,
                            reason="Bucket de Cloud Storage completamente vacío",
                            estimated_monthly_cost_usd=0.0,
                            labels=dict(bucket.labels or {}),
                        )
                    )
                    continue

                # Verificar última actividad usando el blob más reciente
                try:
                    latest_blob = max(
                        bucket.list_blobs(),
                        key=lambda b: b.updated or datetime.min.replace(tzinfo=timezone.utc),
                        default=None,
                    )
                    if latest_blob and latest_blob.updated:
                        age_days = (datetime.now(timezone.utc) - latest_blob.updated).days
                        if age_days >= _INACTIVITY_THRESHOLD_DAYS:
                            logger.info(f"Bucket inactivo: {bucket.name} (último acceso: {age_days}d)")
                            empty_buckets.append(
                                IdleResource(
                                    resource_id=bucket.name,
                                    resource_type="google_storage_bucket",
                                    project_id=self.project_id,
                                    zone_or_region=location,
                                    reason=f"Bucket sin actividad de escritura en {age_days} días",
                                    estimated_monthly_cost_usd=_INACTIVE_BUCKET_BASE_COST,
                                    age_days=age_days,
                                    labels=dict(bucket.labels or {}),
                                )
                            )
                except Exception as inner_e:
                    logger.debug(f"No se pudo verificar actividad del bucket {bucket.name}: {inner_e}")

        except Exception as e:
            logger.error(f"Error escaneando buckets de Cloud Storage: {e}")
            raise ScannerError(f"Error escaneando Storage: {e}")

        logger.info(f"Buckets vacíos/inactivos detectados: {len(empty_buckets)}")
        return empty_buckets
