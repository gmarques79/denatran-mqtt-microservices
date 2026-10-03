"""
Testes unitários para o Microsserviço de Condutores.
"""
from unittest.mock import MagicMock
from services.condutores.database import CondutoresDB
from services.condutores.service import CondutoresService

def test_cadastro_valido(temp_condutores_db: CondutoresDB):
    sucesso, msg, dados = temp_condutores_db.cadastrar("12345678900", "João da Silva")
    assert sucesso is True
    assert "sucesso" in msg.lower()
    assert dados["cpf"] == "12345678900"
    assert dados["nome"] == "João da Silva"

def test_cpf_duplicado(temp_condutores_db: CondutoresDB):
    temp_condutores_db.cadastrar("12345678900", "João da Silva")
    sucesso, msg, dados = temp_condutores_db.cadastrar("12345678900", "Outro Nome")
    assert sucesso is False
    assert "já cadastrado" in msg.lower()
    assert dados is None

def test_condutor_inexistente(temp_condutores_db: CondutoresDB):
    condutor = temp_condutores_db.obter("99999999999")
    assert condutor is None

def test_validacao_campos_vazios(temp_condutores_db: CondutoresDB):
    # CPF vazio
    sucesso, msg, _ = temp_condutores_db.cadastrar("", "Maria Santos")
    assert sucesso is False
    assert "cpf" in msg.lower()

    # Nome vazio
    sucesso, msg, _ = temp_condutores_db.cadastrar("12345678900", "")
    assert sucesso is False
    assert "nome" in msg.lower()

def test_listar_condutores(temp_condutores_db: CondutoresDB):
    temp_condutores_db.cadastrar("111", "Ana")
    temp_condutores_db.cadastrar("222", "Carlos")
    lista = temp_condutores_db.listar()
    assert len(lista) == 2
    assert lista[0]["nome"] == "Ana"

def test_service_handlers(temp_condutores_db: CondutoresDB):
    mock_node = MagicMock()
    service = CondutoresService(node=mock_node, db=temp_condutores_db)

    # Cadastro via handler
    sucesso, msg, dados = service.handle_cadastrar({"cpf": "333", "nome": "Roberto"})
    assert sucesso is True

    # Obter via handler
    sucesso, msg, dados = service.handle_obter({"cpf": "333"})
    assert sucesso is True
    assert dados["nome"] == "Roberto"

    # Obter inexistente via handler
    sucesso, msg, dados = service.handle_obter({"cpf": "000"})
    assert sucesso is False

    # Transferir quando novo condutor não existe
    sucesso, msg, dados = service.handle_transferir({"placa": "ABC1D23", "novo_cpf": "999"})
    assert sucesso is False
    assert "não está cadastrado" in msg.lower()
