import streamlit as st
import pandas as pd
import altair as alt

# Configuração da página
st.set_page_config(page_title="Painel de Gastos", layout="wide")
st.title("💸 Painel de Gastos Pessoais & Parcelamentos")

# Identificador da planilha extraído da sua URL original
sheet_id = "1N_a9NbTMm5a_wT-UzmWlqhaqB7_iHso5Z1znTGYAtLI"

# URLs para exportar abas específicas via API gviz do Google Sheets
url_gastos = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Página1" 
url_parcelas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=compras+parceladas"

# Função auxiliar para tratar os valores monetários das duas abas
def limpar_valores(df):
    if "valor" in df.columns:
        df["valor"] = (
            df["valor"]
            .astype(str)
            .str.replace("R\$", "", regex=True)
            .str.replace(".", "", regex=False)  # Remove ponto de milhar se houver
            .str.replace(",", ".", regex=False)  # Substitui vírgula por ponto decimal
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
    
    # Caso a coluna 'nome' não exista nas parcelas, preenche como 'Parcelado'
    if "nome" not in dados_parcelas.columns:
        dados_parcelas["nome"] = "Parcelado"
except Exception as e:
    st.warning("Não foi possível carregar a aba 'compras parceladas'. Verifique se o nome está correto no Sheets.")
    dados_parcelas = pd.DataFrame(columns=["data", "categoria", "descricao", "valor", "parcela", "ano_mes", "nome"])

# Filtros na Barra Lateral
st.sidebar.header("Filtros")

# Junta os meses de ambas as planilhas para garantir que todos apareçam no filtro
todos_meses = sorted(
    list(set(dados_gastos["ano_mes"].dropna().unique()) | set(dados_parcelas["ano_mes"].dropna().unique())), 
    reverse=True
)
mes_selecionado = st.sidebar.selectbox("🗓️ Selecione o mês de análise", todos_meses)

categorias = ["Todas"] + sorted(list(set(dados_gastos["categoria"].dropna().unique()) | set(dados_parcelas["categoria"].dropna().unique())))
categoria_selecionada = st.sidebar.selectbox("🏷️ Categoria", categorias)

nomes = ["Todos"] + sorted(list(set(dados_gastos["nome"].dropna().unique()) | set(dados_parcelas["nome"].dropna().unique())))
nome_selecionado = st.sidebar.selectbox("👤 Responsável", nomes)

# Entrada de Receita para cálculo de saldo
st.sidebar.markdown("---")
st.sidebar.header("💰 Resumo Financeiro")
valor_receber = st.sidebar.number_input(
    "Valor disponível a receber (R$):", 
    min_value=0.0, 
    value=0.0, 
    step=100.0, 
    format="%.2f"
)

# --- Processamento dos Filtros e Integração das Parcelas do Mês ---

# Filtra gastos do mês correspondente
filtro_gastos = dados_gastos[dados_gastos["ano_mes"] == mes_selecionado]

# Filtra parcelas que vencem no mês correspondente
filtro_parcelas_mes = dados_parcelas[dados_parcelas["ano_mes"] == mes_selecionado]

# Une os gastos comuns com as parcelas devidas NESTE mês específico
colunas_unificadas = ["data", "categoria", "valor", "nome", "ano_mes"]
filtro_unificado = pd.concat([
    filtro_gastos[colunas_unificadas], 
    filtro_parcelas_mes[colunas_unificadas]
], ignore_index=True)

# Aplica os filtros secundários (Categoria e Responsável) na análise unificada do mês
if categoria_selecionada != "Todas":
    filtro_unificado = filtro_unificado[filtro_unificado["categoria"] == categoria_selecionada]

if nome_selecionado != "Todos":
    filtro_unificado = filtro_unificado[filtro_unificado["nome"] == nome_selecionado]

# Cálculos para os KPIs do Mês
total_gastos = filtro_unificado['valor'].sum()
saldo_atual = valor_receber - total_gastos

# Exibição dos KPIs
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total de Gastos no Mês (Fixo + Parcelas):", f"R$ {total_gastos:,.2f}")
col2.metric("📂 Categorias Ativas:", filtro_unificado["categoria"].nunique())
col3.metric("🟢 Saldo Atual no Momento:", f"R$ {saldo_atual:,.2f}", delta=f"Receita: R$ {valor_receber:,.2f}")

# Gráfico de barras por categoria do mês atual
st.subheader("📊 Gastos por categoria (Mês Selecionado):")
categoria_sum = (
    filtro_unificado.groupby("categoria", as_index=False)["valor"]
    .sum()
    .sort_values(by="valor", ascending=False)
)

if not categoria_sum.empty:
    bar_chart = alt.Chart(categoria_sum).mark_bar().encode(
        x=alt.X("categoria:N", sort="-y", title="Categoria", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valor:Q", axis=None),
        color=alt.Color("categoria:N", legend=alt.Legend(orient="top")),
        tooltip=["categoria", "valor"]
    ).properties(height=300)

    labels = alt.Chart(categoria_sum).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12, color="white"
    ).encode(
        x=alt.X("categoria:N", sort="-y"),
        y="valor:Q",
        text=alt.Text("valor:Q", format=".2f")
    )
    st.altair_chart(bar_chart + labels, use_container_width=True)
else:
    st.info("Nenhum gasto registrado para os filtros selecionados.")

# Gráfico de pizza por nome do mês atual
st.subheader("🥧 Gastos por nome (Mês Selecionado):")
nome_sum = filtro_unificado.groupby("nome", as_index=False)["valor"].sum().sort_values(by="valor", ascending=False)

if not nome_sum.empty:
    pie_chart = alt.Chart(nome_sum).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="valor", type="quantitative"),
        color=alt.Color(field="nome", type="nominal", legend=alt.Legend(orient="top")),
        tooltip=["nome", "valor"]
    )
    st.altair_chart(pie_chart, use_container_width=True)

