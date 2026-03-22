from typing import List
from google.cloud import compute_v1
import os
from foundation.models import IdleResource
from foundation.exceptions import ScannerError
from foundation.logger import get_logger

logger = get_logger(__name__)

class ComputeScanner:
    """Escanea recursos de Compute Engine (ej. Discos Persistentes)."""
    
    def __init__(self, project_id: str, zone: str) -> None:
        self.project_id = project_id
        self.zone = zone
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        if not self.demo_mode:
            try:
                # Autenticación automática vía Application Default Credentials (ADC)
                self.disk_client = compute_v1.DisksClient()
                logger.info(f"ComputeScanner inicializado -> Project: {project_id}, Zone: {zone}")
            except Exception as e:
                logger.error(f"Fallo al inicializar ComputeScanner: {e}")
                raise ScannerError(f"Error de inicialización en ComputeScanner: {e}")
        else:
            logger.info(f"ComputeScanner inicializado en MODO DEMO -> Project: {project_id}, Zone: {zone}")

    def scan_unattached_disks(self) -> List[IdleResource]:
        """Detecta discos persistentes que no están adjuntados a ninguna VM."""
        logger.info(f"Escaneando discos sin adjuntar en zona {self.zone}...")
        if self.demo_mode:
            return [
                IdleResource(resource_id="demo-unattached-disk-1", resource_type="google_compute_disk", project_id=self.project_id, zone_or_region=self.zone, reason="Unattached demo disk"),
                IdleResource(resource_id="demo-unattached-disk-2", resource_type="google_compute_disk", project_id=self.project_id, zone_or_region=self.zone, reason="Old backup demo disk")
            ]
        idle_disks: List[IdleResource] = []
        try:
            request = compute_v1.ListDisksRequest(project=self.project_id, zone=self.zone)
            disks = self.disk_client.list(request=request)
            
            for disk in disks:
                # Si 'users' está vacío, el disco no está en uso por ninguna instancia
                if not disk.users:
                    logger.info(f"Disco ocioso detectado: {disk.name}")
                    idle_disks.append(
                        IdleResource(
                            resource_id=disk.name,
                            resource_type="google_compute_disk",
                            project_id=self.project_id,
                            zone_or_region=self.zone,
                            reason="Unattached persistent disk"
                        )
                    )
            return idle_disks
        except Exception as e:
            logger.error(f"Error al listar discos de Compute Engine: {e}")
            raise ScannerError(f"Error escaneando discos: {e}")
