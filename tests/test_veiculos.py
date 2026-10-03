"""
Testes unitários para o Microsserviço de Veículos.
"""
from unittest.mock import MagicMock
from services.veiculos.database import VeiculosDB
from services.veiculos.service import VeiculosService

def test_emplacamento_valido(temp_veiculos_db: VeiculosDB):
    sucesso, msg, dados = temp_veiculos_db.emplacar(
        placa="ABC1D23",
        modelo="Fiat Uno",
        valor=50000.0,
        cpf_condutor="12345678900",
        data_emplacamento="2026-03-15"
    )
    assert sucesso is True
    assert "sucesso" in msg.lower()
    assert dados["placa"] == "ABC1D23"
    assert dados["valor"] == 50000.0

def test_placa_duplicada(temp_veiculos_db: VeiculosDB):
    temp_veiculos_db.emplacar("ABC1D23", "Fiat Uno", 50000.0, "12345678900", "2026-03-15")
    sucesso, msg, dados = temp_veiculos_db.emplacar("ABC1D23", "Outro Carro", 60000.0, "99999999900", "2026-04-10")
    assert sucesso is False
    assert "já emplacado" in msg.lower()
    assert dados is None

def test_calculo_ipva(temp_veiculos_db: VeiculosDB):
    # R$ 50.000,00 * 0.02 = R$ 1.000,00
    temp_veiculos_db.emplacar("ABC1D23", "Fiat Uno", 50000.0, "12345678900", "2026-03-15")
    sucesso, msg, dados = temp_veiculos_db.calcular_ipva("ABC1D23")
    assert sucesso is True
    assert dados["valor_veiculo"] == 50000.0
    assert dados["aliquota"] == 0.02
    assert dados["valor_ipva"] == 1000.0

    # R$ 75.450,00 * 0.02 = R$ 1.509,00
    temp_veiculos_db.emplacar("XYZ9999", "Sedan Luxo", 75450.0, "12345678900", "2026-05-20")
    sucesso, msg, dados = temp_veiculos_db.calcular_ipva("XYZ9999")
    assert sucesso is True
    assert dados["valor_ipva"] == 1509.0

def test_ipva_veiculo_inexistente(temp_veiculos_db: VeiculosDB):
    sucesso, msg, dados = temp_veiculos_db.calcular_ipva("NAOEXISTE")
    assert sucesso is False
    assert "não encontrado" in msg.lower()

def test_transferencia_proprietario(temp_veiculos_db: VeiculosDB):
    temp_veiculos_db.emplacar("ABC1D23", "Fiat Uno", 50000.0, "111", "2026-01-01")
    sucesso, msg, dados = temp_veiculos_db.atualizar_proprietario("ABC1D23", "222")
    assert sucesso is True
    assert dados["cpf_condutor"] == "222"

    veiculo = temp_veiculos_db.obter("ABC1D23")
    assert veiculo["cpf_condutor"] == "222"

def test_consulta_veiculos_por_ano(temp_veiculos_db: VeiculosDB):
    temp_veiculos_db.emplacar("CAR2025", "Carro 2025", 30000.0, "111", "2025-05-10")
    temp_veiculos_db.emplacar("CAR2026A", "Carro 2026 A", 40000.0, "111", "2026-01-15")
    temp_veiculos_db.emplacar("CAR2026B", "Carro 2026 B", 50000.0, "222", "2026-07-20")

    lista_2026 = temp_veiculos_db.listar_por_ano(2026)
    assert len(lista_2026) == 2
    placas = [v["placa"] for v in lista_2026]
    assert "CAR2026A" in placas
    assert "CAR2026B" in placas
    assert "CAR2025" not in placas

    lista_2025 = temp_veiculos_db.listar_por_ano(2025)
    assert len(lista_2025) == 1
    assert lista_2025[0]["placa"] == "CAR2025"

def test_validacoes_campos_veiculo(temp_veiculos_db: VeiculosDB):
    # Placa vazia
    sucesso, msg, _ = temp_veiculos_db.emplacar("", "Modelo", 1000.0, "111")
    assert sucesso is False
    assert "placa" in msg.lower()

    # Modelo vazio
    sucesso, msg, _ = temp_veiculos_db.emplacar("ABC1111", "", 1000.0, "111")
    assert sucesso is False
    assert "modelo" in msg.lower()

    # Valor negativo
    sucesso, msg, _ = temp_veiculos_db.emplacar("ABC1111", "Modelo", -500.0, "111")
    assert sucesso is False
    assert "negativo" in msg.lower()

    # CPF vazio
    sucesso, msg, _ = temp_veiculos_db.emplacar("ABC1111", "Modelo", 1000.0, "")
    assert sucesso is False
    assert "cpf" in msg.lower()

def test_service_validacao_condutor_mqtt(temp_veiculos_db: VeiculosDB):
    mock_node = MagicMock()
    service = VeiculosService(node=mock_node, db=temp_veiculos_db)

    # 1. Simula condutor NÃO encontrado via MQTT
    mock_node.request.return_value = {"sucesso": False, "mensagem": "Condutor não encontrado"}
    sucesso, msg, dados = service.handle_emplacar({
        "placa": "TST0001",
        "modelo": "Fusca",
        "valor": 15000.0,
        "cpf_condutor": "99999999999"
    })
    assert sucesso is False
    assert "cadastre o condutor antes" in msg.lower()

    # 2. Simula condutor encontrado via MQTT
    mock_node.request.return_value = {"sucesso": True, "dados": {"cpf": "111", "nome": "João"}}
    sucesso, msg, dados = service.handle_emplacar({
        "placa": "TST0001",
        "modelo": "Fusca",
        "valor": 15000.0,
        "cpf_condutor": "111"
    })
    assert sucesso is True
    assert dados["placa"] == "TST0001"
