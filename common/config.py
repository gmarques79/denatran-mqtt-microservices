"""
Configurações globais e por variáveis de ambiente.
"""
import os

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
DEFAULT_TIMEOUT = float(os.getenv("DEFAULT_TIMEOUT", "7.0"))
