"""
Trata o histórico consolidado e gera a base para visualização.

Lê  historico/livros_consolidado.csv  (gerado por etapas/consolidar.py)
e grava:

    historico/livros_tratado.csv   série completa limpa e sem works duplicados,
                                   com as flags conhecido / no_periodo / tem_pt
    processed/livros_analise.csv   uma linha por obra (última coleta), só as
                                   conhecidas e publicadas até ANO_MAX_PUBLICACAO,
                                   com sinopse/categorias do Google Books quando houver
    processed/livros_top.csv       lista rápida dos mais lidos por gênero principal, para
                                   conferir quais livros estão na base

Uso (a partir da raiz do projeto):
    python -m booktrends.etapas.tratar

Ver transform/tratamento.py para as regras.
"""

import logging

import pandas as pd

from booktrends.config import BASE_DIR
from booktrends.load.csv_writer import salvar_csv
from booktrends.logging_setup import configurar_logging
from booktrends.transform.titulos import aplicar_titulos
from booktrends.transform.tratamento import tratar

logger = logging.getLogger(__name__)

TOP_POR_GENERO = 30
COLUNAS_GB = ["gb_categorias", "gb_descricao", "gb_link"]


def _anexar_google_books(atual):
    """Traz campos estáticos do Google Books, por ID (canônico ou agrupado)."""
    caminho = BASE_DIR / "processed" / "livros_merged.csv"
    if not caminho.exists():
        return atual
    gb = pd.read_csv(caminho, encoding="utf-8-sig", usecols=lambda c: c == "id_livro" or c in COLUNAS_GB)
    gb = gb.dropna(subset=[c for c in COLUNAS_GB if c in gb.columns], how="all")
    if gb.empty:
        return atual

    # um work duplicado pode ser o que tem os dados do Google Books
    ids = atual[["id_livro", "ids_agrupados"]].copy()
    ids["id_gb"] = ids["ids_agrupados"].fillna(ids["id_livro"]).str.split("; ")
    ids = ids.explode("id_gb").merge(gb, left_on="id_gb", right_on="id_livro", suffixes=("", "_gb"))
    ids = ids.drop_duplicates("id_livro")[["id_livro", *[c for c in COLUNAS_GB if c in ids.columns]]]
    logger.info("Google Books: %d de %d obras com dados", len(ids), len(atual))
    return atual.merge(ids, on="id_livro", how="left")


def _top_por_genero(atual):
    top = (
        atual.sort_values("leitores", ascending=False)
        .groupby("genero_principal", group_keys=False)
        .head(TOP_POR_GENERO)
    )
    colunas = [
        "genero_principal", "genero_fonte", "titulo_exibicao", "titulo", "autor_principal",
        "ano_publicacao", "leitores", "qtd_edicoes", "nota_media", "tem_pt",
    ]
    return top[colunas].sort_values(["genero_principal", "leitores"], ascending=[True, False]).reset_index(drop=True)


def main():
    entrada = BASE_DIR / "historico" / "livros_consolidado.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python -m booktrends.etapas.consolidar' primeiro.", entrada)
        return

    hist = pd.read_csv(entrada, encoding="utf-8-sig", low_memory=False)
    tratado, atual = tratar(hist)
    atual = _anexar_google_books(atual)
    atual = aplicar_titulos(atual)  # títulos em pt já buscados (cache)

    salvar_csv(tratado, BASE_DIR / "historico" / "livros_tratado.csv")
    salvar_csv(atual, BASE_DIR / "processed" / "livros_analise.csv")
    top = _top_por_genero(atual)
    salvar_csv(top, BASE_DIR / "processed" / "livros_top.csv")

    for genero, bloco in top.groupby("genero_principal"):
        logger.info(
            "Mais lidos em %s: %s", genero,
            " | ".join(f"{t} ({a})" for t, a in bloco.head(5)[["titulo_exibicao", "autor_principal"]].itertuples(index=False)),
        )


if __name__ == "__main__":
    configurar_logging()
    main()
