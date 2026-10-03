"""
Configuração padronizada de logging com prefixos de serviço.
"""
import logging
import sys

def get_logger(service_name: str) -> logging.Logger:
    """
    Retorna um logger formatado no padrão [SERVICO] Mensagem.
    """
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt=f"[{service_name.upper()}] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
