"""
Lógica de negócio e registro de handlers MQTT para o Microsserviço de Condutores.
"""
from typing import Dict, Any, Tuple
from common.messaging import MQTTNode
from common import topics
from services.condutores.database import CondutoresDB

class CondutoresService:
    def __init__(self, node: MQTTNode, db: CondutoresDB = None):
        self.node = node
        self.db = db or CondutoresDB()
        self._register_handlers()

    def _register_handlers(self):
        # Cadastrar condutor
        self.node.register_handler(
            topics.CONDUTOR_CADASTRAR,
            topics.CONDUTOR_CADASTRAR_RESPOSTA,
            self.handle_cadastrar
        )
        # Obter condutor por CPF
        self.node.register_handler(
            topics.CONDUTOR_OBTER,
            topics.CONDUTOR_OBTER_RESPOSTA,
            self.handle_obter
        )
        # Listar condutores
        self.node.register_handler(
            topics.CONDUTOR_LISTAR,
            topics.CONDUTOR_LISTAR_RESPOSTA,
            self.handle_listar
        )
        # Transferência de proprietário (iniciada pelo cliente)
        self.node.register_handler(
            topics.CONDUTOR_TRANSFERIR,
            topics.CONDUTOR_TRANSFERIR_RESPOSTA,
            self.handle_transferir
        )
        # Também atende se a requisição de transferência for enviada no tópico do veículo
        self.node.register_handler(
            topics.VEICULO_TRANSFERIR,
            topics.VEICULO_TRANSFERIR_RESPOSTA,
            self.handle_transferir
        )

    def handle_cadastrar(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        cpf = dados.get("cpf", "")
        nome = dados.get("nome", "")
        return self.db.cadastrar(cpf, nome)

    def handle_obter(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        cpf = str(dados.get("cpf", "")).strip()
        if not cpf:
            return False, "CPF não informado.", None

        condutor = self.db.obter(cpf)
        if condutor:
            return True, "Condutor localizado.", condutor
        return False, f"Condutor com CPF {cpf} não encontrado.", None

    def handle_listar(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        condutores = self.db.listar()
        return True, f"{len(condutores)} condutor(es) cadastrado(s).", condutores

    def handle_transferir(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        """
        Coordena a transferência de propriedade:
        1. Verifica se o novo condutor existe no banco de dados de Condutores.
        2. Solicita via MQTT ao Microsserviço de Veículos a alteração do proprietário.
        """
        placa = str(dados.get("placa", "")).strip().upper()
        novo_cpf = str(dados.get("novo_cpf") or dados.get("cpf_novo_dono") or "").strip()

        if not placa:
            return False, "Placa do veículo não pode ser vazia.", None
        if not novo_cpf:
            return False, "CPF do novo proprietário não pode ser vazio.", None

        # 1. Verifica existência do novo condutor
        novo_condutor = self.db.obter(novo_cpf)
        if not novo_condutor:
            return False, f"Novo condutor com CPF {novo_cpf} não está cadastrado no sistema.", None

        # 2. Chama o microsserviço de Veículos via MQTT para efetuar a atualização
        resp = self.node.request(
            topics.VEICULO_ATUALIZAR_PROPRIETARIO,
            topics.VEICULO_ATUALIZAR_PROPRIETARIO_RESPOSTA,
            {"placa": placa, "novo_cpf": novo_cpf}
        )

        if not resp.get("sucesso"):
            return False, resp.get("mensagem", "Falha ao atualizar proprietário no serviço de Veículos."), None

        mensagem_sucesso = (
            f"Proprietário do veículo {placa} transferido com sucesso para "
            f"{novo_condutor['nome']} (CPF: {novo_cpf})."
        )
        return True, mensagem_sucesso, resp.get("dados")
