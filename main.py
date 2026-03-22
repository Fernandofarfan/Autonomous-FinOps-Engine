import os
from foundation.analyzer import ResourceAnalyzer
from foundation.logger import get_logger
from compute.scanner import ComputeScanner
from networking.scanner import NetworkScanner
from remediation.generator import TerraformGenerator

logger = get_logger("finops_engine.main")

def main() -> None:
    # 0. Configuración Initial y Setup
    project_id = os.getenv("GCP_PROJECT_ID", "my-finops-project")
    zone = os.getenv("GCP_ZONE", "us-central1-a")
    region = os.getenv("GCP_REGION", "us-central1")
    
    logger.info("=== Bootstrapping Autonomous FinOps Engine ===")
    
    # 1. Scanning
    logger.info("Fase 1: Escaneo Multi-Pilar Invocado...")
    compute_scanner = ComputeScanner(project_id, zone)
    network_scanner = NetworkScanner(project_id, region)
    
    unattached_disks = compute_scanner.scan_unattached_disks()
    unused_ips = network_scanner.scan_unused_ips()
    
    # 2. Analysis
    logger.info("Fase 2: Consolidación y Análisis de Desperdicios...")
    analyzer = ResourceAnalyzer()
    analyzer.add_resources(unattached_disks)
    analyzer.add_resources(unused_ips)
    
    report_json = analyzer.generate_report()
    logger.info(f"Reporte de Finanzas Extraído:\n{report_json}")
    
    # 3. Remediation (IaC Generation)
    logger.info("Fase 3: Generando Código de Remediación (Terraform)...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "remediation", "templates")
    # Terraform output
    output_dir = os.path.join(base_dir, "tf_output")
    
    generator = TerraformGenerator(template_dir=templates_dir, output_dir=output_dir)
    generator.generate(report_json)
    
    logger.info("=== FinOps Engine Pipeline Terminado Exitosamente ===")

if __name__ == "__main__":
    main()
