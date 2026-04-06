import os
from typing import List, Optional

from google.cloud import compute_v1
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from foundation.models import IdleResource
from foundation.exceptions import ScannerError
from foundation.logger import get_logger

logger = get_logger(__name__)

_IP_COST_PER_MONTH = 7.20  # USD por IP estática no utilizada


class NetworkScanner:
    """
    Escanea recursos de Networking en busca de desperdicios:
    - Direcciones IP externas estáticas sin usar.
    - Reglas de firewall demasiado permisivas o no utilizadas.
    Soporta escaneo multi-región y retries automáticos ante errores de API.
    """

    def __init__(self, project_id: str, region: Optional[str] = None) -> None:
        self.project_id = project_id
        self.region = region
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

        if not self.demo_mode:
            try:
                self.address_client = compute_v1.AddressesClient()
                self.region_client = compute_v1.RegionsClient()
                self.firewall_client = compute_v1.FirewallsClient()
                logger.info(
                    f"NetworkScanner inicializado → Project: {project_id}, "
                    f"Region: {region or 'TODAS (multi-región)'}"
                )
            except Exception as e:
                logger.error(f"Fallo al inicializar NetworkScanner: {e}")
                raise ScannerError(f"Error de inicialización en NetworkScanner: {e}")
        else:
            logger.info(f"NetworkScanner inicializado en MODO DEMO → Project: {project_id}")

    def _get_all_regions(self) -> List[str]:
        """Retorna la lista de todas las regiones habilitadas del proyecto."""
        try:
            request = compute_v1.ListRegionsRequest(project=self.project_id)
            return [r.name for r in self.region_client.list(request=request)]
        except Exception as e:
            logger.warning(f"No se pudieron listar todas las regiones: {e}. Usando región por defecto.")
            return [self.region or "us-central1"]

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_unused_ips(self) -> List[IdleResource]:
        """
        Detecta direcciones IP externas estáticas reservadas pero no asignadas.
        Si no se especifica región, itera sobre TODAS las regiones del proyecto.
        """
        logger.info("Escaneando IPs estáticas sin uso...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-unused-ip-1",
                    resource_type="google_compute_address",
                    project_id=self.project_id,
                    zone_or_region="us-central1",
                    reason="IP externa estática reservada sin asignar (DEMO)",
                    estimated_monthly_cost_usd=_IP_COST_PER_MONTH,
                ),
                IdleResource(
                    resource_id="demo-unused-ip-2",
                    resource_type="google_compute_address",
                    project_id=self.project_id,
                    zone_or_region="europe-west1",
                    reason="IP externa estática (Legacy) sin asignar (DEMO)",
                    estimated_monthly_cost_usd=_IP_COST_PER_MONTH,
                ),
            ]

        regions = [self.region] if self.region else self._get_all_regions()
        idle_ips: List[IdleResource] = []

        for region in regions:
            try:
                request = compute_v1.ListAddressesRequest(project=self.project_id, region=region)
                for address in self.address_client.list(request=request):
                    # RESERVED = creada pero no asignada a ningún recurso
                    if address.status == "RESERVED":
                        logger.info(f"IP ociosa detectada: {address.name} (región: {region})")
                        idle_ips.append(
                            IdleResource(
                                resource_id=address.name,
                                resource_type="google_compute_address",
                                project_id=self.project_id,
                                zone_or_region=region,
                                reason="IP externa estática reservada, sin asignar a ningún recurso",
                                estimated_monthly_cost_usd=_IP_COST_PER_MONTH,
                                labels=dict(address.labels or {}),
                            )
                        )
            except Exception as e:
                logger.warning(f"Error escaneando IPs en región {region}: {e}")

        logger.info(f"IPs sin uso detectadas: {len(idle_ips)}")
        return idle_ips

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scan_overly_permissive_firewalls(self) -> List[IdleResource]:
        """
        Detecta reglas de firewall que permiten acceso desde cualquier IP
        (0.0.0.0/0 o ::/0) hacia puertos sensibles (SSH:22, RDP:3389).
        Aunque no son un costo directo, representan un riesgo de seguridad
        que puede derivar en costos (bots mineros, exfiltración).
        """
        logger.info("Escaneando reglas de firewall excesivamente permisivas...")

        if self.demo_mode:
            return [
                IdleResource(
                    resource_id="demo-allow-ssh-world",
                    resource_type="google_compute_firewall",
                    project_id=self.project_id,
                    zone_or_region="global",
                    reason="Regla de firewall permite SSH (22) desde 0.0.0.0/0 — riesgo de seguridad (DEMO)",
                    estimated_monthly_cost_usd=0.0,
                ),
            ]

        risky_rules: List[IdleResource] = []
        _SENSITIVE_PORTS = {"22", "3389", "23", "5900"}

        try:
            request = compute_v1.ListFirewallsRequest(project=self.project_id)
            for fw in self.firewall_client.list(request=request):
                if fw.direction != "INGRESS":
                    continue
                source_ranges = list(fw.source_ranges or [])
                is_open_world = "0.0.0.0/0" in source_ranges or "::/0" in source_ranges
                if not is_open_world:
                    continue

                for allowed in fw.allowed:
                    ports = list(allowed.ports or [])
                    port_strs = {str(p).split("-")[0] for p in ports}
                    exposed = port_strs & _SENSITIVE_PORTS
                    if exposed or not ports:  # Sin puertos específicos = all ports
                        logger.warning(f"Regla permisiva detectada: {fw.name} (puertos: {ports or 'ALL'})")
                        risky_rules.append(
                            IdleResource(
                                resource_id=fw.name,
                                resource_type="google_compute_firewall",
                                project_id=self.project_id,
                                zone_or_region="global",
                                reason=f"Regla ingress abierta a 0.0.0.0/0 en puertos {ports or 'ALL'}",
                                estimated_monthly_cost_usd=0.0,
                            )
                        )
        except Exception as e:
            logger.error(f"Error escaneando reglas de firewall: {e}")
            raise ScannerError(f"Error escaneando firewalls: {e}")

        logger.info(f"Reglas de firewall permisivas detectadas: {len(risky_rules)}")
        return risky_rules
