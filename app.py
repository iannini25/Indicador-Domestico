import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Afazeres Domésticos | Indicadores",
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
    if isinstance(arquivo, bytes):
        arquivo = io.BytesIO(arquivo)

    planilha = pd.ExcelFile(arquivo)

    titulo = str(pd.read_excel(planilha, sheet_name=planilha.sheet_names[0], header=None).iloc[0, 0])
    if "cor ou ra" not in titulo.lower():
        raise ValueError(
            "a planilha não é a Tabela 1.1.1 (horas semanais por sexo e cor ou raça)"
        )

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
    .note {background: #fff8e8; border-left: 4px solid #e8a838; padding: 0.85rem 1rem; border-radius: 8px; color: #55451f;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏠 Cuidados e afazeres domésticos no Brasil")
st.markdown(
    '<p class="intro">Quantas horas por semana as pessoas dedicam ao trabalho de cuidado não remunerado? '
    "Explore as diferenças entre homens e mulheres, raça/cor e unidades da Federação.</p>",
    unsafe_allow_html=True,
)


with st.sidebar:
    st.header("Dados")
    arquivo_enviado = st.file_uploader(
        "Enviar outra planilha (.xls ou .xlsx)",
        type=["xls", "xlsx"],
        help="A planilha precisa seguir o formato da Tabela 1.1.1 do IBGE. Sem envio, usamos a planilha do projeto.",
    )

if arquivo_enviado is not None:
    try:
        dados = carregar_dados(arquivo_enviado.getvalue())
        st.sidebar.success(f"Usando: {arquivo_enviado.name}")
    except Exception as erro:
        st.sidebar.error(f"Não consegui ler o arquivo enviado: {erro}")
        st.error("O arquivo enviado não pôde ser lido. Envie uma planilha no formato da Tabela 1.1.1 do IBGE.")
        st.stop()
else:
    if not ARQUIVO_DADOS.exists():
        st.error("Não encontrei a planilha. Confira se o arquivo está na pasta conteudo.")
        st.stop()
    dados = carregar_dados(str(ARQUIVO_DADOS))
    st.sidebar.caption("Usando a planilha padrão do projeto (Tabela 1.1.1 — IBGE).")

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

st.subheader("Evolução ao longo dos anos")
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

st.divider()
st.subheader("Por que acompanhar a economia do cuidado?")
st.write(
    "O trabalho de cuidar de pessoas e manter a casa funcionando sustenta a vida cotidiana, "
    "mas nem sempre é reconhecido nas decisões públicas. A diferença de horas entre grupos "
    "ajuda gestores a discutir serviços de cuidado, políticas de apoio às famílias e divisão "
    "mais equilibrada das tarefas."
)


# --- Reportagens -----------------------------------------------------------
PASTA_IMAGENS = Path(__file__).parent / "imagens"

REPORTAGENS = [
    {
        "tema": "Carga Mental Feminina",
        "titulo": "PNAD: mulheres gastam quase o dobro de tempo no serviço doméstico",
        "veiculo": "Agência Brasil",
        "data": "11/08/2023",
        "resumo": (
            "Pela PNAD Contínua 2022, as mulheres dedicam cerca de 21,3 horas por semana aos "
            "afazeres domésticos e ao cuidado de pessoas, contra 11,7 horas dos homens. Além das "
            "horas visíveis, pesa a tarefa invisível de planejar e lembrar de tudo — a chamada "
            "carga mental."
        ),
        "link": "https://agenciabrasil.ebc.com.br/geral/noticia/2023-08/pnad-mulheres-gastam-quase-o-dobro-de-tempo-no-servico-domestico",
        "imagem": "carga-mental-feminina.jpg",
        "credito_imagem": "Foto: valtercirillo/Pixabay — publicada por Agência Brasil",
    },
    {
        "tema": "Economia do Cuidado",
        "titulo": "Batizado Brasil que Cuida, Plano Nacional de Cuidados sairá em breve",
        "veiculo": "Agência Brasil",
        "data": "19/03/2025",
        "resumo": (
            "O governo federal detalhou o Plano Nacional de Cuidados, que organiza serviços de "
            "cuidado para crianças, idosos e pessoas com deficiência. A proposta reconhece o "
            "cuidado como trabalho e busca reduzir a sobrecarga que hoje recai sobre as mulheres."
        ),
        "link": "https://agenciabrasil.ebc.com.br/direitos-humanos/noticia/2025-03/batizado-brasil-que-cuida-plano-nacional-de-cuidados-saira-em-breve",
        "imagem": "economia-do-cuidado.jpg",
        "credito_imagem": "Foto: Rafa Neddermeyer/Agência Brasil",
    },
]

st.subheader("Reportagens sobre o tema")
st.caption(
    "Matérias que ajudam a interpretar os números do painel. As imagens são as próprias fotos "
    "das reportagens, com os créditos originais."
)

colunas_reportagens = st.columns(len(REPORTAGENS))
for coluna, reportagem in zip(colunas_reportagens, REPORTAGENS):
    with coluna:
        st.markdown(f"**{reportagem['tema']}**")

        caminho_imagem = PASTA_IMAGENS / reportagem["imagem"]
        if caminho_imagem.exists():
            st.image(str(caminho_imagem), use_container_width=True)
        else:
            st.info("Imagem não encontrada na pasta imagens.")
        st.caption(reportagem["credito_imagem"])

        st.markdown(f"##### {reportagem['titulo']}")
        st.write(reportagem["resumo"])
        st.caption(f"Fonte: {reportagem['veiculo']} — {reportagem['data']}")
        st.markdown(f"[Ler a reportagem completa]({reportagem['link']})")

st.markdown(
    '<div class="note">Fonte dos dados do painel: IBGE — PNAD Contínua, Tabela 1.1.1 '
    "(número médio de horas semanais dedicadas aos cuidados de pessoas e/ou afazeres domésticos).</div>",
    unsafe_allow_html=True,
)
