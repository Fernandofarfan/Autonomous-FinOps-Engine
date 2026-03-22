import os
import json
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from foundation.exceptions import GeneratorError
from foundation.logger import get_logger

logger = get_logger(__name__)

class TerraformGenerator:
    """Toma el reporte JSON de recursos ociosos y genera código IaC (Terraform)."""
    
    def __init__(self, template_dir: str, output_dir: str) -> None:
        self.template_dir = template_dir
        self.output_dir = output_dir
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        try:
            self.env = Environment(loader=FileSystemLoader(self.template_dir))
            logger.info(f"Jinja2 TerraformGenerator inicializado (templates={template_dir})")
        except Exception as e:
            logger.error(f"Fallo al cargar las plantillas Jinja2: {e}")
            raise GeneratorError(f"Error inicializando Jinja2: {e}")

    def generate(self, report_json: str) -> None:
        """Orquesta la creación de archivos Terraform (main.tf y variables.tf)."""
        logger.info("Iniciando generación de código Terraform...")
        try:
            data = json.loads(report_json)
            idle_resources = data.get("idle_resources", [])
            
            if not idle_resources:
                logger.info("No hay recursos ociosos. Operación omitida.")
                return
                
            self._generate_main_tf(idle_resources)
            self._generate_variables_tf()
            
            logger.info(f"Archivos de Terraform generados exitosamente en -> {self.output_dir}")
        except json.JSONDecodeError as jde:
            logger.error(f"JSON inválido provisto al generador: {jde}")
            raise GeneratorError(f"Error parseando JSON: {jde}")
        except Exception as e:
            logger.error(f"Fallo inesperado al generar código Terraform: {e}")
            raise GeneratorError(f"Error generando IaC: {e}")
            
    def _generate_main_tf(self, resources: List[Dict[str, Any]]) -> None:
        """Renderiza main.tf con imports y definiciones de recursos."""
        template = self.env.get_template("main.tf.j2")
        rendered = template.render(resources=resources)
        
        output_path = os.path.join(self.output_dir, "main.tf")
        with open(output_path, "w") as f:
            f.write(rendered)
        logger.info(f"Archivo generado: {output_path}")

    def _generate_variables_tf(self) -> None:
        """Renderiza variables.tf."""
        template = self.env.get_template("variables.tf.j2")
        rendered = template.render()
        
        output_path = os.path.join(self.output_dir, "variables.tf")
        with open(output_path, "w") as f:
            f.write(rendered)
        logger.info(f"Archivo generado: {output_path}")
