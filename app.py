from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Afaseres Domésticos | Indicadores",
    page_icon="🏠",
    layout="wide",
)

ARQUIVO_DADOS = Path(__file__).parent / "conteudo" / "Tabela 1.1.1.xls"
COLUNAS = [
    "Localidade",
    "Total geral",
    "Total branca",
    "Total preta ou parda",
    "Homem branco",
    "Homem preto ou pardo",
    "Mulher branca",
    "Mulher preta ou parda",
]


@st.cache_data
def carregar_dados(arquivo):
    planilha = pd.ExcelFile(arquivo)
    registros = []

    for ano in planilha.sheet_names:
        if "(CV)" in ano:
            continue

        tabela = pd.read_excel(planilha, sheet_name=ano, header=None)
        inicio = tabela.index[tabela.iloc[:, 0].astype(str).str.strip() == "Brasil"]
        if len(inicio) == 0:
            continue

        dados_ano = tabela.iloc[inicio[0] :, :8].copy()
        dados_ano.columns = COLUNAS
        dados_ano["Ano"] = int(ano)
        dados_ano["Localidade"] = dados_ano["Localidade"].astype(str).str.strip()
        dados_ano = dados_ano[dados_ano["Localidade"].ne("")]

        for coluna in COLUNAS[1:]:
            dados_ano[coluna] = pd.to_numeric(dados_ano[coluna], errors="coerce")

        registros.append(dados_ano)

    if not registros:
        return pd.DataFrame(columns=COLUNAS + ["Ano"])

    return pd.concat(registros, ignore_index=True).dropna(subset=["Total geral"])


def formatar_horas(valor):
    return f"{valor:.1f} h"


