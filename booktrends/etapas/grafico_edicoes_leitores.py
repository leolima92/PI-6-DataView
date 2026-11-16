
"""Gráfico de edições × leitores por perfil de popularidade.

Issue #11 — Book Trends.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Localizar a raiz do projeto a partir deste arquivo
RAIZ_PROJETO = Path(__file__).resolve().parents[2]


def carregar_dados(caminho_csv: Path) -> pd.DataFrame:
    """Carrega os perfis dos livros e valida as colunas necessárias."""

    colunas_obrigatorias = [
        "id_livro",
        "titulo_exibicao",
        "autor_principal",
        "qtd_edicoes",
        "leitores",
        "perfil",
        "genero_principal",
        "periodo",
    ]

    if not caminho_csv.is_file():
        raise FileNotFoundError(
            f"Arquivo de perfis não encontrado: {caminho_csv}"
        )

    df = pd.read_csv(caminho_csv)

    faltantes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {faltantes}"
        )

    return df



def criar_grafico(df: pd.DataFrame) -> go.Figure:
    """Cria o gráfico interativo de edições × leitores por perfil."""

    # Manter somente valores positivos para os eixos logarítmicos
    dados_grafico = df.loc[
        (df["qtd_edicoes"] > 0) &
        (df["leitores"] > 0)
    ].copy()

    # Ordem dos perfis na legenda
    ordem_perfis = [
        "Clássico vivo",
        "Fenômeno recente",
        "Esquecido",
        "Redescoberto / em alta",
        "Estável",
    ]

    # Paleta de cores para diferenciar os perfis
    cores_perfis = {
        "Clássico vivo": "#8B5CF6",
        "Fenômeno recente": "#F59E0B",
        "Esquecido": "#EF4444",
        "Redescoberto / em alta": "#10B981",
        "Estável": "#CBD5E1",
    }

    fig = px.scatter(
        dados_grafico,
        x="qtd_edicoes",
        y="leitores",
        color="perfil",
        custom_data=[
            "genero_principal",  # índice 0
            "periodo",           # índice 1
            "qtd_edicoes",       # índice 2
            "leitores",          # índice 3
            "titulo_exibicao",  # índice 4
            "autor_principal",   # índice 5
        ],
        category_orders={"perfil": ordem_perfis},
        color_discrete_map=cores_perfis,
        log_x=True,
        log_y=True,
        hover_name="titulo_exibicao",
        hover_data={
            "autor_principal": True,
            "genero_principal": True,
            "periodo": True,
            "qtd_edicoes": ":,",
            "leitores": ":,",
            "perfil": False,
        },
        labels={
            "qtd_edicoes": "Quantidade de edições",
            "leitores": "Quantidade de leitores",
            "perfil": "Perfil de popularidade",
            "autor_principal": "Autor",
            "genero_principal": "Gênero",
            "periodo": "Período",
        },
        title="Livros que desafiam o tempo: edições × leitores",
    )

    # Destacar os perfis principais e deixar Estável em segundo plano
    for trace in fig.data:
        # Tooltip construído a partir do registro do próprio ponto
        trace.hovertemplate = (
            "<b>%{customdata[4]}</b>"
            "<br>Autor: %{customdata[5]}"
            "<br>Gênero: %{customdata[0]}"
            "<br>Período: %{customdata[1]}"
            "<br>Edições: %{customdata[2]}"
            "<br>Leitores: %{customdata[3]}"
            "<extra></extra>"
        )

        if trace.name == "Estável":
            trace.update(
                marker=dict(
                    size=4,
                    opacity=0.16,
                    color="#94A3B8"
                )
            )
        else:
            trace.update(
                marker=dict(
                    size=8,
                    opacity=0.75,
                    line=dict(
                        width=0.4,
                        color="white"
                    )
                )
            )

    # Layout geral
    fig.update_layout(
        template="plotly_white",
        height=750,
        title_x=0.5,
        legend_title_text="Perfil de popularidade",
        hovermode="closest",
        margin=dict(l=80, r=40, t=100, b=100),
    )

    fig.update_xaxes(
        title="Quantidade de edições (escala logarítmica)",
        tickmode="array",
        tickvals=[1, 10, 100, 1000, 10000],
        ticktext=["1", "10", "100", "1.000", "10.000"],
        showgrid=True,
    )

    fig.update_yaxes(
        title="Quantidade de leitores (escala logarítmica)",
        tickmode="array",
        tickvals=[1, 10, 100, 1000, 10000, 100000],
        ticktext=["1", "10", "100", "1.000", "10.000", "100.000"],
        showgrid=True,
    )

    # Registrar a quantidade de livros não exibidos
    excluidos = len(df) - len(dados_grafico)

    fig.add_annotation(
        text=f"{len(dados_grafico):,} livros exibidos | "
             f"{excluidos} excluídos por valores zero ou negativos",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.15,
        showarrow=False,
        font=dict(size=12, color="#64748B"),
    )


    # Livros selecionados para destaque na apresentação
    livros_destaque = {
        "OL1168083W": "1984",
        "OL796465W": "O Alquimista",
        "OL18020194W": "É assim que acaba",
        "OL1088779W": "The Brown Fairy Book",
        "OL1088783W": "The Crimson Fairy Book",
    }

    # Posicionamento individual dos rótulos
    posicoes_rotulos = [
        "top right",      # 1984
        "top left",       # O Alquimista
        "top left",       # É assim que acaba
        "bottom right",   # The Brown Fairy Book
        "top right",      # The Crimson Fairy Book
    ]

    for indice, (id_livro, nome) in enumerate(livros_destaque.items()):
        livro = dados_grafico.loc[
            dados_grafico["id_livro"] == id_livro
        ]

        if livro.empty:
            print(f"Aviso: livro não encontrado: {nome}")
            continue

        registro = livro.iloc[0]
        perfil = registro["perfil"]

        fig.add_trace(
            go.Scatter(
                x=[registro["qtd_edicoes"]],
                y=[registro["leitores"]],
                customdata=[[
                    registro["genero_principal"],
                    registro["periodo"],
                    registro["qtd_edicoes"],
                    registro["leitores"],
                ]],
                mode="markers+text",
                text=[nome],
                textposition=posicoes_rotulos[indice],
                textfont=dict(size=12, color="#243047"),
                marker=dict(
                    size=15,
                    symbol="diamond",
                    color=cores_perfis[perfil],
                    line=dict(width=2, color="white"),
                ),
                name=f"Destaque: {nome}",
                showlegend=False,
                hovertemplate=(
                    f"<b>{nome}</b>"
                    f"<br>Autor: {registro['autor_principal']}"
                    f"<br>Perfil: {perfil}"
                    f"<br>Edições: {registro['qtd_edicoes']:,}"
                    f"<br>Leitores: {registro['leitores']:,}"
                    "<extra></extra>"
                ),
            )
        )

    # Tooltips com fundo da cor do perfil
    fig.update_layout(
        hoverlabel=dict(
            font=dict(
                family="Arial",
                size=13,
            ),
        )
    )

    for trace in fig.data:
        perfil = trace.name

        if perfil in cores_perfis:
            trace.hoverlabel.bgcolor = cores_perfis[perfil]
            trace.hoverlabel.font.color = (
                "#243047" if perfil == "Estável" else "white"
            )

    # Aplicar as cores também aos livros destacados
    for trace in fig.data:
        if trace.name.startswith("Destaque:"):
            cor = trace.marker.color
            trace.hoverlabel.bgcolor = cor
            trace.hoverlabel.font.color = "white"


    return fig

def criar_script_filtros() -> str:
    """Adiciona filtros interativos de gênero e período ao HTML."""

    return """
    const grafico = document.getElementById('{plot_id}');

    // Guardar uma cópia dos dados originais de cada trace
    const originais = grafico.data.map(trace => ({
        name: trace.name || '',
        customdata: (trace.customdata || []).map(item => Array.from(item)),
        text: trace.text
            ? (Array.isArray(trace.text) ? Array.from(trace.text) : [trace.text])
            : null
    }));

    // Criar os controles acima do gráfico
    const painel = document.createElement('div');
    painel.style.cssText = `
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        justify-content: center;
        gap: 16px;
        padding: 20px;
        font-family: Arial, sans-serif;
        color: #243047;
    `;

    function criarSeletor(titulo, valores) {
        const grupo = document.createElement('label');
        grupo.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 7px;
            font-size: 13px;
            font-weight: 600;
        `;

        const texto = document.createElement('span');
        texto.textContent = titulo;

        const select = document.createElement('select');
        select.style.cssText = `
            min-width: 220px;
            padding: 11px 14px;
            border: 1px solid #CBD5E1;
            border-radius: 9px;
            background: white;
            color: #243047;
            font-size: 14px;
            cursor: pointer;
        `;

        for (const valor of valores) {
            const option = document.createElement('option');
            option.value = valor;
            option.textContent = valor;
            select.appendChild(option);
        }

        grupo.append(texto, select);
        painel.appendChild(grupo);

        return select;
    }

    const todosDados = originais.flatMap(t => t.customdata);

    const generos = [...new Set(
        todosDados.map(item => String(item[0]))
    )].sort((a, b) => a.localeCompare(b, 'pt-BR'));

    const periodos = [...new Set(
        todosDados.map(item => String(item[1]))
    )].sort((a, b) => a.localeCompare(b, 'pt-BR'));

    const filtroGenero = criarSeletor(
        'Gênero literário',
        ['Todos os gêneros', ...generos]
    );

    const filtroPeriodo = criarSeletor(
        'Período de publicação',
        ['Todos os períodos', ...periodos]
    );

    const limpar = document.createElement('button');
    limpar.textContent = 'Limpar filtros';
    limpar.style.cssText = `
        padding: 11px 18px;
        border: 1px solid #CBD5E1;
        border-radius: 9px;
        background: #F1F5F9;
        color: #243047;
        font-size: 14px;
        cursor: pointer;
    `;

    painel.appendChild(limpar);

    const contador = document.createElement('div');
    contador.style.cssText = `
        width: 100%;
        text-align: center;
        font-size: 13px;
        color: #64748B;
    `;
    painel.appendChild(contador);

    grafico.parentNode.insertBefore(painel, grafico);

    function aplicarFiltros() {
        let quantidade = 0;

        for (let i = 0; i < originais.length; i++) {
            const original = originais[i];

            const filtrados = original.customdata.filter(item => {
                const genero = String(item[0]);
                const periodo = String(item[1]);

                const generoOk =
                    filtroGenero.value === 'Todos os gêneros' ||
                    genero === filtroGenero.value;

                const periodoOk =
                    filtroPeriodo.value === 'Todos os períodos' ||
                    periodo === filtroPeriodo.value;

                return generoOk && periodoOk;
            });

            const novosX = filtrados.map(item => item[2]);
            const novosY = filtrados.map(item => item[3]);

            const atualizacao = {
                x: [novosX],
                y: [novosY],
                customdata: [filtrados]
            };

            if (original.text !== null) {
                const indices = original.customdata
                    .map((item, indice) => {
                        const generoOk =
                            filtroGenero.value === 'Todos os gêneros' ||
                            String(item[0]) === filtroGenero.value;

                        const periodoOk =
                            filtroPeriodo.value === 'Todos os períodos' ||
                            String(item[1]) === filtroPeriodo.value;

                        return generoOk && periodoOk ? indice : -1;
                    })
                    .filter(indice => indice !== -1);

                atualizacao.text = [
                    indices.map(indice => original.text[indice])
                ];
            }

            Plotly.restyle(grafico, atualizacao, [i]);

            if (!original.name.startsWith('Destaque:')) {
                quantidade += filtrados.length;
            }
        }

        contador.textContent =
            quantidade.toLocaleString('pt-BR') +
            ' livros encontrados nos filtros selecionados';
    }

    filtroGenero.addEventListener('change', aplicarFiltros);
    filtroPeriodo.addEventListener('change', aplicarFiltros);

    limpar.addEventListener('click', () => {
        filtroGenero.value = 'Todos os gêneros';
        filtroPeriodo.value = 'Todos os períodos';
        aplicarFiltros();
    });

    aplicarFiltros();
    """

def main():
    caminho_csv = RAIZ_PROJETO / "processed" / "perfis_livros.csv"

    df = carregar_dados(caminho_csv)

    print(f"Total de livros carregados: {len(df):,}")

    # Gerar a visualização
    fig = criar_grafico(df)

    # Criar pasta de saída
    pasta_saida = RAIZ_PROJETO / "analise" / "graficos"
    pasta_saida.mkdir(parents=True, exist_ok=True)

    caminho_html = pasta_saida / "edicoes_leitores_perfil.html"

    fig.write_html(
        caminho_html,
        include_plotlyjs=True,
        full_html=True,
        post_script=criar_script_filtros(),
    )

    print(f"Gráfico gerado: {caminho_html.resolve()}")
    print("Abra o arquivo HTML no navegador para visualizar.")



if __name__ == "__main__":
    main()
