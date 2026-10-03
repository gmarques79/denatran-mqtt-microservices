"""
Lógica de negócio e registro de handlers MQTT para o Microsserviço de Multas.
"""
from collections import defaultdict
from typing import Dict, Any, Tuple
from common.messaging import MQTTNode
from common import topics
from services.multas.database import MultasDB

class MultasService:
    def __init__(self, node: MQTTNode, db: MultasDB = None):
        self.node = node
        self.db = db or MultasDB()
        self._register_handlers()

    def _register_handlers(self):
        # Lançar multa
        self.node.register_handler(
            topics.MULTA_LANCAR,
            topics.MULTA_LANCAR_RESPOSTA,
            self.handle_lancar
        )
        # Multas por veículo em um ano
        self.node.register_handler(
            topics.MULTA_POR_VEICULO,
            topics.MULTA_POR_VEICULO_RESPOSTA,
            self.handle_por_veiculo
        )
        # Multas por condutor em um ano
        self.node.register_handler(
            topics.MULTA_POR_CONDUTOR,
            topics.MULTA_POR_CONDUTOR_RESPOSTA,
            self.handle_por_condutor
        )
        # Multas lançadas em um ano
        self.node.register_handler(
            topics.MULTA_POR_ANO,
            topics.MULTA_POR_ANO_RESPOSTA,
            self.handle_por_ano
        )
        # Top 5 condutores com maiores pontuações
        self.node.register_handler(
            topics.MULTA_TOP_5,
            topics.MULTA_TOP_5_RESPOSTA,
            self.handle_top_5
        )

    def handle_lancar(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        descricao = str(dados.get("descricao", "")).strip()

        if not placa:
            return False, "Placa do veículo não pode ser vazia.", None
        if not descricao:
            return False, "Descrição da multa não pode ser vazia.", None

        try:
            pontuacao = int(dados.get("pontuacao"))
        except (ValueError, TypeError):
            return False, "Pontuação inválida.", None

        if pontuacao < 0:
            return False, "Pontuação não pode ser negativa.", None

        try:
            ano = int(dados.get("ano"))
        except (ValueError, TypeError):
            return False, "Ano inválido.", None

        if ano < 1900 or ano > 2100:
            return False, "Ano inválido (deve ser entre 1900 e 2100).", None

        # Validação da existência do veículo via MQTT com o serviço de Veículos
        self.node.logger.info(f"Validando veículo placa={placa} via MQTT...")
        resp_veiculo = self.node.request(
            topics.VEICULO_OBTER,
            topics.VEICULO_OBTER_RESPOSTA,
            {"placa": placa}
        )

        if not resp_veiculo.get("sucesso"):
            return False, f"Veículo com placa {placa} não encontrado. Multa não pode ser lançada.", None

        return self.db.lancar(ano, descricao, pontuacao, placa)

    def handle_por_veiculo(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        placa = str(dados.get("placa", "")).strip().upper()
        if not placa:
            return False, "Placa não informada.", None

        try:
            ano = int(dados.get("ano"))
        except (ValueError, TypeError):
            return False, "Ano inválido.", None

        # 1. Obter dados do veículo via MQTT
        resp_veiculo = self.node.request(
            topics.VEICULO_OBTER,
            topics.VEICULO_OBTER_RESPOSTA,
            {"placa": placa}
        )
        if not resp_veiculo.get("sucesso"):
            return False, f"Veículo com placa {placa} não encontrado.", None

        veiculo_dados = resp_veiculo.get("dados", {})
        cpf_condutor = veiculo_dados.get("cpf_condutor", "")

        # 2. Obter dados do condutor via MQTT
        nome_condutor = "Desconhecido"
        if cpf_condutor:
            resp_condutor = self.node.request(
                topics.CONDUTOR_OBTER,
                topics.CONDUTOR_OBTER_RESPOSTA,
                {"cpf": cpf_condutor}
            )
            if resp_condutor.get("sucesso"):
                nome_condutor = resp_condutor.get("dados", {}).get("nome", "Desconhecido")

        # 3. Buscar multas no banco local de multas
        multas = self.db.listar_por_veiculo_ano(placa, ano)
        multas_formatadas = [
            {
                "id": m["id"],
                "descricao": m["descricao"],
                "pontuacao": m["pontuacao"]
            }
            for m in multas
        ]

        resultado = {
            "placa": placa,
            "ano": ano,
            "condutor": {
                "cpf": cpf_condutor,
                "nome": nome_condutor
            },
            "multas": multas_formatadas
        }

        return True, f"{len(multas_formatadas)} multa(s) localizada(s) para o veículo {placa} em {ano}.", resultado

    def handle_por_condutor(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        cpf = str(dados.get("cpf", "")).strip()
        if not cpf:
            return False, "CPF não informado.", None

        try:
            ano = int(dados.get("ano"))
        except (ValueError, TypeError):
            return False, "Ano inválido.", None

        # 1. Validar condutor via MQTT
        resp_condutor = self.node.request(
            topics.CONDUTOR_OBTER,
            topics.CONDUTOR_OBTER_RESPOSTA,
            {"cpf": cpf}
        )
        if not resp_condutor.get("sucesso"):
            return False, f"Condutor com CPF {cpf} não encontrado.", None

        nome_condutor = resp_condutor.get("dados", {}).get("nome", "")

        # 2. Obter placas associadas ao condutor via MQTT com Veículos
        resp_veiculos = self.node.request(
            topics.VEICULO_POR_CONDUTOR,
            topics.VEICULO_POR_CONDUTOR_RESPOSTA,
            {"cpf": cpf}
        )
        placas = resp_veiculos.get("dados", []) if resp_veiculos.get("sucesso") else []

        # 3. Consultar multas dessas placas no ano
        multas = self.db.listar_por_placas_ano(placas, ano)
        total_pontos = sum(m["pontuacao"] for m in multas)

        resultado = {
            "cpf": cpf,
            "nome": nome_condutor,
            "ano": ano,
            "veiculos": placas,
            "total_pontos": total_pontos,
            "total_multas": len(multas),
            "multas": multas
        }

        return True, f"{len(multas)} multa(s) localizada(s) para o condutor {nome_condutor} em {ano} (Total: {total_pontos} pts).", resultado

    def handle_por_ano(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        try:
            ano = int(dados.get("ano"))
        except (ValueError, TypeError):
            return False, "Ano inválido.", None

        multas = self.db.listar_por_ano(ano)
        resultado = {
            "ano": ano,
            "total_multas": len(multas),
            "multas": multas
        }
        return True, f"{len(multas)} multa(s) lançada(s) no ano {ano}.", resultado

    def handle_top_5(self, dados: Dict[str, Any]) -> Tuple[bool, str, Any]:
        # 1. Agregação de pontos por placa no banco local de multas
        pontos_por_placa = self.db.total_pontos_por_placa()
        if not pontos_por_placa:
            return True, "Nenhuma multa registrada no sistema.", []

        # 2. Obter mapeamento de veículo -> condutor via MQTT com o serviço de Veículos
        resp_props = self.node.request(
            topics.VEICULO_LISTAR_PROPRIETARIOS,
            topics.VEICULO_LISTAR_PROPRIETARIOS_RESPOSTA,
            {}
        )
        if not resp_props.get("sucesso"):
            return False, "Falha ao obter relação de veículos e condutores do serviço de Veículos.", None

        proprietarios = resp_props.get("dados", [])
        mapa_placa_cpf = {p["placa"]: p["cpf_condutor"] for p in proprietarios}

        # 3. Agrega a pontuação por condutor (CPF)
        pontos_por_cpf = defaultdict(int)
        for item in pontos_por_placa:
            placa = item["placa"]
            pts = item["total_pontos"]
            cpf = mapa_placa_cpf.get(placa)
            if cpf:
                pontos_por_cpf[cpf] += pts

        if not pontos_por_cpf:
            return True, "Nenhum condutor associado a veículos com multas.", []

        # 4. Ordenação decrescente pela pontuação total
        ranking_ordenado = sorted(pontos_por_cpf.items(), key=lambda x: x[1], reverse=True)[:5]

        # 5. Obter os nomes dos condutores via MQTT com o serviço de Condutores
        resultado_top_5 = []
        for posicao, (cpf, total_pts) in enumerate(ranking_ordenado, start=1):
            resp_cond = self.node.request(
                topics.CONDUTOR_OBTER,
                topics.CONDUTOR_OBTER_RESPOSTA,
                {"cpf": cpf}
            )
            nome = "Desconhecido"
            if resp_cond.get("sucesso"):
                nome = resp_cond.get("dados", {}).get("nome", "Desconhecido")

            resultado_top_5.append({
                "posicao": posicao,
                "cpf": cpf,
                "nome": nome,
                "pontuacao_total": total_pts
            })

        return True, "Top 5 condutores com maiores pontuações obtido com sucesso.", resultado_top_5
