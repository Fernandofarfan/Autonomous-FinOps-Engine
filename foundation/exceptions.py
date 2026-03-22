class FinOpsEngineError(Exception):
    """Excepción base para el Motor de FinOps."""
    pass

class ScannerError(FinOpsEngineError):
    """Excepciones relacionadas a los escáneres."""
    pass

class AnalyzerError(FinOpsEngineError):
    """Excepciones relacionadas al análisis."""
    pass

class GeneratorError(FinOpsEngineError):
    """Excepciones relacionadas a la generación de Terraform."""
    pass
