import streamlit as st
import pandas as pd
import altair as alt

# Configuração da página
st.set_page_config(page_title="Painel de Gastos", layout="wide")
st.title("💸 Painel de Gastos Pessoais & Parcelamentos")

# URL principal da planilha (Aba Principal)
csv_url_gastos = "https://docs.google.com/spreadsheets/d/1N_a9NbTMm5a_wT-UzmWlqhaqB7_iHso5Z1znTGYAtLI/export?format=csv"

# URL para puxar especificamente a aba "compras parceladas"
csv_url_parcelas = "https://docs.google.com/spreadsheets/d/1N_a9NbTMm5a_wT-UzmWlqhaqB7_iHso5Z1znTGYAtLI/gviz/tq?tqx=out:csv&sheet=compras+parceladas"

# Função para limpar e converter os valores monetários do padrão brasileiro para float
def limpar_valores(df):
    if "valor" in df.columns:
        df["valor"] = (
            df["valor"]
            .astype(str)
            .str.replace("R\$", "", regex=True)
            .str.replace(".", "", regex=False)   # Remove pontos de milhar (ex: 1.000)
            .str.replace(",", ".", regex=False)   # Substitui a vírgula por ponto decimal
            .str.strip()
        )
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    return df

# --- CARREGAR E TRATAR ABA GASTOS ---
dados_gastos = pd.read_csv(csv_url_gastos)
dados_gastos["data"] = pd.to_datetime(dados_gastos["data"], dayfirst=True, errors="coerce")
dados_gastos = limpar_valores(dados_gastos)
dados_gastos["ano_mes"] = dados_gastos["data"].dt.strftime("%Y-%m")

# --- CARREGAR E TRATAR ABA COMPRAS PARCELADAS ---
try:
    dados_parcelas = pd.read_csv(csv_url_parcelas)
    dados_parcelas["data"] = pd.to_datetime(dados_parcelas["data"], dayfirst=True, errors="coerce")
    dados_parcelas = limpar_valores(dados_parcelas)
    dados_parcelas["ano_mes"] = dados_parcelas["data"].dt.strftime("%Y-%m")
    
    # Como a aba parcelas não tem a coluna 'nome' (responsável), vamos preencher como "Parcelado"
    if "nome" not in dados_parcelas.columns:
        dados_parcelas["nome"] = "Parcelado"
except Exception as e:
    st.error(f"Erro ao carregar a aba 'compras parceladas': {e}")
    dados_parcelas = pd.DataFrame(columns=["data", "categoria", "descricao", "valor", "parcela", "ano_mes", "nome"])


# --- FILTROS NA BARRA LATERAL ---
st.sidebar.header("Filtros")

# Garante que o filtro liste os meses de ambas as abas combinadas
meses_combinados = sorted(
    list(set(dados_gastos["ano_mes"].dropna().unique()) | set(dados_parcelas["ano_mes"].dropna().unique())), 
    reverse=True
)
mes_selecionado = st.sidebar.selectbox("🗓️ Selecione o mês", meses_combinados)

categorias = ["Todas"] + sorted(list(set(dados_gastos["categoria"].dropna().unique()) | set(dados_parcelas["categoria"].dropna().unique())))
categoria_selecionada = st.sidebar.selectbox("🏷️ Categoria", categorias)

nomes = ["Todos"] + sorted(list(set(dados_gastos["nome"].dropna().unique()) | set(dados_parcelas["nome"].dropna().unique())))
nome_selecionado = st.sidebar.selectbox("👤 Responsável", nomes)


# --- ENTRADA DE RECEITA ---
st.sidebar.markdown("---")
st.sidebar.header("💰 Resumo Financeiro")
valor_receber = st.sidebar.number_input(
    "Valor disponível a receber (R$):", 
    min_value=0.0, 
    value=0.0, 
    step=100.0, 
    format="%.2f"
)


# --- UNIÃO E FILTRAGEM DOS DADOS DO MÊS SELECIONADO ---
# Filtrando os dados normais do mês
filtro_gastos = dados_gastos[dados_gastos["ano_mes"] == mes_selecionado]

# Filtrando as parcelas que vencem neste mesmo mês
filtro_parcelas = dados_parcelas[dados_parcelas["ano_mes"] == mes_selecionado]

