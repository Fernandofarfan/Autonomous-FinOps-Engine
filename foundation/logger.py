import logging
import sys
import os

try:
    import colorlog
    _COLORLOG_AVAILABLE = True
except ImportError:
    _COLORLOG_AVAILABLE = False

# Directorio de logs relativo al módulo
_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finops.log")

_COLOR_MAP = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def get_logger(name: str) -> logging.Logger:
    """
    Configura y retorna un logger estructurado con:
    - Salida a stdout con colores (si colorlog está disponible).
    - Salida a archivo 'finops.log' en el directorio raíz del proyecto.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    log_format = "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # — Handler 1: Consola (stdout), con colores si colorlog disponible —
    if _COLORLOG_AVAILABLE:
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_formatter = colorlog.ColoredFormatter(
            fmt=f"%(log_color)s{log_format}%(reset)s",
            datefmt=date_format,
            log_colors=_COLOR_MAP,
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # — Handler 2: Archivo finops.log (DEBUG completo) —
    try:
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Si no se puede escribir el archivo, simplemente se omite
        pass

    return logger
