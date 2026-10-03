"""
Cliente de Linha de Comando (CLI) para o sistema DENATRAN.
Comunicação 100% via MQTT utilizando modelo Publish/Subscribe.
"""
import sys
import os
import time

# Garante que o diretório raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.messaging import MQTTNode
from common import topics

def format_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class DenatranCLI:
    def __init__(self):
        self.node = MQTTNode("CLIENTE")

    def start(self):
        print("\n[CLIENTE] Conectando ao broker MQTT...")
        try:
            self.node.start()
            print("[CLIENTE] Conexão estabelecida com sucesso!\n")
        except Exception as e:
            print(f"[CLIENTE] Falha ao conectar ao broker MQTT: {e}")
            sys.exit(1)

    def close(self):
        self.node.stop()

    def cadastrar_condutor(self):
        print("\n--- 1. CADASTRAR CONDUTOR ---")
        cpf = input("Digite o CPF (somente números): ").strip()
        nome = input("Digite o nome completo: ").strip()

        if not cpf or not nome:
            print("❌ Erro: CPF e Nome são obrigatórios.")
            return

        payload = {"cpf": cpf, "nome": nome}
        resp = self.node.request(topics.CONDUTOR_CADASTRAR, topics.CONDUTOR_CADASTRAR_RESPOSTA, payload)

        if resp.get("sucesso"):
            print(f"✅ {resp.get('mensagem')}")
            dados = resp.get("dados") or {}
            print(f"   Nome: {dados.get('nome')} | CPF: {dados.get('cpf')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def emplacar_veiculo(self):
        print("\n--- 2. EMPLACAR VEÍCULO ---")
        placa = input("Placa (ex: ABC1D23): ").strip().upper()
        modelo = input("Modelo (ex: Toyota Corolla): ").strip()
        valor_str = input("Valor do veículo (ex: 75000.00): ").strip()
        cpf_condutor = input("CPF do condutor proprietário: ").strip()
        data_emplacamento = input("Data de emplacamento (AAAA-MM-DD, deixe vazio para hoje): ").strip()

        try:
            valor = float(valor_str)
        except ValueError:
            print("❌ Erro: Valor deve ser um número válido.")
            return

        payload = {
            "placa": placa,
            "modelo": modelo,
            "valor": valor,
            "cpf_condutor": cpf_condutor
        }
        if data_emplacamento:
            payload["data_emplacamento"] = data_emplacamento

        resp = self.node.request(topics.VEICULO_EMPLACAR, topics.VEICULO_EMPLACAR_RESPOSTA, payload)

        if resp.get("sucesso"):
            print(f"✅ {resp.get('mensagem')}")
            d = resp.get("dados") or {}
            print(f"   Placa: {d.get('placa')} | Modelo: {d.get('modelo')} | Valor: {format_moeda(d.get('valor', 0))} | Condutor: {d.get('cpf_condutor')} | Data: {d.get('data_emplacamento')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def calcular_ipva(self):
        print("\n--- 3. CALCULAR IPVA ---")
        placa = input("Placa do veículo: ").strip().upper()
        if not placa:
            print("❌ Erro: Placa é obrigatória.")
            return

        resp = self.node.request(topics.VEICULO_IPVA, topics.VEICULO_IPVA_RESPOSTA, {"placa": placa})

        if resp.get("sucesso"):
            d = resp.get("dados") or {}
            print(f"✅ {resp.get('mensagem')}")
            print(f"   Placa: {d.get('placa')} ({d.get('modelo')})")
            print(f"   Valor venal: {format_moeda(d.get('valor_veiculo', 0))}")
            print(f"   Alíquota: {d.get('aliquota_percentual', '2%')}")
            print(f"   IPVA a pagar: {format_moeda(d.get('valor_ipva', 0))}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def transferir_proprietario(self):
        print("\n--- 4. TRANSFERIR PROPRIETÁRIO ---")
        placa = input("Placa do veículo a ser transferido: ").strip().upper()
        novo_cpf = input("CPF do novo proprietário: ").strip()

        if not placa or not novo_cpf:
            print("❌ Erro: Placa e CPF do novo proprietário são obrigatórios.")
            return

        payload = {"placa": placa, "novo_cpf": novo_cpf}
        resp = self.node.request(topics.CONDUTOR_TRANSFERIR, topics.CONDUTOR_TRANSFERIR_RESPOSTA, payload)

        if resp.get("sucesso"):
            print(f"✅ {resp.get('mensagem')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def lancar_multa(self):
        print("\n--- 5. LANÇAR MULTA ---")
        placa = input("Placa do veículo multado: ").strip().upper()
        ano_str = input("Ano da infração (ex: 2026): ").strip()
        descricao = input("Descrição da infração (ex: Avanço de sinal vermelho): ").strip()
        pontuacao_str = input("Pontuação da multa (ex: 7): ").strip()

        try:
            ano = int(ano_str)
            pontuacao = int(pontuacao_str)
        except ValueError:
            print("❌ Erro: Ano e pontuação devem ser números inteiros.")
            return

        payload = {
            "placa": placa,
            "ano": ano,
            "descricao": descricao,
            "pontuacao": pontuacao
        }
        resp = self.node.request(topics.MULTA_LANCAR, topics.MULTA_LANCAR_RESPOSTA, payload)

        if resp.get("sucesso"):
            d = resp.get("dados") or {}
            print(f"✅ {resp.get('mensagem')}")
            print(f"   ID: #{d.get('id')} | Placa: {d.get('placa')} | Pontos: {d.get('pontuacao')} | Descrição: {d.get('descricao')} | Ano: {d.get('ano')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def veiculos_por_ano(self):
        print("\n--- 6. VEÍCULOS EMPLACADOS POR ANO ---")
        ano_str = input("Informe o ano (ex: 2026): ").strip()
        try:
            ano = int(ano_str)
        except ValueError:
            print("❌ Erro: Ano deve ser um número inteiro.")
            return

        resp = self.node.request(topics.VEICULO_LISTAR_POR_ANO, topics.VEICULO_LISTAR_POR_ANO_RESPOSTA, {"ano": ano})

        if resp.get("sucesso"):
            veiculos = resp.get("dados") or []
            print(f"\n✅ {resp.get('mensagem')}")
            if not veiculos:
                print("   Nenhum veículo encontrado para este ano.")
            else:
                print(f"   {'PLACA':<10} | {'MODELO':<20} | {'VALOR':<15} | {'CPF CONDUTOR':<14} | {'DATA'}")
                print("   " + "-" * 75)
                for v in veiculos:
                    print(f"   {v.get('placa'):<10} | {v.get('modelo'):<20} | {format_moeda(v.get('valor', 0)):<15} | {v.get('cpf_condutor'):<14} | {v.get('data_emplacamento')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def multas_veiculo_ano(self):
        print("\n--- 7. MULTAS DE UM VEÍCULO EM UM ANO ---")
        placa = input("Placa do veículo: ").strip().upper()
        ano_str = input("Ano da consulta: ").strip()

        try:
            ano = int(ano_str)
        except ValueError:
            print("❌ Erro: Ano deve ser um número inteiro.")
            return

        payload = {"placa": placa, "ano": ano}
        resp = self.node.request(topics.MULTA_POR_VEICULO, topics.MULTA_POR_VEICULO_RESPOSTA, payload)

        if resp.get("sucesso"):
            d = resp.get("dados") or {}
            condutor = d.get("condutor") or {}
            multas = d.get("multas") or []

            print(f"\n✅ Consulta de Multas - Veículo {d.get('placa')} (Ano {d.get('ano')})")
            print(f"   Condutor Responsável: {condutor.get('nome')} (CPF: {condutor.get('cpf')})")
            print(f"   Total de infrações: {len(multas)}")

            if not multas:
                print("   Nenhuma multa registrada neste ano para este veículo.")
            else:
                print("\n   Infrações registradas:")
                total_pts = sum(m.get("pontuacao", 0) for m in multas)
                for m in multas:
                    print(f"   - [ID #{m.get('id')}] {m.get('descricao')} ({m.get('pontuacao')} pontos)")
                print(f"   Total de pontos acumulados: {total_pts}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def multas_condutor_ano(self):
        print("\n--- 8. MULTAS DE UM CONDUTOR EM UM ANO ---")
        cpf = input("CPF do condutor: ").strip()
        ano_str = input("Ano da consulta: ").strip()

        try:
            ano = int(ano_str)
        except ValueError:
            print("❌ Erro: Ano deve ser um número inteiro.")
            return

        payload = {"cpf": cpf, "ano": ano}
        resp = self.node.request(topics.MULTA_POR_CONDUTOR, topics.MULTA_POR_CONDUTOR_RESPOSTA, payload)

        if resp.get("sucesso"):
            d = resp.get("dados") or {}
            multas = d.get("multas") or []
            veiculos = d.get("veiculos") or []

            print(f"\n✅ Relatório de Infrações do Condutor")
            print(f"   Nome: {d.get('nome')} | CPF: {d.get('cpf')}")
            print(f"   Ano: {d.get('ano')}")
            print(f"   Veículos associados: {', '.join(veiculos) if veiculos else 'Nenhum'}")
            print(f"   Pontuação acumulada no ano: {d.get('total_pontos', 0)} pontos")

            if not multas:
                print("   Nenhuma multa registrada para os veículos deste condutor no ano informado.")
            else:
                print("\n   Detalhes das multas:")
                for m in multas:
                    print(f"   - [ID #{m.get('id')}] Placa {m.get('placa')}: {m.get('descricao')} ({m.get('pontuacao')} pts)")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def multas_por_ano(self):
        print("\n--- 9. MULTAS LANÇADAS EM UM ANO ---")
        ano_str = input("Ano da consulta: ").strip()

        try:
            ano = int(ano_str)
        except ValueError:
            print("❌ Erro: Ano deve ser um número inteiro.")
            return

        resp = self.node.request(topics.MULTA_POR_ANO, topics.MULTA_POR_ANO_RESPOSTA, {"ano": ano})

        if resp.get("sucesso"):
            d = resp.get("dados") or {}
            multas = d.get("multas") or []
            print(f"\n✅ {resp.get('mensagem')}")
            if not multas:
                print("   Nenhuma multa cadastrada neste ano.")
            else:
                print(f"   {'ID':<5} | {'PLACA':<10} | {'PONTOS':<8} | {'DESCRICAO'}")
                print("   " + "-" * 55)
                for m in multas:
                    print(f"   {m.get('id'):<5} | {m.get('placa'):<10} | {m.get('pontuacao'):<8} | {m.get('descricao')}")
        else:
            print(f"❌ {resp.get('mensagem')}")

    def top_5_condutores(self):
        print("\n--- 10. TOP 5 CONDUTORES COM MAIOR PONTUAÇÃO ---")
        resp = self.node.request(topics.MULTA_TOP_5, topics.MULTA_TOP_5_RESPOSTA, {})

        if resp.get("sucesso"):
            ranking = resp.get("dados") or []
            print(f"\n✅ {resp.get('mensagem')}\n")
            if not ranking:
                print("   Nenhum registro de multas para compor o ranking.")
            else:
                print("=" * 60)
                print(f"{'POS':<5} | {'CONDUTOR':<25} | {'CPF':<15} | {'PONTOS'}")
                print("=" * 60)
                for item in ranking:
                    print(f"{item.get('posicao'):<5} | {item.get('nome'):<25} | {item.get('cpf'):<15} | {item.get('pontuacao_total')} pontos")
                print("=" * 60)
        else:
            print(f"❌ {resp.get('mensagem')}")

    def run_demo(self):
        print("\n" + "=" * 65)
        print("       DEMONSTRAÇÃO COMPLETA DO SISTEMA DENATRAN (MQTT)")
        print("=" * 65)

        print("\n[PASSO 1] Cadastrando condutor João da Silva...")
        r = self.node.request(topics.CONDUTOR_CADASTRAR, topics.CONDUTOR_CADASTRAR_RESPOSTA, {"cpf": "11122233344", "nome": "João da Silva"})
        print(f"Resultado: {r.get('mensagem')}")

        print("\n[PASSO 1.1] Cadastrando condutora Maria Santos...")
        r = self.node.request(topics.CONDUTOR_CADASTRAR, topics.CONDUTOR_CADASTRAR_RESPOSTA, {"cpf": "55566677788", "nome": "Maria Santos"})
        print(f"Resultado: {r.get('mensagem')}")

        print("\n[PASSO 2] Emplacando veículo BRA2E19 (Toyota Corolla) para João...")
        r = self.node.request(topics.VEICULO_EMPLACAR, topics.VEICULO_EMPLACAR_RESPOSTA, {
            "placa": "BRA2E19",
            "modelo": "Toyota Corolla",
            "valor": 120000.0,
            "cpf_condutor": "11122233344",
            "data_emplacamento": "2026-02-10"
        })
        print(f"Resultado: {r.get('mensagem')}")

        print("\n[PASSO 2.1] Emplacando veículo KMI8899 (Honda Civic) para Maria...")
        r = self.node.request(topics.VEICULO_EMPLACAR, topics.VEICULO_EMPLACAR_RESPOSTA, {
            "placa": "KMI8899",
            "modelo": "Honda Civic",
            "valor": 140000.0,
            "cpf_condutor": "55566677788",
            "data_emplacamento": "2026-04-18"
        })
        print(f"Resultado: {r.get('mensagem')}")

        print("\n[PASSO 3] Calculando IPVA do veículo BRA2E19 (Alíquota 2%)...")
        r = self.node.request(topics.VEICULO_IPVA, topics.VEICULO_IPVA_RESPOSTA, {"placa": "BRA2E19"})
        d = r.get("dados", {})
        print(f"Resultado: {r.get('mensagem')}")
        print(f"Veículo: {d.get('placa')} ({d.get('modelo')}) | Valor: {format_moeda(d.get('valor_veiculo', 0))} | IPVA: {format_moeda(d.get('valor_ipva', 0))}")

        print("\n[PASSO 4] Lançando multas...")
        r = self.node.request(topics.MULTA_LANCAR, topics.MULTA_LANCAR_RESPOSTA, {
            "placa": "BRA2E19", "ano": 2026, "descricao": "Excesso de velocidade (> 20%)", "pontuacao": 5
        })
        print(f"Multa 1 (BRA2E19): {r.get('mensagem')}")

        r = self.node.request(topics.MULTA_LANCAR, topics.MULTA_LANCAR_RESPOSTA, {
            "placa": "BRA2E19", "ano": 2026, "descricao": "Avanço de sinal vermelho", "pontuacao": 7
        })
        print(f"Multa 2 (BRA2E19): {r.get('mensagem')}")

        r = self.node.request(topics.MULTA_LANCAR, topics.MULTA_LANCAR_RESPOSTA, {
            "placa": "KMI8899", "ano": 2026, "descricao": "Estacionar em local proibido", "pontuacao": 4
        })
        print(f"Multa 3 (KMI8899): {r.get('mensagem')}")

        print("\n[PASSO 5] Consultando veículos emplacados em 2026...")
        r = self.node.request(topics.VEICULO_LISTAR_POR_ANO, topics.VEICULO_LISTAR_POR_ANO_RESPOSTA, {"ano": 2026})
        print(f"Total encontrados: {len(r.get('dados', []))}")
        for v in r.get("dados", []):
            print(f"  - Placa: {v.get('placa')} | Modelo: {v.get('modelo')} | Dono: {v.get('cpf_condutor')}")

        print("\n[PASSO 6] Consultando multas do veículo BRA2E19 em 2026 (exibindo condutor)...")
        r = self.node.request(topics.MULTA_POR_VEICULO, topics.MULTA_POR_VEICULO_RESPOSTA, {"placa": "BRA2E19", "ano": 2026})
        d = r.get("dados", {})
        cond = d.get("condutor", {})
        print(f"Condutor: {cond.get('nome')} (CPF: {cond.get('cpf')})")
        for m in d.get("multas", []):
            print(f"  - Infrao #{m.get('id')}: {m.get('descricao')} ({m.get('pontuacao')} pts)")

        print("\n[PASSO 7] Consultando multas do condutor João da Silva (CPF: 11122233344) em 2026...")
        r = self.node.request(topics.MULTA_POR_CONDUTOR, topics.MULTA_POR_CONDUTOR_RESPOSTA, {"cpf": "11122233344", "ano": 2026})
        d = r.get("dados", {})
        print(f"Condutor: {d.get('nome')} | Pontos acumulados: {d.get('total_pontos')} | Multas: {d.get('total_multas')}")

        print("\n[PASSO 8] Consultando todas as multas lançadas em 2026...")
        r = self.node.request(topics.MULTA_POR_ANO, topics.MULTA_POR_ANO_RESPOSTA, {"ano": 2026})
        print(f"Total de multas em 2026: {r.get('dados', {}).get('total_multas')}")

        print("\n[PASSO 9] Transferindo proprietário do veículo BRA2E19 de João para Maria...")
        r = self.node.request(topics.CONDUTOR_TRANSFERIR, topics.CONDUTOR_TRANSFERIR_RESPOSTA, {
            "placa": "BRA2E19", "novo_cpf": "55566677788"
        })
        print(f"Resultado: {r.get('mensagem')}")

        print("\n[PASSO 10] Consultando Top 5 condutores com maior pontuação...")
        r = self.node.request(topics.MULTA_TOP_5, topics.MULTA_TOP_5_RESPOSTA, {})
        print("-" * 55)
        for item in r.get("dados", []):
            print(f"{item.get('posicao')}. {item.get('nome')} (CPF: {item.get('cpf')}) — {item.get('pontuacao_total')} pontos")
        print("-" * 55)
        print("\n✅ Demonstração concluída com sucesso!")

    def menu(self):
        while True:
            print("\n" + "=" * 40)
            print("        DENATRAN - SISTEMA")
            print("=" * 40)
            print("1  - Cadastrar condutor")
            print("2  - Emplacar veículo")
            print("3  - Calcular IPVA")
            print("4  - Transferir proprietário")
            print("5  - Lançar multa")
            print("6  - Veículos emplacados por ano")
            print("7  - Multas de um veículo")
            print("8  - Multas de um condutor")
            print("9  - Multas lançadas em um ano")
            print("10 - Top 5 condutores")
            print("0  - Sair")
            print("=" * 40)

            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self.cadastrar_condutor()
            elif opcao == "2":
                self.emplacar_veiculo()
            elif opcao == "3":
                self.calcular_ipva()
            elif opcao == "4":
                self.transferir_proprietario()
            elif opcao == "5":
                self.lancar_multa()
            elif opcao == "6":
                self.veiculos_por_ano()
            elif opcao == "7":
                self.multas_veiculo_ano()
            elif opcao == "8":
                self.multas_condutor_ano()
            elif opcao == "9":
                self.multas_por_ano()
            elif opcao == "10":
                self.top_5_condutores()
            elif opcao == "0":
                print("\nEncerrando cliente DENATRAN. Até logo!")
                break
            else:
                print("Opção inválida. Digite um número de 0 a 10.")

            time.sleep(0.5)

def main():
    cli = DenatranCLI()
    try:
        cli.start()
        if len(sys.argv) > 1 and sys.argv[1] in ("--demo", "-d"):
            cli.run_demo()
        else:
            cli.menu()
    except KeyboardInterrupt:
        print("\n\nSaindo...")
    finally:
        cli.close()

if __name__ == "__main__":
    main()
