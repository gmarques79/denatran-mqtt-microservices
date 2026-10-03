"""
Camada de comunicação MQTT para microsserviços e cliente.
Implementa o padrão Request-Response assíncrono via Pub/Sub com Correlation ID (UUID)
e execução desacoplada em ThreadPool para evitar deadlocks em chamadas síncronas entre serviços.
"""
import os
import json
import time
import uuid
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, Any, Optional, Dict, Tuple
import paho.mqtt.client as mqtt

from common.logger import get_logger
from common.config import MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE, DEFAULT_TIMEOUT

HandlerFunc = Callable[[Dict[str, Any]], Tuple[bool, str, Any]]

class MQTTNode:
    """
    Nó de comunicação MQTT com suporte a RPC assíncrono e handlers de requisição.
    """
    def __init__(
        self,
        service_name: str,
        host: str = MQTT_HOST,
        port: int = MQTT_PORT,
        keepalive: int = MQTT_KEEPALIVE,
        max_workers: int = 10,
        topic_prefix: str = ""
    ):
        self.service_name = service_name
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.topic_prefix = topic_prefix or os.getenv("MQTT_TOPIC_PREFIX", "")
        self.logger = get_logger(service_name)
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"{service_name}-worker")
        self._handlers: Dict[str, Tuple[str, HandlerFunc]] = {} # req_topic -> (resp_topic, func)
        self._pending_requests: Dict[str, Future] = {}          # request_id -> Future
        self._pending_lock = threading.Lock()
        self._subscribed_topics: set = set()
        self._connected = threading.Event()
        self._stop_event = threading.Event()

        client_id = f"{service_name.lower()}-{uuid.uuid4().hex[:8]}"
        if hasattr(mqtt, "CallbackAPIVersion"):
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        else:
            self.client = mqtt.Client(client_id=client_id)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, *args, **kwargs):
        self.logger.info(f"Conectado ao broker MQTT em {self.host}:{self.port}")
        self._connected.set()
        # Reinscrever tópicos caso tenha ocorrido reconexão
        for topic in list(self._subscribed_topics):
            self.client.subscribe(topic)
            self.logger.info(f"Inscrito em {topic}")

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        self._connected.clear()
        self.logger.warning("Desconectado do broker MQTT. Tentando reconectar...")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            raw_payload = msg.payload.decode("utf-8")
            payload = json.loads(raw_payload)
        except Exception as e:
            self.logger.error(f"Erro ao decodificar mensagem JSON do tópico {topic}: {e}")
            return

        request_id = payload.get("request_id")

        # 1. Verifica se é resposta para uma requisição pendente deste nó
        with self._pending_lock:
            if request_id and request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id, None)
                if future and not future.done():
                    future.set_result(payload)
                return

        # 2. Verifica se é requisição para um handler registrado
        if topic in self._handlers:
            resp_topic, handler = self._handlers[topic]
            # Executa o processamento em uma thread do executor para não bloquear a thread MQTT de rede
            self.executor.submit(self._dispatch_request, topic, resp_topic, handler, payload)

    def _dispatch_request(self, req_topic: str, resp_topic: str, handler: HandlerFunc, payload: Dict[str, Any]):
        request_id = payload.get("request_id", str(uuid.uuid4()))
        dados = payload.get("dados", {})
        
        self.logger.info(f"Requisição recebida em [{req_topic}] ID={request_id}")
        try:
            sucesso, mensagem, resposta_dados = handler(dados)
        except Exception as e:
            self.logger.error(f"Exceção não tratada ao processar requisição em [{req_topic}]: {e}")
            sucesso = False
            mensagem = f"Erro interno ao processar requisição: {str(e)}"
            resposta_dados = None

        response_payload = {
            "request_id": request_id,
            "sucesso": sucesso,
            "mensagem": mensagem,
            "dados": resposta_dados
        }

        self.publish(resp_topic, response_payload)
        self.logger.info(f"Resposta enviada para [{resp_topic}] ID={request_id} (sucesso={sucesso})")

    def register_handler(self, req_topic: str, resp_topic: str, handler: HandlerFunc):
        """
        Registra um manipulador para um tópico de requisição.
        Quando uma mensagem chegar em req_topic, handler(dados) será executado
        e o resultado publicado em resp_topic com o mesmo request_id.
        """
        if self.topic_prefix and not req_topic.startswith(self.topic_prefix):
            req_topic = f"{self.topic_prefix}{req_topic}"
        if self.topic_prefix and not resp_topic.startswith(self.topic_prefix):
            resp_topic = f"{self.topic_prefix}{resp_topic}"

        self._handlers[req_topic] = (resp_topic, handler)
        self._subscribed_topics.add(req_topic)
        if self._connected.is_set():
            self.client.subscribe(req_topic)
            self.logger.info(f"Inscrito em {req_topic}")

    def start(self, retry_attempts: int = 15, retry_interval: float = 2.0):
        """
        Inicia a conexão com o broker MQTT e dispara o loop em background.
        Possui retry automático para aguardar o broker inicializar.
        """
        self.logger.info(f"Iniciando conexão com broker MQTT em {self.host}:{self.port}...")
        attempt = 0
        while attempt < retry_attempts and not self._stop_event.is_set():
            try:
                attempt += 1
                self.client.connect(self.host, self.port, keepalive=self.keepalive)
                self.client.loop_start()
                if self._connected.wait(timeout=5.0):
                    self.logger.info("Loop de rede MQTT ativo e operacional.")
                    return
            except Exception as e:
                self.logger.warning(
                    f"Tentativa {attempt}/{retry_attempts} falhou ao conectar em {self.host}:{self.port}: {e}. "
                    f"Nova tentativa em {retry_interval}s..."
                )
                time.sleep(retry_interval)

        if not self._connected.is_set():
            raise ConnectionError(f"Não foi possível conectar ao broker MQTT em {self.host}:{self.port} após {retry_attempts} tentativas.")

    def publish(self, topic: str, payload: Dict[str, Any]):
        """
        Publica um dicionário como JSON em um tópico MQTT.
        """
        if self.topic_prefix and not topic.startswith(self.topic_prefix):
            topic = f"{self.topic_prefix}{topic}"
        msg_str = json.dumps(payload, ensure_ascii=False)
        self.client.publish(topic, msg_str, qos=1)

    def request(
        self,
        request_topic: str,
        response_topic: str,
        dados: Dict[str, Any],
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Envia uma requisição assíncrona com Correlation ID e aguarda a resposta correspondente.
        Retorna o dicionário de resposta com chaves: request_id, sucesso, mensagem, dados.
        """
        if self.topic_prefix and not request_topic.startswith(self.topic_prefix):
            request_topic = f"{self.topic_prefix}{request_topic}"
        if self.topic_prefix and not response_topic.startswith(self.topic_prefix):
            response_topic = f"{self.topic_prefix}{response_topic}"

        request_id = str(uuid.uuid4())
        future = Future()

        with self._pending_lock:
            self._pending_requests[request_id] = future

        # Garante inscrição no tópico de resposta
        if response_topic not in self._subscribed_topics:
            self._subscribed_topics.add(response_topic)
            if self._connected.is_set():
                self.client.subscribe(response_topic)
                self.logger.info(f"Inscrito para respostas em {response_topic}")

        req_payload = {
            "request_id": request_id,
            "dados": dados
        }

        self.publish(request_topic, req_payload)

        try:
            response = future.result(timeout=timeout)
            return response
        except FutureTimeoutError:
            with self._pending_lock:
                self._pending_requests.pop(request_id, None)
            self.logger.warning(f"Timeout ({timeout}s) aguardando resposta em [{response_topic}] para ID={request_id}")
            return {
                "request_id": request_id,
                "sucesso": False,
                "mensagem": f"Tempo limite de espera esgotado ({timeout}s) aguardando resposta do serviço em {request_topic}",
                "dados": None
            }
        except Exception as e:
            with self._pending_lock:
                self._pending_requests.pop(request_id, None)
            self.logger.error(f"Erro na requisição para [{request_topic}]: {e}")
            return {
                "request_id": request_id,
                "sucesso": False,
                "mensagem": f"Erro na requisição: {str(e)}",
                "dados": None
            }

    def stop(self):
        """
        Finaliza a conexão e encerra o pool de threads.
        """
        self._stop_event.set()
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        self.executor.shutdown(wait=False)
        self.logger.info("Nó MQTT finalizado.")
