"""
Camada de persistência SQLite para o Microsserviço de Veículos.
"""
import os
import sqlite3
import threading
from datetime import date
from typing import Optional, Dict, Any, List, Tuple

class VeiculosDB:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "veiculos.db")

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
                    CREATE TABLE IF NOT EXISTS veiculos (
                        placa TEXT PRIMARY KEY,
                        modelo TEXT NOT NULL,
                        valor REAL NOT NULL,
                        cpf_condutor TEXT NOT NULL,
                        data_emplacamento TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def emplacar(
        self,
        placa: str,
        modelo: str,
        valor: float,
        cpf_condutor: str,
        data_emplacamento: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        placa = str(placa).strip().upper()
        modelo = str(modelo).strip()
        cpf_condutor = str(cpf_condutor).strip()

        if not placa:
            return False, "Placa não pode ser vazia.", None
        if not modelo:
            return False, "Modelo não pode ser vazio.", None
        if valor < 0:
            return False, "Valor do veículo não pode ser negativo.", None
        if not cpf_condutor:
            return False, "CPF do condutor não pode ser vazio.", None

        if not data_emplacamento:
            data_emplacamento = date.today().isoformat()
        else:
            data_emplacamento = str(data_emplacamento).strip()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT placa FROM veiculos WHERE placa = ?", (placa,))
                if cursor.fetchone():
                    return False, f"Veículo com placa {placa} já emplacado.", None

                cursor.execute(
                    """
                    INSERT INTO veiculos (placa, modelo, valor, cpf_condutor, data_emplacamento)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (placa, modelo, valor, cpf_condutor, data_emplacamento)
                )
                conn.commit()
                return True, "Veículo emplacado com sucesso.", {
                    "placa": placa,
                    "modelo": modelo,
                    "valor": valor,
                    "cpf_condutor": cpf_condutor,
                    "data_emplacamento": data_emplacamento
                }
            except sqlite3.IntegrityError:
                return False, f"Veículo com placa {placa} já emplacado.", None
            except Exception as e:
                return False, f"Erro ao acessar banco de dados: {str(e)}", None
            finally:
                conn.close()

    def obter(self, placa: str) -> Optional[Dict[str, Any]]:
        placa = str(placa).strip().upper()
        if not placa:
            return None

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT placa, modelo, valor, cpf_condutor, data_emplacamento FROM veiculos WHERE placa = ?",
                    (placa,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
            finally:
                conn.close()

    def calcular_ipva(self, placa: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        placa = str(placa).strip().upper()
        veiculo = self.obter(placa)
        if not veiculo:
            return False, f"Veículo com placa {placa} não encontrado.", None

        aliquota = 0.02
        valor_ipva = round(veiculo["valor"] * aliquota, 2)
        resultado = {
            "placa": placa,
            "modelo": veiculo["modelo"],
            "valor_veiculo": veiculo["valor"],
            "aliquota": aliquota,
            "aliquota_percentual": "2%",
            "valor_ipva": valor_ipva
        }
        return True, "IPVA calculado com sucesso.", resultado

    def atualizar_proprietario(self, placa: str, novo_cpf: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        placa = str(placa).strip().upper()
        novo_cpf = str(novo_cpf).strip()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT placa, modelo, valor, data_emplacamento FROM veiculos WHERE placa = ?", (placa,))
                veiculo = cursor.fetchone()
                if not veiculo:
                    return False, f"Veículo com placa {placa} não encontrado.", None

                cursor.execute(
                    "UPDATE veiculos SET cpf_condutor = ? WHERE placa = ?",
                    (novo_cpf, placa)
                )
                conn.commit()
                return True, f"Proprietário do veículo {placa} atualizado com sucesso.", {
                    "placa": placa,
                    "modelo": veiculo["modelo"],
                    "cpf_condutor": novo_cpf
                }
            finally:
                conn.close()

    def listar_por_ano(self, ano: int) -> List[Dict[str, Any]]:
        ano_str = str(ano).strip()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT placa, modelo, valor, cpf_condutor, data_emplacamento
                    FROM veiculos
                    WHERE substr(data_emplacamento, 1, 4) = ?
                    ORDER BY data_emplacamento ASC, placa ASC
                    """,
                    (ano_str,)
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def listar_por_condutor(self, cpf: str) -> List[Dict[str, Any]]:
        cpf = str(cpf).strip()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT placa, modelo, valor, cpf_condutor, data_emplacamento FROM veiculos WHERE cpf_condutor = ?",
                    (cpf,)
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def listar_proprietarios(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT placa, cpf_condutor FROM veiculos")
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
