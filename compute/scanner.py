import os
from datetime import datetime, timezone
from typing import List, Optional

from google.cloud import compute_v1
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from foundation.models import IdleResource
from foundation.exceptions import ScannerError
from foundation.logger import get_logger

logger = get_logger(__name__)

# Costo estimado por GB/mes de disco persistente HDD en GCP ($0.04/GB)
_DISK_COST_PER_GB = 0.04
# Costo estimado por snapshot GB/mes ($0.026/GB)
_SNAPSHOT_COST_PER_GB = 0.026
# Costo estimado base de una instancia detenida (solo disco de arranque ~50GB)
_STOPPED_INSTANCE_BASE_COST = 2.0


def _parse_age_days(creation_timestamp: str) -> Optional[int]:
    """Calcula la antigüedad en días desde el timestamp de creación de GCP."""
    try:
        created_at = datetime.fromisoformat(creation_timestamp.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created_at).days
    except Exception:
        return None


class ComputeScanner:
    """
    Escanea recursos de Compute Engine en busca de desperdicios:
    - Discos persistentes desconectados.
    - Instancias de VM en estado TERMINATED por muchos días.
    - Snapshots obsoletos.
    Soporta escaneo multi-zona y retries automáticos ante errores de API.
    """

    def __init__(self, project_id: str, zone: Optional[str] = None) -> None:
        self.project_id = project_id
        self.zone = zone
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

        if not self.demo_mode:
            try:
                self.disk_client = compute_v1.DisksClient()
                self.instance_client = compute_v1.InstancesClient()
                self.snapshot_client = compute_v1.SnapshotsClient()
                self.zone_client = compute_v1.ZonesClient()
                logger.info(
                    f"ComputeScanner inicializado → Project: {project_id}, "
                    f"Zone: {zone or 'TODAS (multi-zona)'}"
                )
            except Exception as e:
                logger.error(f"Fallo al inicializar ComputeScanner: {e}")
                raise ScannerError(f"Error de inicialización en ComputeScanner: {e}")
        else:
            logger.info(f"ComputeScanner inicializado en MODO DEMO → Project: {project_id}")

    def _get_all_zones(self) -> List[str]:
        """Retorna la lista de todas las zonas habilitadas en el proyecto."""
        try:
            request = compute_v1.ListZonesRequest(project=self.project_id)
            zones = self.zone_client.list(request=request)
            return [z.name for z in zones]
        except Exception as e:
            logger.warning(f"No se pudieron listar todas las zonas: {e}. Usando zona por defecto.")
            return [self.zone or "us-central1-a"]

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_unattached_disks(self) -> List[IdleResource]:
        """
        Detecta discos persistentes no adjuntados a ninguna VM.
        Si no se especificó zona, itera sobre TODAS las zonas del proyecto.
        """
        logger.info("Escaneando discos desconectados...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-unattached-disk-1",
                    resource_type="google_compute_disk",
                    project_id=self.project_id,
                    zone_or_region="us-central1-a",
                    reason="Unattached persistent disk (DEMO)",
                    estimated_monthly_cost_usd=4.00,
                    age_days=45,
                ),
                IdleResource(
                    resource_id="demo-unattached-disk-2",
                    resource_type="google_compute_disk",
                    project_id=self.project_id,
                    zone_or_region="us-central1-a",
                    reason="Old backup disk, never re-attached (DEMO)",
                    estimated_monthly_cost_usd=8.00,
                    age_days=120,
                ),
            ]

        zones = [self.zone] if self.zone else self._get_all_zones()
        idle_disks: List[IdleResource] = []

        for zone in zones:
            try:
                request = compute_v1.ListDisksRequest(project=self.project_id, zone=zone)
                for disk in self.disk_client.list(request=request):
                    if not disk.users:
                        age = _parse_age_days(disk.creation_timestamp)
                        size_gb = disk.size_gb or 50
                        cost = round(size_gb * _DISK_COST_PER_GB, 2)
                        logger.info(f"Disco ocioso detectado: {disk.name} (zona: {zone})")
                        idle_disks.append(
                            IdleResource(
                                resource_id=disk.name,
                                resource_type="google_compute_disk",
                                project_id=self.project_id,
                                zone_or_region=zone,
                                reason=f"Unattached persistent disk ({size_gb}GB)",
                                estimated_monthly_cost_usd=cost,
                                age_days=age,
                                labels=dict(disk.labels or {}),
                            )
                        )
            except Exception as e:
                logger.warning(f"Error escaneando discos en zona {zone}: {e}")

        logger.info(f"Discos desconectados detectados: {len(idle_disks)}")
        return idle_disks

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_stopped_instances(self) -> List[IdleResource]:
        """
        Detecta VMs en estado TERMINATED por más días de lo configurado en
        MAX_STOPPED_INSTANCE_DAYS. Aunque no corra, sigue generando costos
        de disco y de IP si tienen una asignada.
        """
        _max_stopped = int(os.getenv("MAX_STOPPED_INSTANCE_DAYS", "14"))
        logger.info(f"Escaneando VMs detenidas por más de {_max_stopped} días...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-stopped-vm-1",
                    resource_type="google_compute_instance",
                    project_id=self.project_id,
                    zone_or_region="us-east1-b",
                    reason=f"VM detenida (TERMINATED) hace más de {_max_stopped} días (DEMO)",
                    estimated_monthly_cost_usd=_STOPPED_INSTANCE_BASE_COST,
                    age_days=30,
                ),
            ]

        zones = [self.zone] if self.zone else self._get_all_zones()
        stopped: List[IdleResource] = []

        for zone in zones:
            try:
                request = compute_v1.ListInstancesRequest(project=self.project_id, zone=zone)
                for instance in self.instance_client.list(request=request):
                    if instance.status != "TERMINATED":
                        continue
                    age = _parse_age_days(instance.creation_timestamp)
                    if age is not None and age >= _max_stopped:
                        logger.info(f"VM detenida detectada: {instance.name} ({age}d) en zona {zone}")
                        stopped.append(
                            IdleResource(
                                resource_id=instance.name,
                                resource_type="google_compute_instance",
                                project_id=self.project_id,
                                zone_or_region=zone,
                                reason=f"VM TERMINATED hace {age} días (umbral: {_max_stopped}d)",
                                estimated_monthly_cost_usd=_STOPPED_INSTANCE_BASE_COST,
                                age_days=age,
                                labels=dict(instance.labels or {}),
                            )
                        )
            except Exception as e:
                logger.warning(f"Error escaneando instancias en zona {zone}: {e}")

        logger.info(f"VMs detenidas detectadas: {len(stopped)}")
        return stopped

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_old_snapshots(self) -> List[IdleResource]:
        """
        Detecta snapshots de disco más antiguos que MAX_SNAPSHOT_AGE_DAYS.
        Los snapshots huérfanos acumulados son fuel silencioso de costos.
        """
        _max_snap = int(os.getenv("MAX_SNAPSHOT_AGE_DAYS", "60"))
        logger.info(f"Escaneando snapshots más antiguos de {_max_snap} días...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-old-snapshot-1",
                    resource_type="google_compute_snapshot",
                    project_id=self.project_id,
                    zone_or_region="global",
                    reason=f"Snapshot obsoleto (más de {_max_snap} días) (DEMO)",
                    estimated_monthly_cost_usd=2.50,
                    age_days=90,
                ),
            ]

        old_snapshots: List[IdleResource] = []
        try:
            request = compute_v1.ListSnapshotsRequest(project=self.project_id)
            for snap in self.snapshot_client.list(request=request):
                age = _parse_age_days(snap.creation_timestamp)
                if age is not None and age >= _max_snap:
                    size_gb = snap.storage_bytes // (1024 ** 3) if snap.storage_bytes else 10
                    cost = round(size_gb * _SNAPSHOT_COST_PER_GB, 2)
                    logger.info(f"Snapshot obsoleto: {snap.name} ({age}d)")
                    old_snapshots.append(
                        IdleResource(
                            resource_id=snap.name,
                            resource_type="google_compute_snapshot",
                            project_id=self.project_id,
                            zone_or_region="global",
                            reason=f"Snapshot con {age} días de antigüedad (umbral: {_max_snap}d)",
                            estimated_monthly_cost_usd=cost,
                            age_days=age,
                            labels=dict(snap.labels or {}),
                        )
                    )
        except Exception as e:
            logger.error(f"Error escaneando snapshots: {e}")
            raise ScannerError(f"Error escaneando snapshots: {e}")

        logger.info(f"Snapshots obsoletos detectados: {len(old_snapshots)}")
        return old_snapshots
