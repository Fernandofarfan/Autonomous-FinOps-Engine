import os
import subprocess
from typing import List

from jinja2 import Environment, FileSystemLoader

from foundation.models import IdleResource
from foundation.exceptions import GeneratorError, RemediationError
from foundation.logger import get_logger

logger = get_logger(__name__)


class TerraformGenerator:
    """
    Toma la lista consolidada de recursos ociosos (IdleResource) y genera
    código Terraform listo para importar y destruir los recursos detectados.

    Opcionalmente puede ejecutar `terraform init` y `terraform apply -auto-approve`
    de forma autónoma si AUTO_APPLY=true.
    """

    def __init__(self, template_dir: str, output_dir: str) -> None:
        self.template_dir = template_dir
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            logger.info(f"Jinja2 TerraformGenerator inicializado (templates={template_dir})")
        except Exception as e:
            logger.error(f"Fallo al cargar las plantillas Jinja2: {e}")
            raise GeneratorError(f"Error inicializando Jinja2: {e}")

    def generate(self, idle_resources: List[IdleResource], auto_apply: bool = False) -> None:
        """
        Orquesta la generación de archivos Terraform y, si auto_apply=True,
        ejecuta el plan completo de remediación.

        Args:
            idle_resources: Lista directa de objetos IdleResource (sin JSON).
            auto_apply: Si True, ejecuta terraform init + apply automáticamente.
        """
        logger.info("Iniciando generación de código Terraform...")

        if not idle_resources:
            logger.info("No hay recursos ociosos detectados. Generación omitida.")
            return

        try:
            resource_dicts = [r.model_dump() for r in idle_resources]
            # Normalizar claves para los templates
            for rd, r in zip(resource_dicts, idle_resources):
                rd["id"] = r.resource_id
                rd["type"] = r.resource_type
                rd["project"] = r.project_id
                rd["location"] = r.zone_or_region

            self._generate_main_tf(resource_dicts)
            self._generate_variables_tf()
            self._generate_outputs_tf(resource_dicts)

            logger.info(f"Archivos Terraform generados exitosamente → {self.output_dir}")

            if auto_apply:
                self._execute_terraform()

        except GeneratorError:
            raise
        except Exception as e:
            logger.error(f"Fallo inesperado al generar código Terraform: {e}")
            raise GeneratorError(f"Error generando IaC: {e}")

    def _generate_main_tf(self, resources: list) -> None:
        """Renderiza main.tf con bloques import{} y resource{} para cada recurso."""
        template = self.env.get_template("main.tf.j2")
        rendered = template.render(resources=resources)
        output_path = os.path.join(self.output_dir, "main.tf")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        logger.info(f"Generado: {output_path}")

    def _generate_variables_tf(self) -> None:
        """Renderiza variables.tf."""
        template = self.env.get_template("variables.tf.j2")
        rendered = template.render()
        output_path = os.path.join(self.output_dir, "variables.tf")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        logger.info(f"Generado: {output_path}")

    def _generate_outputs_tf(self, resources: list) -> None:
        """Renderiza outputs.tf con la lista de recursos que serán eliminados."""
        template = self.env.get_template("outputs.tf.j2")
        rendered = template.render(resources=resources)
        output_path = os.path.join(self.output_dir, "outputs.tf")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        logger.info(f"Generado: {output_path}")

    def _execute_terraform(self) -> None:
        """
        Ejecuta terraform init y terraform apply -auto-approve en el directorio
        de salida. Requiere que Terraform esté instalado en el PATH del sistema.

        ⚠️  ADVERTENCIA: Esto destruirá recursos reales en GCP. Solo usar con
        credenciales ADC configuradas y revisión previa de los archivos .tf.
        """
        logger.warning("=" * 60)
        logger.warning("AUTO-APPLY ACTIVADO — Ejecutando Terraform de forma autónoma.")
        logger.warning("Se DESTRUIRÁN recursos reales en GCP. Presiona Ctrl+C para abortar.")
        logger.warning("=" * 60)

        try:
            # 1. Terraform init
            logger.info("Ejecutando: terraform init")
            init_result = subprocess.run(
                ["terraform", "init"],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if init_result.returncode != 0:
                raise RemediationError(f"terraform init falló:\n{init_result.stderr}")
            logger.info("Terraform init completado exitosamente.")

            # 2. Terraform apply
            logger.info("Ejecutando: terraform apply -auto-approve")
            apply_result = subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if apply_result.returncode != 0:
                raise RemediationError(f"terraform apply falló:\n{apply_result.stderr}")

            logger.info("✅ Terraform apply completado. Recursos remediados exitosamente.")
            logger.info(apply_result.stdout)

        except FileNotFoundError:
            raise RemediationError(
                "Terraform no encontrado en el PATH. "
                "Instálalo desde https://developer.hashicorp.com/terraform/downloads"
            )
        except subprocess.TimeoutExpired:
            raise RemediationError("Terraform excedió el tiempo de espera (timeout).")
