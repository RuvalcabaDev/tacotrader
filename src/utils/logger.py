import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "tacotrader",
    level: str = "INFO",
    format_str: Optional[str] = None,
) -> logging.Logger:
    """
    Configura y retorna un logger.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_str: Formato personalizado para los logs
        
    Returns:
        Logger configurado
    """
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurar nivel
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Evitar handlers duplicados
    if logger.handlers:
        return logger
    
    # Crear formatter
    formatter = logging.Formatter(format_str)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Logger por defecto
logger = setup_logger()