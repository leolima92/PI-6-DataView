"""
Curva de sobrevivência dos livros por gênero (issue #9).

Pergunta: quanto tempo um livro continua relevante? Para cada faixa de
idade (anos desde a publicação), calcula a fração dos livros que continuam
"vivos", ou seja, com pelo menos LIMIAR_VIVO leitores hoje (por padrão, a
mediana de leitores da base).

Lê  processed/perfis_livros.csv  (gerado por analise_perfis.py) e grava:

    processed/sobrevivencia.csv                     tabela gênero × faixa de idade
    analise/graficos/sobrevivencia_por_genero.png   um painel por gênero

Uso (a partir da raiz do projeto):
    python analise_sobrevivencia.py

Cuidado ao interpretar (viés de sobrevivência): a base só tem livros que
foram relevantes em algum momento (ver MIN_LEITORES / MIN_EDICOES no
config). A curva mede, entre os livros que um dia foram conhecidos, quantos
continuam sendo lidos com o passar dos anos, e não a chance de qualquer
livro publicado sobreviver.
"""

import logging

import pandas as pd

from config import BASE_DIR, FAIXAS_IDADE, LIMIAR_VIVO, MIN_LIVROS_PONTO
from load.csv_writer import salvar_csv
from logging_setup import configurar_logging

logger = logging.getLogger(__name__)

TODOS = "Todos os gêneros"
MIN_PONTOS_PAINEL = 4   # gênero com menos faixas válidas que isso fica fora do gráfico

# cores (paleta de referência da skill de dataviz, modo claro)
COR_SERIE = "#2a78d6"
COR_REFERENCIA = "#a3a29c"
COR_TEXTO = "#0b0b0b"
COR_TEXTO_2 = "#52514e"
COR_GRADE = "#e6e5e0"
COR_FUNDO = "#fcfcfb"


def _rotulo_faixa(inicio, fim):
    return f"{inicio}+" if fim is None else f"{inicio}–{fim - 1}"


def calcular(perfis, limiar=None):
    """Tabela: genero, faixa_idade, ordem, livros, vivos, pct_vivos, exibir."""
    df = perfis.dropna(subset=["idade", "genero_principal"]).copy()
    limiar = df["leitores"].median() if limiar is None else limiar
    df["vivo"] = df["leitores"] >= limiar

    limites = [*FAIXAS_IDADE, float("inf")]
    rotulos = [
        _rotulo_faixa(ini, None if fim == float("inf") else int(fim))
        for ini, fim in zip(limites[:-1], limites[1:])
    ]
    df["faixa_idade"] = pd.cut(df["idade"], limites, right=False, labels=rotulos)

    todos = df.assign(genero_principal=TODOS)
    tabela = (
        pd.concat([df, todos])
        .groupby(["genero_principal", "faixa_idade"], observed=False)
        .agg(livros=("vivo", "size"), vivos=("vivo", "sum"))
        .reset_index()
        .rename(columns={"genero_principal": "genero"})
    )
    tabela["ordem"] = tabela["faixa_idade"].cat.codes
    tabela["pct_vivos"] = (tabela["vivos"] / tabela["livros"]).where(tabela["livros"] > 0).round(3)
    tabela["exibir"] = tabela["livros"] >= MIN_LIVROS_PONTO
    tabela["limiar_leitores"] = limiar
    tabela["faixa_idade"] = tabela["faixa_idade"].astype(str)
    logger.info("Livro 'vivo' = pelo menos %.0f leitores hoje", limiar)
    return tabela.sort_values(["genero", "ordem"]).reset_index(drop=True)


