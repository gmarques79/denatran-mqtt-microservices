"""
Testes unitários para o Microsserviço de Multas.
"""
from unittest.mock import MagicMock
from services.multas.database import MultasDB
from services.multas.service import MultasService
from common import topics

def test_lancamento_valido(temp_multas_db: MultasDB):
    sucesso, msg, dados = temp_multas_db.lancar(
        ano=2026,
        descricao="Excesso de velocidade",
        pontuacao=5,
        placa="ABC1D23"
    )
    assert sucesso is True
    assert "sucesso" in msg.lower()
    assert dados["id"] == 1
    assert dados["pontuacao"] == 5
    assert dados["placa"] == "ABC1D23"

def test_validacoes_campos_multa(temp_multas_db: MultasDB):
    # Placa vazia
    sucesso, msg, _ = temp_multas_db.lancar(2026, "Descricao", 5, "")
    assert sucesso is False
    assert "placa" in msg.lower()

    # Descricao vazia
    sucesso, msg, _ = temp_multas_db.lancar(2026, "", 5, "ABC1D23")
    assert sucesso is False
    assert "descrição" in msg.lower()

    # Pontuacao negativa
    sucesso, msg, _ = temp_multas_db.lancar(2026, "Descricao", -2, "ABC1D23")
    assert sucesso is False
    assert "negativa" in msg.lower()

    # Ano invalido
    sucesso, msg, _ = temp_multas_db.lancar(1800, "Descricao", 5, "ABC1D23")
    assert sucesso is False
    assert "ano inválido" in msg.lower()

def test_service_veiculo_inexistente_rejeitado(temp_multas_db: MultasDB):
    mock_node = MagicMock()
    service = MultasService(node=mock_node, db=temp_multas_db)

    # Veículo não encontrado via MQTT
    mock_node.request.return_value = {"sucesso": False, "mensagem": "Veículo não encontrado"}

    sucesso, msg, dados = service.handle_lancar({
        "ano": 2026,
        "descricao": "Estacionar em local proibido",
        "pontuacao": 4,
        "placa": "NAOEXISTE"
    })
    assert sucesso is False
    assert "não encontrado" in msg.lower()

def test_consulta_multas_por_veiculo_com_condutor(temp_multas_db: MultasDB):
    mock_node = MagicMock()
    service = MultasService(node=mock_node, db=temp_multas_db)

    # Cadastra multas no banco local de multas
    temp_multas_db.lancar(2026, "Excesso de velocidade", 5, "ABC1D23")
    temp_multas_db.lancar(2026, "Avanço de sinal vermelho", 7, "ABC1D23")
    temp_multas_db.lancar(2025, "Outra infração", 3, "ABC1D23") # ano diferente

    def mock_request(req_topic, resp_topic, dados, **kwargs):
        if req_topic == topics.VEICULO_OBTER:
            return {"sucesso": True, "dados": {"placa": "ABC1D23", "cpf_condutor": "12345678900"}}
        elif req_topic == topics.CONDUTOR_OBTER:
            return {"sucesso": True, "dados": {"cpf": "12345678900", "nome": "João da Silva"}}
        return {"sucesso": False}

    mock_node.request.side_effect = mock_request

    sucesso, msg, dados = service.handle_por_veiculo({"placa": "ABC1D23", "ano": 2026})
    assert sucesso is True
    assert dados["placa"] == "ABC1D23"
    assert dados["ano"] == 2026
    assert dados["condutor"]["cpf"] == "12345678900"
    assert dados["condutor"]["nome"] == "João da Silva"
    assert len(dados["multas"]) == 2
    assert dados["multas"][0]["pontuacao"] == 5
    assert dados["multas"][1]["pontuacao"] == 7