# Tabela detalhada unificada
st.subheader("📄 Detalhamento do Mês (Gastos Gerais + Parcelas do Mês):")
st.dataframe(filtro_unificado, use_container_width=True)


# --- SEÇÃO SEPARADA: Análise Isolada de Parcelas Futuras ---
st.markdown("---")
st.subheader("🔮 Projeção de Compras Parceladas (Meses Futuros)")

# Filtra apenas as parcelas que são estritamente posteriores ao mês que você está analisando hoje
parcelas_futuras = dados_parcelas[dados_parcelas["ano_mes"] > mes_selecionado]

if not parcelas_futuras.empty:
    cronograma_parcelas = parcelas_futuras.groupby("ano_mes", as_index=False)["valor"].sum().sort_values(by="ano_mes")
    
    col_graf, col_tab = st.columns([2, 1])
    
    with col_graf:
        chart_futuro = alt.Chart(cronograma_parcelas).mark_bar(color="#FFA500").encode(
            x=alt.X("ano_mes:N", title="Mês de Vencimento Futuro"),
            y=alt.Y("valor:Q", axis=None),
            tooltip=["ano_mes", "valor"]
        ).properties(height=250)
        
        labels_futuro = alt.Chart(cronograma_parcelas).mark_text(
            align="center", baseline="bottom", dy=-5, color="white"
        ).encode(
            x=alt.X("ano_mes:N"),
            y="valor:Q",
            text=alt.Text("valor:Q", format=".2f")
        )
        st.altair_chart(chart_futuro + labels_futuro, use_container_width=True)
        
    with col_tab:
        st.dataframe(parcelas_futuras[["data", "categoria", "descricao", "valor", "parcela", "ano_mes"]], use_container_width=True)
else:
    st.info("Você não possui parcelas registradas para os meses seguintes ao selecionado.")


# --- NOVO GRÁFICO: Histórico e Total Gasto Geral de Todos os Meses ---
st.markdown("---")
st.subheader("📈 Histórico do Total Gasto Geral (Todos os Meses/Ano)")

# Agrega e une todo o histórico da planilha (Gastos Fixos + Parcelas respectivas de cada mês)
historico_gastos = dados_gastos.groupby("ano_mes", as_index=False)["valor"].sum()
historico_parcelas = dados_parcelas.groupby("ano_mes", as_index=False)["valor"].sum()

historico_geral = pd.merge(historico_gastos, historico_parcelas, on="ano_mes", how="outer", suffixes=("_fixo", "_parcela")).fillna(0.0)
historico_geral["Total Geral"] = historico_geral["valor_fixo"] + historico_geral["valor_parcela"]
historico_geral = historico_geral.sort_values(by="ano_mes")

if not historico_geral.empty:
    chart_geral = alt.Chart(historico_geral).mark_bar(color="#1f77b4").encode(
        x=alt.X("ano_mes:N", title="Mês / Ano", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("Total Geral:Q", axis=None, title="Total Gasto (R$)"),
        tooltip=[alt.Tooltip("ano_mes", title="Mês"), alt.Tooltip("Total Geral", title="Total (R$)", format=",.2f")]
    ).properties(height=350)

    labels_geral = alt.Chart(historico_geral).mark_text(
        align="center",
        baseline="bottom",
        dy=-5,
        fontSize=11,
        color="white"
    ).encode(
        x=alt.X("ano_mes:N"),
        y="Total Geral:Q",
        text=alt.Text("Total Geral:Q", format=".2f")
    )

    st.altair_chart(chart_geral + labels_geral, use_container_width=True)
else:
    st.info("Nenhum histórico disponível para gerar o gráfico geral.")

# Rodapé
st.markdown("#### Dados atualizados automaticamente da planilha do Google Sheets.")
