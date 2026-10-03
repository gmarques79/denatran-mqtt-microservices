"""
Camada de persistência SQLite para o Microsserviço de Multas.
"""
import os
import sqlite3
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

class MultasDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "multas.db")

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
                    CREATE TABLE IF NOT EXISTS multas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ano INTEGER NOT NULL,
                        descricao TEXT NOT NULL,
                        pontuacao INTEGER NOT NULL,
                        placa TEXT NOT NULL,
                        criado_em TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def lancar(
        self,
        ano: int,
        descricao: str,
        pontuacao: int,
        placa: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        placa = str(placa).strip().upper()
        descricao = str(descricao).strip()

        if not placa:
            return False, "Placa não pode ser vazia.", None
        if not descricao:
            return False, "Descrição da multa não pode ser vazia.", None
        if pontuacao < 0:
            return False, "Pontuação não pode ser negativa.", None
        if ano < 1900 or ano > 2100:
            return False, "Ano inválido.", None

        criado_em = datetime.now().isoformat()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO multas (ano, descricao, pontuacao, placa, criado_em)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ano, descricao, pontuacao, placa, criado_em)
                )
                multa_id = cursor.lastrowid
                conn.commit()
                return True, "Multa lançada com sucesso.", {
                    "id": multa_id,
                    "ano": ano,
                    "descricao": descricao,
                    "pontuacao": pontuacao,
                    "placa": placa,
                    "criado_em": criado_em
                }
            except Exception as e:
                return False, f"Erro ao acessar banco de dados de multas: {str(e)}", None
            finally:
                conn.close()

    def listar_por_veiculo_ano(self, placa: str, ano: int) -> List[Dict[str, Any]]:
        placa = str(placa).strip().upper()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, descricao, pontuacao
                    FROM multas
                    WHERE placa = ? AND ano = ?
                    ORDER BY id ASC
                    """,
                    (placa, ano)
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def listar_por_placas_ano(self, placas: List[str], ano: int) -> List[Dict[str, Any]]:
        if not placas:
            return []

        placas_limpas = [str(p).strip().upper() for p in placas if str(p).strip()]
        if not placas_limpas:
            return []

        placeholders = ",".join("?" for _ in placas_limpas)
        params = list(placas_limpas) + [ano]

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, ano, descricao, pontuacao, placa, criado_em
                    FROM multas
                    WHERE placa IN ({placeholders}) AND ano = ?
                    ORDER BY id ASC
                    """,
                    params
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def listar_por_ano(self, ano: int) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, ano, descricao, pontuacao, placa, criado_em
                    FROM multas
                    WHERE ano = ?
                    ORDER BY id ASC
                    """,
                    (ano,)
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def total_pontos_por_placa(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT placa, SUM(pontuacao) AS total_pontos
                    FROM multas
                    GROUP BY placa
                    ORDER BY total_pontos DESC
                    """
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
