"""
Teste completo de integração fim a fim (E2E) via MQTT.
Demonstra a comunicação distribuída entre todos os microsserviços do sistema DENATRAN.
"""
import time
import pytest
from common.messaging import MQTTNode
from common import topics
from services.condutores.service import CondutoresService
from services.veiculos.service import VeiculosService
from services.multas.service import MultasService
from services.condutores.database import CondutoresDB
from services.veiculos.database import VeiculosDB
from services.multas.database import MultasDB

@pytest.fixture(scope="module")
def running_services(tmp_path_factory):
    # Cria diretórios temporários para isolamento dos bancos de teste
    temp_dir = tmp_path_factory.mktemp("integ_data")
    cond_db = CondutoresDB(db_path=str(temp_dir / "condutores.db"))
    veic_db = VeiculosDB(db_path=str(temp_dir / "veiculos.db"))
    mult_db = MultasDB(db_path=str(temp_dir / "multas.db"))

    # Inicia os nós MQTT para cada microsserviço com isolamento de tópico
    node_cond = MQTTNode("CONDUTORES-IT", topic_prefix="integ/")
    service_cond = CondutoresService(node=node_cond, db=cond_db)
    node_cond.start()

    node_veic = MQTTNode("VEICULOS-IT", topic_prefix="integ/")
    service_veic = VeiculosService(node=node_veic, db=veic_db)
    node_veic.start()

    node_mult = MQTTNode("MULTAS-IT", topic_prefix="integ/")
    service_mult = MultasService(node=node_mult, db=mult_db)
    node_mult.start()

    # Inicia nó do cliente
    node_client = MQTTNode("CLIENTE-IT", topic_prefix="integ/")
    node_client.start()

    time.sleep(1.0) # Aguarda inscrições MQTT propagarem

    yield node_client

    # Encerra os nós
    node_client.stop()
    node_mult.stop()
    node_veic.stop()
    node_cond.stop()