def test_consulta_multas_por_condutor(temp_multas_db: MultasDB):
    mock_node = MagicMock()
    service = MultasService(node=mock_node, db=temp_multas_db)

    temp_multas_db.lancar(2026, "Multa Carro 1", 5, "CARRO1")
    temp_multas_db.lancar(2026, "Multa Carro 2", 7, "CARRO2")

    def mock_request(req_topic, resp_topic, dados, **kwargs):
        if req_topic == topics.CONDUTOR_OBTER:
            return {"sucesso": True, "dados": {"cpf": "111", "nome": "Carlos"}}
        elif req_topic == topics.VEICULO_POR_CONDUTOR:
            return {"sucesso": True, "dados": ["CARRO1", "CARRO2"]}
        return {"sucesso": False}

    mock_node.request.side_effect = mock_request

    sucesso, msg, dados = service.handle_por_condutor({"cpf": "111", "ano": 2026})
    assert sucesso is True
    assert dados["nome"] == "Carlos"
    assert dados["total_pontos"] == 12
    assert len(dados["multas"]) == 2

def test_consulta_multas_por_ano(temp_multas_db: MultasDB):
    temp_multas_db.lancar(2026, "Multa 1", 3, "ABC1D23")
    temp_multas_db.lancar(2026, "Multa 2", 4, "XYZ9999")
    temp_multas_db.lancar(2025, "Multa Antiga", 5, "ABC1D23")

    mock_node = MagicMock()
    service = MultasService(node=mock_node, db=temp_multas_db)

    sucesso, msg, dados = service.handle_por_ano({"ano": 2026})
    assert sucesso is True
    assert dados["total_multas"] == 2
    assert len(dados["multas"]) == 2

def test_top_5_condutores_ranking(temp_multas_db: MultasDB):
    mock_node = MagicMock()
    service = MultasService(node=mock_node, db=temp_multas_db)

    # Cria multas para várias placas
    temp_multas_db.lancar(2026, "Multa P1", 35, "PLACA1") # Dono: 111 (35 pts)
    temp_multas_db.lancar(2026, "Multa P2", 28, "PLACA2") # Dono: 222 (28 pts)
    temp_multas_db.lancar(2026, "Multa P3", 21, "PLACA3") # Dono: 333 (21 pts)
    temp_multas_db.lancar(2026, "Multa P4", 17, "PLACA4") # Dono: 444 (17 pts)
    temp_multas_db.lancar(2026, "Multa P5", 12, "PLACA5") # Dono: 555 (12 pts)
    temp_multas_db.lancar(2026, "Multa P6", 5,  "PLACA6") # Dono: 666 (5 pts)

    def mock_request(req_topic, resp_topic, dados, **kwargs):
        if req_topic == topics.VEICULO_LISTAR_PROPRIETARIOS:
            return {
                "sucesso": True,
                "dados": [
                    {"placa": "PLACA1", "cpf_condutor": "111"},
                    {"placa": "PLACA2", "cpf_condutor": "222"},
                    {"placa": "PLACA3", "cpf_condutor": "333"},
                    {"placa": "PLACA4", "cpf_condutor": "444"},
                    {"placa": "PLACA5", "cpf_condutor": "555"},
                    {"placa": "PLACA6", "cpf_condutor": "666"},
                ]
            }
        elif req_topic == topics.CONDUTOR_OBTER:
            nomes = {
                "111": "João da Silva",
                "222": "Maria Santos",
                "333": "Pedro Souza",
                "444": "Ana Oliveira",
                "555": "Carlos Lima",
                "666": "Fernanda Costa"
            }
            cpf = dados.get("cpf")
            return {"sucesso": True, "dados": {"cpf": cpf, "nome": nomes.get(cpf, "Desconhecido")}}
        return {"sucesso": False}

    mock_node.request.side_effect = mock_request

    sucesso, msg, ranking = service.handle_top_5({})
    assert sucesso is True
    assert len(ranking) == 5 # Máximo 5 condutores

    # Validação da ordem decrescente
    assert ranking[0]["nome"] == "João da Silva"
    assert ranking[0]["pontuacao_total"] == 35
    assert ranking[1]["nome"] == "Maria Santos"
    assert ranking[1]["pontuacao_total"] == 28
    assert ranking[2]["nome"] == "Pedro Souza"
    assert ranking[2]["pontuacao_total"] == 21
    assert ranking[3]["nome"] == "Ana Oliveira"
    assert ranking[3]["pontuacao_total"] == 17
    assert ranking[4]["nome"] == "Carlos Lima"
    assert ranking[4]["pontuacao_total"] == 12