def desenhar(tabela, caminho):
    """Small multiples: um painel por gênero + a curva geral em cinza."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    validos = tabela[tabela["exibir"]]
    pontos = validos[validos["genero"] != TODOS].groupby("genero").size()
    generos = pontos[pontos >= MIN_PONTOS_PAINEL].index.tolist()
    fora = sorted(set(tabela["genero"]) - set(generos) - {TODOS})
    # ordena os painéis pela sobrevivência média (quem dura mais primeiro)
    media = validos[validos["genero"].isin(generos)].groupby("genero")["pct_vivos"].mean()
    generos = media.sort_values(ascending=False).index.tolist()

    faixas = tabela.drop_duplicates("ordem").sort_values("ordem")["faixa_idade"].tolist()
    geral = validos[validos["genero"] == TODOS]

    colunas = 4
    linhas = -(-len(generos) // colunas)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, eixos = plt.subplots(
        linhas, colunas, figsize=(3.2 * colunas, 2.7 * linhas + 0.9),
        sharex=True, sharey=True, facecolor=COR_FUNDO,
    )
    eixos = eixos.ravel()

    for eixo, genero in zip(eixos, generos):
        serie = validos[validos["genero"] == genero]
        eixo.set_facecolor(COR_FUNDO)
        eixo.plot(geral["ordem"], geral["pct_vivos"], color=COR_REFERENCIA, lw=1.5, ls="--", zorder=1)
        eixo.plot(
            serie["ordem"], serie["pct_vivos"], color=COR_SERIE, lw=2, marker="o", ms=5,
            markeredgecolor=COR_FUNDO, markeredgewidth=1.5, zorder=2,
        )
        n = int(serie["livros"].sum())
        eixo.set_title(f"{genero}  ·  {n} livros", loc="left", color=COR_TEXTO, fontsize=10, fontweight="bold")
        eixo.set_ylim(0, 1)
        eixo.set_yticks([0, 0.25, 0.5, 0.75, 1])
        eixo.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
        eixo.set_xticks(range(len(faixas)))
        eixo.set_xticklabels(faixas, rotation=45, ha="right")
        eixo.grid(axis="y", color=COR_GRADE, lw=0.8)
        eixo.tick_params(colors=COR_TEXTO_2, length=0, labelbottom=True)
        for lado in ("top", "right", "left"):
            eixo.spines[lado].set_visible(False)
        eixo.spines["bottom"].set_color(COR_GRADE)

    for eixo in eixos[len(generos):]:
        eixo.set_visible(False)

    limiar = tabela["limiar_leitores"].iloc[0]
    fig.suptitle(
        "Quanto tempo um livro continua sendo lido?",
        x=0.01, ha="left", fontsize=14, fontweight="bold", color=COR_TEXTO,
    )
    nota = (
        f"% dos livros de cada idade com pelo menos {limiar:.0f} leitores hoje (mediana da base). "
        "Linha tracejada cinza = todos os gêneros. "
        f"Faixas com menos de {MIN_LIVROS_PONTO} livros omitidas."
    )
    if fora:
        nota += f"\nSem dados suficientes para painel: {', '.join(fora)}."
    nota += "\nBase: só livros que já foram conhecidos (viés de sobrevivência). Fonte: Open Library."
    fig.text(0.01, 0.005, nota, fontsize=8, color=COR_TEXTO_2, va="bottom")
    fig.tight_layout(rect=(0, 0.12, 1, 0.95), h_pad=2.5)
    fig.text(0.5, 0.095, "Idade do livro (anos desde a publicação)", ha="center", color=COR_TEXTO_2, fontsize=9)

    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=150, facecolor=COR_FUNDO)
    plt.close(fig)
    logger.info("-> %s (%d painéis)", caminho, len(generos))


def main():
    entrada = BASE_DIR / "processed" / "perfis_livros.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python analise_perfis.py' primeiro.", entrada)
        return

    perfis = pd.read_csv(entrada, encoding="utf-8-sig", low_memory=False)
    tabela = calcular(perfis, LIMIAR_VIVO)
    salvar_csv(tabela, BASE_DIR / "processed" / "sobrevivencia.csv")
    desenhar(tabela, BASE_DIR / "analise" / "graficos" / "sobrevivencia_por_genero.png")

    resumo = tabela[tabela["exibir"]].groupby("genero")["pct_vivos"].agg(["first", "last", "mean"])
    resumo.columns = ["mais_novos", "mais_velhos", "media"]
    logger.info("Sobrevivência por gênero:\n%s", resumo.round(2).sort_values("media", ascending=False).to_string())


if __name__ == "__main__":
    configurar_logging()
    main()
