#==============================================#
# ======== IMPORTS E CONFIGURAÇÕES ============#
#==============================================#

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import html
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide")

#=================================================#
# ======== CONFIGURAÇÕES DEPARTAMENTOS ===========#
#=================================================#
DEPARTAMENTOS_PADRAO = [
    "Atendimento",
    "Analista de Cobrança",
    "Assistência 24H",
    "Abertura de Eventos",
    "Central de Relacionamento",
    "Cancelamento",
    "Cadastro",
    "Troca Periféricos",
    "Ouvidoria",
    "Juridico",
]

DEPARTAMENTO_MAP = {
    'Atendimento': 'Atendimento',
    'Analista de Cobrança': 'Analista de Cobrança',
    'Analista de cobranca': 'Analista de Cobrança',
    'Cobranca': 'Analista de Cobrança',
    'Assistência 24h': 'Assistência 24H',
    'Assistência 24Hrs': 'Assistência 24H',
    'Rastreador': 'Assistência 24H',
    'MonitoramentoRastreamento': 'Assistência 24H',
    'Abertura de Eventos': 'Abertura de Eventos',
    'Abertura eventos': 'Abertura de Eventos',
    'Central de relacionamento': 'Central de Relacionamento',
    'Cancelamento': 'Cancelamento',
    'Cadastro': 'Cadastro',
    'Analista de Cadastro': 'Cadastro',
    'Troca Perifericos': 'Troca Periféricos',
    'Ouvidoria': 'Ouvidoria',
    'Jurídico': 'Juridico'
    }

#=================================#
# ======== CSS dos cards =========#
#=================================#
st.html("""
    <style>
        .card { background-color: #333333; color: white; padding: 10px; border-radius: 8px; margin-bottom: 10px; height: 140px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box; }
        .card-title  { margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px; font-weight: bold; line-height: 1.3; }
        .card-text   { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 15px; line-height: 1.2; }
        .card-metric { text-align: right; }
        .card-metric-value { font-size: 22px; font-weight: bold; }
        .in-time { font-size: 18px; font-weight: bold; }
        
        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }

        .footer-empresa {
            font-size: 22px;
            font-weight: bold;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .card-empty { height: 140px; margin-bottom: 10px; }
    </style>
""")

#=======================================#
# ======== Conexão com o Banco =========#
#=======================================#

engine = create_engine("postgresql+psycopg2://postgres:postgres123@192.168.1.62:5432/sistema")