st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] { padding: 1rem 1.2rem; border-radius: 14px; border: 1px solid #e5eaf2;}
    .intro {color: #586579; font-size: 1.05rem; max-width: 850px;}
    .note {Raçaground: #fff8e8; border-left: 4px solid #e8a838; padding: 0.85rem 1rem; border-radius: 8px; color: #55451f;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏠 Cuidados e afaseres domésticos no Brasil")
st.markdown(
    '<p class="intro">Quantas horas por semana as pesssoas dedicam ao trabalho de cuidado não remunerado? '
    "Explore as diferenças entre homens e mulheres, raça/cor e unidades da Federação.</p>",
    unsafe_allow_html=True,
)


if not ARQUIVO_DADOS.exists():
    st.error("Não encontrei a planilha. Confira se o arquivo está na pasta conteudo.")
    st.stop()

dados = carregar_dados(str(ARQUIVO_DADOS))
if dados.empty:
    st.error("A planilha não contém dados no formato esperado.")
    st.stop()

localidades = sorted(dados["Localidade"].unique())
estados_e_regioes = [nome for nome in localidades if nome not in ["Brasil"]]
selecao_inicial = [nome for nome in ["Bahia", "Pernambuco", "Ceará", "Amazonas"] if nome in localidades]

with st.sidebar:
    st.header("Filtros")
    anos = sorted(dados["Ano"].unique(), reverse=True)
    ano = st.selectbox("Ano", anos)
    estados = st.multiselect(
        "Estados e regiões",
        options=estados_e_regioes,
        default=selecao_inicial or estados_e_regioes[:4],
        help="A seleção inicial destaca os estados das personas do projeto.",
    )
    grupos = st.multiselect(
        "Grupos para comparar",
        ["Homens brancos", "Homens pretos ou pardos", "Mulheres brancas", "Mulheres pretas ou pardas"],
        default=["Homens brancos", "Homens pretos ou pardos", "Mulheres brancas", "Mulheres pretas ou pardas"],
    )

colunas_grupos = {
    "Homens brancos": "Homem branco",
    "Homens pretos ou pardos": "Homem preto ou pardo",
    "Mulheres brancas": "Mulher branca",
    "Mulheres pretas ou pardas": "Mulher preta ou parda",
}
rotulos = {
    "Homem branco": "Homens brancos",
    "Homem preto ou pardo": "Homens pretos ou pardos",
    "Mulher branca": "Mulheres brancas",
    "Mulher preta ou parda": "Mulheres pretas ou pardas",
}

dados_ano = dados[dados["Ano"] == ano]
brasil = dados_ano[dados_ano["Localidade"] == "Brasil"]
if brasil.empty:
    st.warning("O valor nacional não está disponível para o ano selecionado.")
    st.stop()

linha_brasil = brasil.iloc[0]
horas_homens = linha_brasil[["Homem branco", "Homem preto ou pardo"]].mean()
horas_mulheres = linha_brasil[["Mulher branca", "Mulher preta ou parda"]].mean()
diferenca = horas_mulheres - horas_homens

k1, k2, k3 = st.columns(3)
k1.metric("Média nacional — mulheres", formatar_horas(horas_mulheres))
k2.metric("Média nacional — homens", formatar_horas(horas_homens))
k3.metric("Diferença média", formatar_horas(diferenca), help="Média simples entre os dois grupos de raça/cor disponíveis para cada sexo.")


st.subheader(f"Comparação por estado — {ano}")
if not estados:
    st.info("Selecione pelo menos um estado ou região na barra lateral para ver a comparação.")
else:
    recorte = dados_ano[dados_ano["Localidade"].isin(estados)].copy()
    if grupos:
        colunas = [colunas_grupos[grupo] for grupo in grupos]
        longo = recorte.melt(
            id_vars=["Localidade"],
            value_vars=colunas,
            var_name="Grupo",
            value_name="Horas semanais",
        )
        longo["Grupo"] = longo["Grupo"].map(rotulos)
        fig = px.bar(
            longo,
            x="Localidade",
            y="Horas semanais",
            color="Grupo",
            barmode="group",
            color_discrete_sequence=["#4776b4", "#6fa3d2", "#d7799a", "#a94f76"],
            labels={"Localidade": "Estado / região", "Horas semanais": "Horas por semana"},
        )
        fig.update_layout(legend_title_text="Grupo")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Escolha pelo menos um grupo para montar o gráfico.")

st.subheader("Evolucao ao longo dos anos")
if estados:
    historico = dados[dados["Localidade"].isin(estados + ["Brasil"])].copy()
    historico_longo = historico.melt(
        id_vars=["Localidade", "Ano"],
        value_vars=["Total geral"],
        var_name="Indicador",
        value_name="Horas semanais",
    )
    fig_linha = px.line(
        historico_longo,
        x="Ano",
        y="Horas semanais",
        color="Localidade",
        markers=True,
        labels={"Ano": "Ano", "Horas semanais": "Horas por semana", "Localidade": "Estado / região"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig_linha.update_layout()
    st.plotly_chart(fig_linha, use_container_width=True)

st.subheader("Panorama dos estados selecionados")
if estados:
    comparacao = dados_ano[dados_ano["Localidade"].isin(estados)].copy()
    comparacao["Homens"] = comparacao[["Homem branco", "Homem preto ou pardo"]].mean(axis=1)
    comparacao["Mulheres"] = comparacao[["Mulher branca", "Mulher preta ou parda"]].mean(axis=1)
    fig_box = px.box(
        comparacao.melt(
            id_vars=["Localidade"],
            value_vars=["Homens", "Mulheres"],
            var_name="Sexo",
            value_name="Horas semanais",
        ),
        x="Sexo",
        y="Horas semanais",
        color="Sexo",
        points="all",
        color_discrete_map={"Homens": "#4776b4", "Mulheres": "#c75e84"},
        labels={"Horas semanais": "Horas por semana"},
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

st.subheader("Por que acompanhar a economia do cuidado?")
texto, imagem = st.columns([1.4, 1])
with texto:
    st.write(
        "O trabalho de cuidar de pessoas e manter a casa funcionando sustenta a vida cotidiana, "
        "mas nem sempre é reconhecido nas decisões públicas. A diferença de horas entre grupos "
        "ajuda gestores a discutir serviços de cuidado, políticas de apoio às famílias e divisão "
        "mais equilibrada das tarefas."
    )
  


