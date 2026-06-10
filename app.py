import streamlit as st
import pandas as pd
import altair as alt

# Configuração da página
st.set_page_config(page_title="Painel de Gastos", layout="wide")
st.title("💸 Painel de Gastos Pessoais")

# URL pública da planilha exportada como CSV
csv_url = "https://docs.google.com/spreadsheets/d/1N_a9NbTMm5a_wT-UzmWlqhaqB7_iHso5Z1znTGYAtLI/export?format=csv"

# Leitura dos dados
dados = pd.read_csv(csv_url)

# Tratamento das colunas
dados["data"] = pd.to_datetime(dados["data"], dayfirst=True, errors="coerce")
dados["valor"] = (
    dados["valor"]
    .astype(str)
    .str.replace("R\$", "", regex=True)
    .str.replace(",", ".", regex=False)
)
dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
dados["ano_mes"] = dados["data"].dt.strftime("%Y-%m")

# Filtros na Barra Lateral
st.sidebar.header("Filtros")
meses = sorted(dados["ano_mes"].dropna().unique(), reverse=True)
mes_selecionado = st.sidebar.selectbox("🗓️ Selecione o mês", meses)

categorias = ["Todas"] + sorted(dados["categoria"].dropna().unique())
categoria_selecionada = st.sidebar.selectbox("🏷️ Categoria", categorias)

nomes = ["Todos"] + sorted(dados["nome"].dropna().unique())
nome_selecionado = st.sidebar.selectbox("👤 Responsável", nomes)

# --- NOVA SEÇÃO: Entrada de Receita ---
st.sidebar.markdown("---")
st.sidebar.header("💰 Resumo Financeiro")
# Campo para inserir o valor a receber (com valor padrão de 0.00)
valor_receber = st.sidebar.number_input(
    "Valor disponível a receber (R$):", 
    min_value=0.0, 
    value=0.0, 
    step=100.0, 
    format="%.2f"
)

# Aplicar filtros nos dados
filtro = dados[dados["ano_mes"] == mes_selecionado]

if categoria_selecionada != "Todas":
    filtro = filtro[filtro["categoria"] == categoria_selecionada]

if nome_selecionado != "Todos":
    filtro = filtro[filtro["nome"] == nome_selecionado]

# Cálculos para os KPIs
total_gastos = filtro['valor'].sum()
saldo_atual = valor_receber - total_gastos

# KPIs - Alterado para 3 colunas para incluir o Saldo Atual
col1, col2, col3 = st.columns(3)
col1.metric("📉 Total de gastos mês:", f"R$ {total_gastos:,.2f}")
col2.metric("📂 Categorias do filtro", filtro["categoria"].nunique())

# Exibe o saldo atualizado e muda a cor se o saldo for negativo (opcional do Streamlit)
col3.metric(
    "🟢 Saldo Atual no Momento:", 
    f"R$ {saldo_atual:,.2f}", 
    delta=f"Disponível: R$ {valor_receber:,.2f}", 
    delta_color="normal"
)

# Gráfico de barras por categoria (ordenado e com rótulo)
st.subheader("📊 Gastos por categoria:")

categoria_sum = (
    filtro.groupby("categoria", as_index=False)["valor"]
    .sum()
    .sort_values(by="valor", ascending=False)
)

bar_chart = alt.Chart(categoria_sum).mark_bar().encode(
    x=alt.X("categoria:N", sort="-y", title="Categoria", axis=alt.Axis(labelAngle=0)),  # Horizontal
    y=alt.Y("valor:Q", axis=None),
    color=alt.Color("categoria:N", legend=alt.Legend(orient="top")),
    tooltip=["categoria", "valor"]
).properties(height=350)

# Rótulos acima das colunas
labels = alt.Chart(categoria_sum).mark_text(
    align="center",
    baseline="bottom",
    dy=-5,
    fontSize=12,
    color="white"
).encode(
    x=alt.X("categoria:N", sort="-y"),
    y="valor:Q",
    text=alt.Text("valor:Q", format=".2f")
)

st.altair_chart(bar_chart + labels, use_container_width=True)

# Gráfico de pizza por nome (ordenado e com legenda horizontal)
st.subheader("🥧 Gastos por nome:")

nome_sum = filtro.groupby("nome", as_index=False)["valor"].sum().sort_values(by="valor", ascending=False)

pie_chart = alt.Chart(nome_sum).mark_arc(innerRadius=50).encode(
    theta=alt.Theta(field="valor", type="quantitative"),
    color=alt.Color(field="nome", type="nominal", legend=alt.Legend(orient="top")),
    tooltip=["nome", "valor"]
)

st.altair_chart(pie_chart, use_container_width=True)

# Tabela detalhada
st.subheader("📄 Detalhamento:")
st.dataframe(filtro, use_container_width=True)

# Rodapé
st.markdown("#### Dados atualizados automaticamente da planilha do Google Sheets.")