def test_fluxo_completo_integracao(running_services):
    client: MQTTNode = running_services

    # 1. Cadastrar condutor João
    resp = client.request(
        topics.CONDUTOR_CADASTRAR,
        topics.CONDUTOR_CADASTRAR_RESPOSTA,
        {"cpf": "12345678900", "nome": "João da Silva"}
    )
    assert resp["sucesso"] is True, resp["mensagem"]
    assert resp["dados"]["cpf"] == "12345678900"

    # 2. Cadastrar condutora Maria
    resp = client.request(
        topics.CONDUTOR_CADASTRAR,
        topics.CONDUTOR_CADASTRAR_RESPOSTA,
        {"cpf": "98765432100", "nome": "Maria Santos"}
    )
    assert resp["sucesso"] is True, resp["mensagem"]

    # 3. Tentar emplacar veículo com condutor inexistente (deve falhar via validação MQTT)
    resp = client.request(
        topics.VEICULO_EMPLACAR,
        topics.VEICULO_EMPLACAR_RESPOSTA,
        {
            "placa": "ERR0001",
            "modelo": "Carro Fantasma",
            "valor": 40000.0,
            "cpf_condutor": "00000000000"
        }
    )
    assert resp["sucesso"] is False
    assert "não encontrado" in resp["mensagem"].lower()

    # 4. Emplacar veículo ABC1D23 para João
    resp = client.request(
        topics.VEICULO_EMPLACAR,
        topics.VEICULO_EMPLACAR_RESPOSTA,
        {
            "placa": "ABC1D23",
            "modelo": "Fiat Uno",
            "valor": 50000.0,
            "cpf_condutor": "12345678900",
            "data_emplacamento": "2026-03-15"
        }
    )
    assert resp["sucesso"] is True, resp["mensagem"]
    assert resp["dados"]["placa"] == "ABC1D23"

    # 5. Emplacar veículo XYZ9999 para Maria
    resp = client.request(
        topics.VEICULO_EMPLACAR,
        topics.VEICULO_EMPLACAR_RESPOSTA,
        {
            "placa": "XYZ9999",
            "modelo": "VW Gol",
            "valor": 60000.0,
            "cpf_condutor": "98765432100",
            "data_emplacamento": "2026-06-20"
        }
    )
    assert resp["sucesso"] is True, resp["mensagem"]

    # 6. Calcular IPVA do veículo ABC1D23 (50000 * 0.02 = 1000)
    resp = client.request(
        topics.VEICULO_IPVA,
        topics.VEICULO_IPVA_RESPOSTA,
        {"placa": "ABC1D23"}
    )
    assert resp["sucesso"] is True
    assert resp["dados"]["valor_ipva"] == 1000.0
    assert resp["dados"]["aliquota"] == 0.02

    # 7. Tentar lançar multa em veículo inexistente (deve falhar via validação MQTT)
    resp = client.request(
        topics.MULTA_LANCAR,
        topics.MULTA_LANCAR_RESPOSTA,
        {
            "ano": 2026,
            "descricao": "Infração Inválida",
            "pontuacao": 3,
            "placa": "NAOEXISTE"
        }
    )
    assert resp["sucesso"] is False
    assert "não encontrado" in resp["mensagem"].lower()

    # 8. Lançar multas no veículo ABC1D23
    resp1 = client.request(
        topics.MULTA_LANCAR,
        topics.MULTA_LANCAR_RESPOSTA,
        {
            "ano": 2026,
            "descricao": "Excesso de velocidade",
            "pontuacao": 5,
            "placa": "ABC1D23"
        }
    )
    assert resp1["sucesso"] is True

    resp2 = client.request(
        topics.MULTA_LANCAR,
        topics.MULTA_LANCAR_RESPOSTA,
        {
            "ano": 2026,
            "descricao": "Avanço de sinal vermelho",
            "pontuacao": 7,
            "placa": "ABC1D23"
        }
    )
    assert resp2["sucesso"] is True

    # 9. Lançar multa no veículo XYZ9999
    resp3 = client.request(
        topics.MULTA_LANCAR,
        topics.MULTA_LANCAR_RESPOSTA,
        {
            "ano": 2026,
            "descricao": "Estacionar em vaga especial",
            "pontuacao": 4,
            "placa": "XYZ9999"
        }
    )
    assert resp3["sucesso"] is True

    # 10. Consultar multas do veículo ABC1D23 em 2026 (deve exibir dados do condutor via MQTT)
    resp = client.request(
        topics.MULTA_POR_VEICULO,
        topics.MULTA_POR_VEICULO_RESPOSTA,
        {"placa": "ABC1D23", "ano": 2026}
    )
    assert resp["sucesso"] is True
    dados = resp["dados"]
    assert dados["placa"] == "ABC1D23"
    assert dados["ano"] == 2026
    assert dados["condutor"]["cpf"] == "12345678900"
    assert dados["condutor"]["nome"] == "João da Silva"
    assert len(dados["multas"]) == 2
    total_pontos = sum(m["pontuacao"] for m in dados["multas"])
    assert total_pontos == 12

    # 11. Consultar multas do condutor João em 2026
    resp = client.request(
        topics.MULTA_POR_CONDUTOR,
        topics.MULTA_POR_CONDUTOR_RESPOSTA,
        {"cpf": "12345678900", "ano": 2026}
    )
    assert resp["sucesso"] is True
    assert resp["dados"]["nome"] == "João da Silva"
    assert resp["dados"]["total_pontos"] == 12
    assert len(resp["dados"]["multas"]) == 2

    # 12. Consultar multas lançadas no ano 2026
    resp = client.request(
        topics.MULTA_POR_ANO,
        topics.MULTA_POR_ANO_RESPOSTA,
        {"ano": 2026}
    )
    assert resp["sucesso"] is True
    assert resp["dados"]["total_multas"] == 3

    # 13. Consultar veículos emplacados em 2026
    resp = client.request(
        topics.VEICULO_LISTAR_POR_ANO,
        topics.VEICULO_LISTAR_POR_ANO_RESPOSTA,
        {"ano": 2026}
    )
    assert resp["sucesso"] is True
    placas_2026 = [v["placa"] for v in resp["dados"]]
    assert "ABC1D23" in placas_2026
    assert "XYZ9999" in placas_2026

    # 14. Transferir proprietário de ABC1D23 para Maria Santos
    resp = client.request(
        topics.CONDUTOR_TRANSFERIR,
        topics.CONDUTOR_TRANSFERIR_RESPOSTA,
        {"placa": "ABC1D23", "novo_cpf": "98765432100"}
    )
    assert resp["sucesso"] is True
    assert "transferido com sucesso" in resp["mensagem"].lower()

    # 15. Consultar multas do veículo ABC1D23 após transferência (agora condutor deve ser Maria)
    resp = client.request(
        topics.MULTA_POR_VEICULO,
        topics.MULTA_POR_VEICULO_RESPOSTA,
        {"placa": "ABC1D23", "ano": 2026}
    )
    assert resp["sucesso"] is True
    assert resp["dados"]["condutor"]["cpf"] == "98765432100"
    assert resp["dados"]["condutor"]["nome"] == "Maria Santos"

    # 16. Consultar ranking dos Top 5 condutores
    resp = client.request(
        topics.MULTA_TOP_5,
        topics.MULTA_TOP_5_RESPOSTA,
        {}
    )
    assert resp["sucesso"] is True
    ranking = resp["dados"]
    assert len(ranking) >= 1
    # Maria agora possui ABC1D23 (12 pts) + XYZ9999 (4 pts) = 16 pts
    assert ranking[0]["cpf"] == "98765432100"
    assert ranking[0]["pontuacao_total"] == 16
    assert ranking[0]["nome"] == "Maria Santos"
