import streamlit as st
import pandas as pd
import altair as alt

# Configuração da página
st.set_page_config(page_title="Painel de Gastos", layout="wide")
st.title("💸 Painel de Gastos Pessoais & Parcelamentos")

# Identificador da planilha extraído da sua URL original
sheet_id = "1N_a9NbTMm5a_wT-UzmWlqhaqB7_iHso5Z1znTGYAtLI"

# --- ALTERE AQUI OS NÚMEROS DO GID CONFORME SUA PLANILHA ---
gid_gastos = "0"          # Substitua pelo gid da aba principal se for diferente de 0
gid_parcelas = "1351111"  # Substitua pelo gid que aparece quando você clica na aba 'compras parceladas'

# URLs seguras utilizando o GID (garante que o Sheets exporte a aba correta)
url_gastos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_gastos}"
url_parcelas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_parcelas}"

# Função auxiliar para tratar os valores monetários
def limpar_valores(df):
    if df.empty:
        return df
    if "valor" in df.columns:
        df["valor"] = (
            df["valor"]
            .astype(str)
            .str.replace("R\$", "", regex=True)
            .str.replace(".", "", regex=False)  # Remove ponto de milhar
            .str.replace(",", ".", regex=False)  # Substitui vírgula por ponto
            .str.strip()
        )
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    return df

# 1. Leitura e tratamento da Aba Principal (Gastos)
try:
    dados_gastos = pd.read_csv(url_gastos)
    dados_gastos["data"] = pd.to_datetime(dados_gastos["data"], dayfirst=True, errors="coerce")
    dados_gastos = limpar_valores(dados_gastos)
    dados_gastos["ano_mes"] = dados_gastos["data"].dt.strftime("%Y-%m")
except Exception as e:
    st.error(f"Erro ao ler a aba principal de Gastos: {e}")
    dados_gastos = pd.DataFrame(columns=["data", "categoria", "valor", "nome", "ano_mes"])

# 2. Leitura e tratamento da Nova Aba (Compras Parceladas)
try:
    dados_parcelas = pd.read_csv(url_parcelas)
    dados_parcelas["data"] = pd.to_datetime(dados_parcelas["data"], dayfirst=True, errors="coerce")
    dados_parcelas = limpar_valores(dados_parcelas)
    dados_parcelas["ano_mes"] = dados_parcelas["data"].dt.strftime("%Y-%m")
    
    if "nome" not in dados_parcelas.columns:
        dados_parcelas["nome"] = "Parcelado"
except Exception as e:
    st.error(f"Erro ao ler a aba 'compras parceladas': {e}")
    dados_parcelas = pd.DataFrame(columns=["data", "categoria", "descricao", "valor", "parcela", "ano_mes", "nome"])

# O RESTANTE DO CÓDIGO DAQUI PARA BAIXO CONTINUA EXATAMENTE IGUAL...
# Rodapé
st.markdown("#### Dados atualizados automaticamente da planilha do Google Sheets.")