# Padronizando colunas essenciais para juntar tudo em uma única tabela de análise do mês
colunas_comuns = ["data", "categoria", "valor", "nome", "ano_mes"]
filtro_unificado = pd.concat([
    filtro_gastos[colunas_comuns], 
    filtro_parcelas[colunas_comuns]
], ignore_index=True)

# Aplicar filtros secundários na análise unificada
if categoria_selecionada != "Todas":
    filtro_unificado = filtro_unificado[filtro_unificado["categoria"] == categoria_selecionada]

if nome_selecionado != "Todos":
    filtro_unificado = filtro_unificado[filtro_unificado["nome"] == nome_selecionado]


# --- CALCULOS E KPIs ---
total_gastos = filtro_unificado['valor'].sum()
saldo_atual = valor_receber - total_gastos

col1, col2, col3 = st.columns(3)
col1.metric("📉 Total de gastos mês (À vista + Parcelas):", f"R$ {total_gastos:,.2f}")
col2.metric("📂 Categorias do filtro", filtro_unificado["categoria"].nunique())
col3.metric(
    "🟢 Saldo Atual no Momento:", 
    f"R$ {saldo_atual:,.2f}", 
    delta=f"Disponível: R$ {valor_receber:,.2f}", 
    delta_color="normal"
)


# --- GRÁFICO DE BARRAS POR CATEGORIA (MÊS SELECIONADO) ---
st.subheader("📊 Gastos por categoria (Incluindo parcelas do período):")

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
    ).properties(height=350)

    labels = alt.Chart(categoria_sum).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12, color="white"
    ).encode(
        x=alt.X("categoria:N", sort="-y"),
        y="valor:Q",
        text=alt.Text("valor:Q", format=".2f")
    )
    st.altair_chart(bar_chart + labels, use_container_width=True)


# --- GRÁFICO DE PIZZA POR RESPONSÁVEL (MÊS SELECIONADO) ---
st.subheader("🥧 Gastos por nome:")
nome_sum = filtro_unificado.groupby("nome", as_index=False)["valor"].sum().sort_values(by="valor", ascending=False)

if not nome_sum.empty:
    pie_chart = alt.Chart(nome_sum).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="valor", type="quantitative"),
        color=alt.Color(field="nome", type="nominal", legend=alt.Legend(orient="top")),
        tooltip=["nome", "valor"]
    )
    st.altair_chart(pie_chart, use_container_width=True)


# --- TABELA DE DETALHAMENTO DO MÊS ---
st.subheader("📄 Detalhamento Geral do Mês Selecionado:")
st.dataframe(filtro_unificado, use_container_width=True)


# --- NOVO GRÁFICO: ANÁLISE SEPARADA DE COMPRAS PARCELADAS MÊS A MÊS ---
st.markdown("---")
st.subheader("🔮 Evolução e Cronograma de Compras Parceladas (Histórico e Futuro)")

# Agrupa todas as parcelas cadastradas da nova aba mês a mês, independente do filtro lateral
parcelas_mes_a_mes = dados_parcelas.groupby("ano_mes", as_index=False)["valor"].sum().sort_values(by="ano_mes")

if not parcelas_mes_a_mes.empty:
    chart_parcelas = alt.Chart(parcelas_mes_a_mes).mark_bar(color="#FFA500").encode(
        x=alt.X("ano_mes:N", title="Mês / Ano de Vencimento", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("valor:Q", axis=None, title="Total Parcelado (R$)"),
        tooltip=[alt.Tooltip("ano_mes", title="Mês Vencimento"), alt.Tooltip("valor", title="Total a Pagar (R$)", format=",.2f")]
    ).properties(height=380)

    labels_parcelas = alt.Chart(parcelas_mes_a_mes).mark_text(
        align="center",
        baseline="bottom",
        dy=-5,
        fontSize=11,
        color="white"
    ).encode(
        x=alt.X("ano_mes:N"),
        y="valor:Q",
        text=alt.Text("valor:Q", format=".2f")
    )

    st.altair_chart(chart_parcelas + labels_parcelas, use_container_width=True)
else:
    st.info("Nenhuma parcela encontrada na aba 'compras parceladas'.")

# Rodapé
st.markdown("#### Dados atualizados automaticamente da planilha do Google Sheets.")
