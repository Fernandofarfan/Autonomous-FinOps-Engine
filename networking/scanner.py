from typing import List
from google.cloud import compute_v1
import os
from foundation.models import IdleResource
from foundation.exceptions import ScannerError
from foundation.logger import get_logger

logger = get_logger(__name__)

class NetworkScanner:
    """Escanea recursos de Networking (ej. Direcciones IP externas)."""
    
    def __init__(self, project_id: str, region: str) -> None:
        self.project_id = project_id
        self.region = region
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        if not self.demo_mode:
            try:
                # Autenticación automática vía Application Default Credentials (ADC)
                self.address_client = compute_v1.AddressesClient()
                logger.info(f"NetworkScanner inicializado -> Project: {project_id}, Region: {region}")
            except Exception as e:
                logger.error(f"Fallo al inicializar NetworkScanner: {e}")
                raise ScannerError(f"Error de inicialización en NetworkScanner: {e}")
        else:
            logger.info(f"NetworkScanner inicializado en MODO DEMO -> Project: {project_id}, Region: {region}")

    def scan_unused_ips(self) -> List[IdleResource]:
        """Detecta direcciones IP externas reservadas que no están en uso."""
        logger.info(f"Escaneando IPs estáticas sin uso en región {self.region}...")
        if self.demo_mode:
            return [
                IdleResource(resource_id="demo-unused-ip-1", resource_type="google_compute_address", project_id=self.project_id, zone_or_region=self.region, reason="Unused external static IP"),
                IdleResource(resource_id="demo-unused-ip-2", resource_type="google_compute_address", project_id=self.project_id, zone_or_region=self.region, reason="Unused external static IP (Legacy)")
            ]
        idle_ips: List[IdleResource] = []
        try:
            request = compute_v1.ListAddressesRequest(project=self.project_id, region=self.region)
            addresses = self.address_client.list(request=request)
            
            for address in addresses:
                # 'RESERVED' significa que está creada pero no asignada a ningún recurso.
                # 'IN_USE' es cuando está asignada.
                if address.status == "RESERVED":
                    logger.info(f"IP ociosa detectada: {address.name}")
                    idle_ips.append(
                        IdleResource(
                            resource_id=address.name,
                            resource_type="google_compute_address",
                            project_id=self.project_id,
                            zone_or_region=self.region,
                            reason="Unused external static IP"
                        )
                    )
            return idle_ips
        except Exception as e:
            logger.error(f"Error al listar IPs: {e}")
            raise ScannerError(f"Error escaneando IPs: {e}")
