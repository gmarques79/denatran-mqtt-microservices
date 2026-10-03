"""
Configurações e fixtures para o pytest.
"""
import os
import sys
import gc
import tempfile
import pytest

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.condutores.database import CondutoresDB
from services.veiculos.database import VeiculosDB
from services.multas.database import MultasDB

def _safe_remove(path: str):
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

@pytest.fixture
def temp_condutores_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = CondutoresDB(db_path=db_path)
    yield db
    _safe_remove(db_path)

@pytest.fixture
def temp_veiculos_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = VeiculosDB(db_path=db_path)
    yield db
    _safe_remove(db_path)

@pytest.fixture
def temp_multas_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = MultasDB(db_path=db_path)
    yield db
    _safe_remove(db_path)
