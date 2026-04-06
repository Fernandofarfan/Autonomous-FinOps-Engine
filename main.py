"""
Punto de entrada principal del Autonomous FinOps Engine.
Delega al CLI de Typer. Equivale a ejecutar: python cli.py run
"""
from cli import app

if __name__ == "__main__":
    # Compatibilidad retroactiva: ejecutar `python main.py` corre el pipeline completo
    import sys
    sys.argv = ["finops", "run"]
    app()
