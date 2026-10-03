"""
Lógica de negócio e registro de handlers MQTT para o Microsserviço de Veículos.
"""
from typing import Dict, Any, Tuple
from common.messaging import MQTTNode
from common import topics
from services.veiculos.database import VeiculosDB

class VeiculosService:
    def __init__(self, node: MQTTNode, db: VeiculosDB = None):
        self.node = node
        self.db = db or VeiculosDB()
        self._register_handlers()

    def _register_handlers(self):
        # Emplacar veículo
        self.node.register_handler(
            topics.VEICULO_EMPLACAR,
            topics.VEICULO_EMPLACAR_RESPOSTA,
            self.handle_emplacar
        )
        # Calcular IPVA
        self.node.register_handler(
            topics.VEICULO_IPVA,
            topics.VEICULO_IPVA_RESPOSTA,
            self.handle_calcular_ipva
        )
        # Listar por ano
        self.node.register_handler(
            topics.VEICULO_LISTAR_POR_ANO,
            topics.VEICULO_LISTAR_POR_ANO_RESPOSTA,
            self.handle_listar_por_ano
        )
        # Obter veículo por placa
        self.node.register_handler(
            topics.VEICULO_OBTER,
            topics.VEICULO_OBTER_RESPOSTA,
            self.handle_obter
        )
        # Listar placas por condutor
        self.node.register_handler(
            topics.VEICULO_POR_CONDUTOR,
            topics.VEICULO_POR_CONDUTOR_RESPOSTA,
            self.handle_por_condutor
        )
        # Listar mapeamento de proprietários (para agregação do Top 5 em multas)
        self.node.register_handler(
            topics.VEICULO_LISTAR_PROPRIETARIOS,
            topics.VEICULO_LISTAR_PROPRIETARIOS_RESPOSTA,
            self.handle_listar_proprietarios
        )
        # Atualizar proprietário
        self.node.register_handler(
            topics.VEICULO_ATUALIZAR_PROPRIETARIO,
            topics.VEICULO_ATUALIZAR_PROPRIETARIO_RESPOSTA,
            self.handle_atualizar_proprietario
        )

    def handle_emplacar(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        modelo = str(dados.get("modelo", "")).strip()
        cpf_condutor = str(dados.get("cpf_condutor", "")).strip()
        data_emplacamento = dados.get("data_emplacamento")

        if not placa:
            return False, "Placa do veículo não pode ser vazia.", None
        if not modelo:
            return False, "Modelo do veículo não pode ser vazio.", None
        if not cpf_condutor:
            return False, "CPF do condutor não pode ser vazio.", None

        try:
            valor = float(dados.get("valor", 0.0))
        except (ValueError, TypeError):
            return False, "Valor do veículo inválido.", None

        if valor < 0:
            return False, "Valor do veículo não pode ser negativo.", None

        # Validação do condutor através de comunicação MQTT com o serviço de Condutores
        self.node.logger.info(f"Validando condutor CPF={cpf_condutor} via MQTT...")
        resp_condutor = self.node.request(
            topics.CONDUTOR_OBTER,
            topics.CONDUTOR_OBTER_RESPOSTA,
            {"cpf": cpf_condutor}
        )

        if not resp_condutor.get("sucesso"):
            return False, (
                f"Condutor com CPF {cpf_condutor} não encontrado. "
                "Cadastre o condutor antes de emplacar o veículo."
            ), None

        # Condutor válido, prossegue com persistência
        return self.db.emplacar(placa, modelo, valor, cpf_condutor, data_emplacamento)

    def handle_calcular_ipva(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        if not placa:
            return False, "Placa não informada.", None
        return self.db.calcular_ipva(placa)

    def handle_listar_por_ano(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        ano = dados.get("ano")
        if ano is None:
            return False, "Ano não informado.", None

        try:
            ano_int = int(ano)
        except (ValueError, TypeError):
            return False, "Ano inválido.", None

        veiculos = self.db.listar_por_ano(ano_int)
        return True, f"{len(veiculos)} veículo(s) encontrado(s) emplacado(s) em {ano_int}.", veiculos

    def handle_obter(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        if not placa:
            return False, "Placa não informada.", None

        veiculo = self.db.obter(placa)
        if veiculo:
            return True, "Veículo localizado.", veiculo
        return False, f"Veículo com placa {placa} não encontrado.", None

    def handle_por_condutor(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        cpf = str(dados.get("cpf", "")).strip()
        if not cpf:
            return False, "CPF não informado.", None

        veiculos = self.db.listar_por_condutor(cpf)
        placas = [v["placa"] for v in veiculos]
        return True, f"{len(placas)} veículo(s) associado(s) ao CPF {cpf}.", placas

    def handle_listar_proprietarios(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        proprietarios = self.db.listar_proprietarios()
        return True, "Lista de proprietários obtida com sucesso.", proprietarios

    def handle_atualizar_proprietario(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        novo_cpf = str(dados.get("novo_cpf", "")).strip()

        if not placa:
            return False, "Placa não pode ser vazia.", None
        if not novo_cpf:
            return False, "Novo CPF não pode ser vazio.", None

        return self.db.atualizar_proprietario(placa, novo_cpf)
