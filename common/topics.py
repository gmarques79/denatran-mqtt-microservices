"""
Definição dos tópicos MQTT utilizados no sistema DENATRAN.
Convenção padronizada:
- Requisição: denatran/<dominio>/<acao>
- Resposta:   denatran/<dominio>/<acao>/resposta
"""

# --- MICROSSERVIÇO: CONDUTORES ---
CONDUTOR_CADASTRAR = "denatran/condutor/cadastrar"
CONDUTOR_CADASTRAR_RESPOSTA = "denatran/condutor/cadastrar/resposta"

CONDUTOR_OBTER = "denatran/condutor/obter"
CONDUTOR_OBTER_RESPOSTA = "denatran/condutor/obter/resposta"

CONDUTOR_TRANSFERIR = "denatran/condutor/transferir"
CONDUTOR_TRANSFERIR_RESPOSTA = "denatran/condutor/transferir/resposta"

CONDUTOR_LISTAR = "denatran/condutor/listar"
CONDUTOR_LISTAR_RESPOSTA = "denatran/condutor/listar/resposta"


# --- MICROSSERVIÇO: VEÍCULOS ---
VEICULO_EMPLACAR = "denatran/veiculo/emplacar"
VEICULO_EMPLACAR_RESPOSTA = "denatran/veiculo/emplacar/resposta"

VEICULO_IPVA = "denatran/veiculo/ipva"
VEICULO_IPVA_RESPOSTA = "denatran/veiculo/ipva/resposta"

VEICULO_TRANSFERIR = "denatran/veiculo/transferir"
VEICULO_TRANSFERIR_RESPOSTA = "denatran/veiculo/transferir/resposta"

VEICULO_LISTAR_POR_ANO = "denatran/veiculo/listar-por-ano"
VEICULO_LISTAR_POR_ANO_RESPOSTA = "denatran/veiculo/listar-por-ano/resposta"

VEICULO_OBTER = "denatran/veiculo/obter"
VEICULO_OBTER_RESPOSTA = "denatran/veiculo/obter/resposta"

VEICULO_POR_CONDUTOR = "denatran/veiculo/por-condutor"
VEICULO_POR_CONDUTOR_RESPOSTA = "denatran/veiculo/por-condutor/resposta"

VEICULO_LISTAR_PROPRIETARIOS = "denatran/veiculo/listar-proprietarios"
VEICULO_LISTAR_PROPRIETARIOS_RESPOSTA = "denatran/veiculo/listar-proprietarios/resposta"

VEICULO_ATUALIZAR_PROPRIETARIO = "denatran/veiculo/atualizar-proprietario"
VEICULO_ATUALIZAR_PROPRIETARIO_RESPOSTA = "denatran/veiculo/atualizar-proprietario/resposta"


# --- MICROSSERVIÇO: MULTAS ---
MULTA_LANCAR = "denatran/multa/lancar"
MULTA_LANCAR_RESPOSTA = "denatran/multa/lancar/resposta"

MULTA_POR_VEICULO = "denatran/multa/por-veiculo"
MULTA_POR_VEICULO_RESPOSTA = "denatran/multa/por-veiculo/resposta"

MULTA_POR_CONDUTOR = "denatran/multa/por-condutor"
MULTA_POR_CONDUTOR_RESPOSTA = "denatran/multa/por-condutor/resposta"

MULTA_POR_ANO = "denatran/multa/por-ano"
MULTA_POR_ANO_RESPOSTA = "denatran/multa/por-ano/resposta"

MULTA_TOP_5 = "denatran/multa/top-5"
MULTA_TOP_5_RESPOSTA = "denatran/multa/top-5/resposta"
