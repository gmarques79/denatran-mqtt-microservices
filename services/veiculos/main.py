"""
Ponto de entrada do Microsserviço de Veículos.
"""
import sys
import os
import time
import signal

# Garante que o diretório raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.messaging import MQTTNode
from services.veiculos.service import VeiculosService

def main():
    node = MQTTNode("VEICULOS")
    service = VeiculosService(node)

    def shutdown(signum, frame):
        node.logger.info("Encerrando microsserviço de Veículos...")
        node.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        node.start()
        node.logger.info("Microsserviço de Veículos aguardando requisições...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)
    except Exception as e:
        node.logger.error(f"Erro fatal no microsserviço de Veículos: {e}")
        node.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
