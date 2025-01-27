import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime
from io import BytesIO
import requests
from pytz import timezone
import time

# Função para calcular dias úteis
def calcular_dias_uteis(data_inicio, data_fim):
    dias_uteis = pd.date_range(start=data_inicio, end=data_fim, freq='B')
    return len(dias_uteis)

# Função para gerar arquivo Excel para download
def baixar_excel(df, nome_arquivo):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
        writer.close()
    st.download_button(
        label=f"📥 Baixar {nome_arquivo}",
        data=buffer.getvalue(),
        file_name=f"{nome_arquivo}.xlsx",
        mime="application/vnd.ms-excel"
    )

# Configuração inicial do Streamlit
st.set_page_config(
    page_title="Dashboard de Processos Seletivos",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Adicionar logotipo e título
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h1 style="text-align: left; color: #006eadff; margin: 0;">Processos Seletivos - PODIUM SOLUÇÕES</h1>
        <img src="https://imgur.com/cJQXp1t.png" style="height: 160px; margin-right: 20px;">
    </div>
    """,
    unsafe_allow_html=True
)

# URL do Google Sheets para exportar em formato XLSX
google_sheets_url = "https://docs.google.com/spreadsheets/d/1kA2sPD14H-A2ea7pg_0d_MOhe6uiGRT0/export?format=xlsx"

# Função para carregar dados do Google Drive
def carregar_dados_google_drive(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_excel(BytesIO(response.content), engine="openpyxl", sheet_name="Processo seletivo")
    except Exception as e:
        st.error(f"Erro ao carregar a planilha do Google Drive: {e}")
        return None

# Atualização automática a cada 60 segundos
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds > 60:
    st.session_state.last_refresh = datetime.now()
    st.experimental_rerun()

# Carregar os dados e tratar erros
df = carregar_dados_google_drive(google_sheets_url)

if df is None:
    st.stop()

# Configuração do fuso horário para o horário de Brasília
fuso_horario_brasilia = timezone('America/Sao_Paulo')
agora = datetime.now().astimezone(fuso_horario_brasilia)
data_atualizacao = agora.strftime("%d/%m/%Y")
hora_atualizacao = agora.strftime("%H:%M")

# Exibir a data e hora de atualização
st.markdown(
    f"<p style='text-align:right; color:#006eadff;'>Data Atualização: {data_atualizacao} | Hora: {hora_atualizacao}</p>",
    unsafe_allow_html=True
)

# Processamento dos dados
df['Data de abertura'] = pd.to_datetime(df['Data de abertura'], errors='coerce')
df['Qtd dias'] = (datetime.now() - df['Data de abertura']).dt.days
df['Qtd dias (úteis)'] = df['Data de abertura'].apply(
    lambda x: calcular_dias_uteis(x, datetime.now()) if pd.notnull(x) else np.nan
)
df['Empresa'] = df['Empresa'].str.upper()

def classificar_nivel(dias):
    if dias <= 20:
        return "Em dias"
    elif 21 <= dias <= 30:
        return "Atraso"
    else:
        return "Crítico"

df['Nível'] = df['Qtd dias (úteis)'].apply(lambda x: classificar_nivel(x) if pd.notnull(x) else np.nan)
empresas = list(df['Empresa'].dropna().unique())
empresas.sort()
empresas.insert(0, "TODAS")

empresa_selecionada = st.sidebar.radio("Empresa", options=empresas)
df_filtrado = df if empresa_selecionada == "TODAS" else df[df['Empresa'] == empresa_selecionada]

st.header("Quantidade de Processos por Empresa")
processos_por_empresa = df_filtrado['Empresa'].value_counts().reset_index()
processos_por_empresa.columns = ['Empresa', 'Quantidade']
fig_empresa = px.bar(
    processos_por_empresa,
    x='Empresa',
    y='Quantidade',
    title="Distribuição de Processos por Empresa",
    text='Quantidade',
    color_discrete_sequence=["#1a2732"]
)
st.plotly_chart(fig_empresa, use_container_width=True)

total_empresas = processos_por_empresa['Empresa'].nunique()
total_processos = df_filtrado.shape[0]
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"<h4 style='color:#1a2732; text-align:center;'>Total de empresas cadastradas: {total_empresas}</h4>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<h4 style='color:#1a2732; text-align:center;'>Total de processos cadastrados: {total_processos}</h4>", unsafe_allow_html=True)

st.header(f"Status dos Processos - {empresa_selecionada}")
status_counts = df_filtrado['Status'].value_counts().reset_index()
status_counts.columns = ['Status', 'Quantidade']
status_counts['Percentual'] = (status_counts['Quantidade'] / status_counts['Quantidade'].sum()) * 100
status_counts['Descrição'] = status_counts.apply(lambda row: f"{row['Status']} - {row['Quantidade']} ({row['Percentual']:.1f}%)", axis=1)
fig_status = px.bar(status_counts, x='Descrição', y='Quantidade', text='Quantidade')
st.plotly_chart(fig_status, use_container_width=True)

st.header(f"Níveis dos Processos - {empresa_selecionada}")
nivel_counts = df_filtrado['Nível'].value_counts().reset_index()
nivel_counts.columns = ['Nível', 'Quantidade']
nivel_colors = {"Em dias": "green", "Atraso": "orange", "Crítico": "red"}

fig_nivel = px.bar(
    nivel_counts,
    x='Nível',
    y='Quantidade',
    title="Distribuição dos Níveis",
    labels={'Quantidade': 'Quantidade'},
    color='Nível',
    color_discrete_map=nivel_colors,
    text='Quantidade',
)
st.plotly_chart(fig_nivel, use_container_width=True)

st.header("Top 5 Empresas Mais Críticas")
top_5_empresas = df[['Empresa', 'Qtd dias (úteis)']].nlargest(5, 'Qtd dias (úteis)')
fig_criticas = px.bar(
    top_5_empresas,
    x='Empresa',
    y='Qtd dias (úteis)',
    title="Top 5 Empresas Mais Críticas",
    text='Qtd dias (úteis)',
    color_discrete_sequence=["#004c70"]
)
st.plotly_chart(fig_criticas, use_container_width=True)

# Tabelas lado a lado
st.header("Tabelas de Processos e Status")
col1, col2 = st.columns(2)

# Tabela de Processos
with col1:
    tabela_processos = df_filtrado[['Empresa', 'Cargo', 'Status', 'Nível', 'Qtd dias (úteis)']].sort_values(by='Qtd dias (úteis)', ascending=False)
    st.dataframe(tabela_processos, use_container_width=True)
    baixar_excel(tabela_processos, "Tabela_Processos")

# Tabela Dias Parados por Status
with col2:
    dias_status = df_filtrado.groupby('Status')['Qtd dias (úteis)'].sum().reset_index()
    dias_status.columns = ['Status', 'Dias Parados']
    dias_status = dias_status.sort_values(by='Dias Parados', ascending=False)
    dias_status['Dias Parados'] = dias_status['Dias Parados'].apply(lambda x: f"{x:,.0f}".replace(",", "."))
    st.dataframe(dias_status, use_container_width=True)
    baixar_excel(dias_status, "Dias_Parados_Por_Status")
