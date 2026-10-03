"""
Camada de persistência SQLite para o Microsserviço de Condutores.
"""
import os
import sqlite3
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

class CondutoresDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "condutores.db")

        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS condutores (
                        cpf TEXT PRIMARY KEY,
                        nome TEXT NOT NULL,
                        criado_em TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def cadastrar(self, cpf: str, nome: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        cpf = str(cpf).strip()
        nome = str(nome).strip()

        if not cpf:
            return False, "CPF não pode ser vazio.", None
        if not nome:
            return False, "Nome não pode ser vazio.", None

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT cpf FROM condutores WHERE cpf = ?", (cpf,))
                if cursor.fetchone():
                    return False, f"Condutor com CPF {cpf} já cadastrado.", None

                criado_em = datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO condutores (cpf, nome, criado_em) VALUES (?, ?, ?)",
                    (cpf, nome, criado_em)
                )
                conn.commit()
                return True, "Condutor cadastrado com sucesso.", {
                    "cpf": cpf,
                    "nome": nome,
                    "criado_em": criado_em
                }
            except sqlite3.IntegrityError:
                return False, f"Condutor com CPF {cpf} já cadastrado.", None
            except Exception as e:
                return False, f"Erro ao acessar banco de dados: {str(e)}", None
            finally:
                conn.close()

    def obter(self, cpf: str) -> Optional[Dict[str, Any]]:
        cpf = str(cpf).strip()
        if not cpf:
            return None

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT cpf, nome, criado_em FROM condutores WHERE cpf = ?", (cpf,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
            finally:
                conn.close()

    def listar(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT cpf, nome, criado_em FROM condutores ORDER BY nome ASC")
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
