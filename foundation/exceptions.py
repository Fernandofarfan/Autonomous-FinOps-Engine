class FinOpsEngineError(Exception):
    """Excepción base para el Motor de FinOps."""
    pass


class ScannerError(FinOpsEngineError):
    """Excepciones producidas durante el escaneo de recursos GCP."""
    pass


class AnalyzerError(FinOpsEngineError):
    """Excepciones relacionadas al análisis y consolidación de hallazgos."""
    pass


class GeneratorError(FinOpsEngineError):
    """Excepciones durante la generación de código de infraestructura (Terraform/IaC)."""
    pass


class RemediationError(FinOpsEngineError):
    """Excepciones durante la ejecución autónoma de Terraform (terraform apply)."""
    pass


class ConfigurationError(FinOpsEngineError):
    """Excepciones de configuración inválida al arrancar el motor."""
    pass