#===================================================#
# ======== FUNÇÃO DE CARREGAMENTO DE DADOS =========#
#===================================================#
@st.cache_data(ttl=5)
def carregar_dados(limit=100):
    query = f"""
        SELECT
            empresa,
            data_criado,
            numero_cliente, 
            nome_agente,
            departamento_agente,
            ultima_mensagem_nome,
            tempo_de_espera,
            (ultima_mensagem_data + ultima_mensagem_hora) AS data_ultima_mensagem,
            status,
            em_espera
        FROM historico_atendimentos
        WHERE status = 'Em atendimento'
        AND ultima_mensagem_data IS NOT NULL AND ultima_mensagem_hora IS NOT NULL
        ORDER BY tempo_de_espera DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, engine, parse_dates=['data_ultima_mensagem'])

#=======================================#
# =========== BLOCO DE FILTROS =========#
#=======================================#

df_inicial = carregar_dados(limit=100)

empresas = df_inicial['empresa'].dropna().unique().tolist()
departamentos_opcoes = DEPARTAMENTOS_PADRAO
mensagem_opcoes = df_inicial['ultima_mensagem_nome'].dropna().unique().tolist()

# Inicializa session_state
if 'empresas_selecionadas' not in st.session_state:
    st.session_state.empresas_selecionadas = empresas

if 'departamentos_selecionados' not in st.session_state:
    st.session_state.departamentos_selecionados = departamentos_opcoes

if 'mensagem_selecionadas' not in st.session_state:
    st.session_state.mensagem_selecionadas = mensagem_opcoes.copy()
else:
    # Remove valores que não existem mais nas opções
    st.session_state.mensagem_selecionadas = [
        m for m in st.session_state.mensagem_selecionadas if m in mensagem_opcoes
    ]

st.sidebar.header("Filtros")

st.sidebar.multiselect(
    'Filtro Associado | Sistema',
    options=sorted(mensagem_opcoes),
    key='mensagem_selecionadas',
    default=st.session_state.mensagem_selecionadas
)

st.sidebar.multiselect(
    "Filtrar por Empresa:",
    options=sorted(empresas),
    key='empresas_selecionadas',
    default=st.session_state.empresas_selecionadas
)

st.sidebar.multiselect(
    "Filtrar por Departamento:",
    options=sorted(departamentos_opcoes),
    key='departamentos_selecionados',
    default=st.session_state.departamentos_selecionados
)

placeholder = st.empty()

#=====================================================#
# ======== FUNÇÃO DE FORMATAÇÃO DE TEMPO =============#
#=====================================================#

def formatar_tempo_hhmmss(delta_segundos):
    if delta_segundos < 0:
        delta_segundos = 0
    segundos = int(delta_segundos)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos_restantes = segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d}"

#=====================================================#
# ======== FUNÇÃO PARA CRIAR CARDS ===================#
#=====================================================#
def criar_card_html(row):
    empresa = html.escape(str(row.empresa))
    agente = html.escape(str(row.nome_agente))

    # Formata a data
    if pd.notnull(row.data_criado):
        try:
            data_formatada = pd.to_datetime(row.data_criado).strftime("%d/%m/%Y")
        except Exception:
            data_formatada = str(row.data_criado)
    else:
        data_formatada = "-"

    departamento_display = html.escape(str(row.departamento_agente_padrao))
    ultima_msg = html.escape(str(row.ultima_mensagem_nome))
    numero_cliente = html.escape(str(row.numero_cliente))

    minutos_decorridos = row.tempo_desde_msg / 60 if pd.notnull(row.tempo_desde_msg) else 0
    tempo_display = formatar_tempo_hhmmss(row.tempo_desde_msg if pd.notnull(row.tempo_desde_msg) else 0)
    
    if minutos_decorridos > 5: 
        cor_fundo, cor_texto = "#d62728", "white" # Vermelho
    elif minutos_decorridos > 3: 
        cor_fundo, cor_texto = "#ffdd57", "black" # Amarelo
    else: 
        cor_fundo, cor_texto = "#28a745", "white" # Verde
    
    tempo_display_html = f'<div class="card-metric-value">{tempo_display}</div>'

    html_card = f"""
    <div class="card" style="background-color: {cor_fundo}; color: {cor_texto};">
        <div>
            <div class="card-text" title="{numero_cliente}"><strong>Cliente:</strong> {numero_cliente}</div>
            <div class="card-text" title="{agente}"><strong>Agente:</strong> {agente}</div>
            <div class="card-text" title="{ultima_msg}"><strong>Últ. Msg:</strong> {ultima_msg}</div>
            <h4  class="card-title" title="{departamento_display}">{departamento_display}</h4>
            <div class="card-text" title="{data_formatada}"><strong>Criado em: </strong>{data_formatada}</div>
        </div>
        
        <div class="card-footer">
            <div class="footer-empresa" title="{empresa}">{empresa}</div>
            <div class="card-metric">{tempo_display_html}</div>
        </div>
    </div>
    """
    return html_card

def criar_cards(df, colunas_por_linha=6):
    if df.empty:
        return
    for i in range(0, len(df), colunas_por_linha):
        cols = st.columns(colunas_por_linha)
        trecho = df.iloc[i:i+colunas_por_linha]
        for j, row in enumerate(trecho.itertuples(index=False)):
            with cols[j]:
                st.html(criar_card_html(row))

def criar_primeira_linha_somente_iguais(df_matches, colunas_por_linha=6):
    cols = st.columns(colunas_por_linha)
    for j in range(colunas_por_linha):
        with cols[j]:
            if j < len(df_matches):
                row = df_matches.iloc[j]
                st.html(criar_card_html(row))
            else:
                st.html('<div class="card-empty"></div>')

#=====================================================#
# ======== ATUALIZAÇÃO AUTOMÁTICA ===================#
#=====================================================#

# Atualiza automaticamente a cada 10 segundos (10000 ms)
st_autorefresh(interval=3000, key="atualizacao_painel")

fuso_horario_local = pytz.timezone('America/Sao_Paulo')
COLUNAS_POR_LINHA = 6

df = carregar_dados(limit=100)

if df.empty:
    with placeholder.container():
        st.warning("Nenhum atendimento ativo encontrado.")
else:
    df_filtrado = df.copy()    
    df_filtrado.loc[:, 'departamento_agente_padrao'] = df_filtrado['departamento_agente'].map(DEPARTAMENTO_MAP).fillna(df_filtrado['departamento_agente'])    
    df_filtrado = df_filtrado[df_filtrado['empresa'].isin(st.session_state.empresas_selecionadas)]
    df_filtrado = df_filtrado[df_filtrado['departamento_agente_padrao'].isin(st.session_state.departamentos_selecionados)]
    df_filtrado['nome_agente'] = df_filtrado['nome_agente'].fillna('').astype(str)
    df_filtrado = df_filtrado[df_filtrado['ultima_mensagem_nome'].isin(st.session_state.mensagem_selecionadas)]
    
    with placeholder.container():
        st.subheader("Painel de Atendimentos Ativos")

        if df_filtrado.empty:
            st.warning("Nenhum atendimento encontrado para os filtros selecionados.")
        else:
            agora = datetime.now(fuso_horario_local)
            try:
                df_filtrado['data_ultima_mensagem'] = df_filtrado['data_ultima_mensagem'].dt.tz_localize(fuso_horario_local, ambiguous='infer')
            except Exception:
                pass

            df_filtrado['tempo_desde_msg'] = (agora - df_filtrado['data_ultima_mensagem']).dt.total_seconds()
            df_filtrado['agente_respondeu'] = df_filtrado['nome_agente'] == df_filtrado['ultima_mensagem_nome']

            df_agente = df_filtrado[df_filtrado['agente_respondeu'] == True].sort_values(by='tempo_desde_msg', ascending=False).reset_index(drop=True)
            df_cliente = df_filtrado[df_filtrado['agente_respondeu'] == False].sort_values(by='tempo_desde_msg', ascending=False).reset_index(drop=True)

            # Primeira linha limitada a 6 iguais
            primeiros_matches = df_agente.iloc[:COLUNAS_POR_LINHA].reset_index(drop=True)

            # O resto é só clientes (iguais extras somem)
            df_resto = df_cliente.copy()

            if not primeiros_matches.empty:
                criar_primeira_linha_somente_iguais(primeiros_matches, colunas_por_linha=COLUNAS_POR_LINHA)
                if not df_resto.empty:
                    st.markdown("---")

            criar_cards(df_resto, colunas_por_linha=COLUNAS_POR_LINHA)
