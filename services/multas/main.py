"""
Ponto de entrada do Microsserviço de Multas.
"""
import sys
import os
import time
import signal

# Garante que o diretório raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.messaging import MQTTNode
from services.multas.service import MultasService

def main():
    node = MQTTNode("MULTAS")
    service = MultasService(node)

    def shutdown(signum, frame):
        node.logger.info("Encerrando microsserviço de Multas...")
        node.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        node.start()
        node.logger.info("Microsserviço de Multas aguardando requisições...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)
    except Exception as e:
        node.logger.error(f"Erro fatal no microsserviço de Multas: {e}")
        node.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
