"""
Combina a base coletada com dados do Google Books (merge por ISBN).
Uso (a partir da raiz do projeto), DEPOIS de rodar a coleta:
    python -m booktrends.etapas.merge
Lê  processed/livros.csv  e gera  processed/livros_merged.csv (snapshot,
sobrescrito a cada rodada), acrescentando as colunas gb_* (sinopse,
categorias, nota, etc.), e acumula em
historico/AAAA-MM/livros_merged_AAAA-MM.csv para manter série histórica.

A fila de consultas começa pelos livros conhecidos de
processed/livros_analise.csv (da rodada anterior), dos mais lidos para os
menos lidos; ver transform/merge_google_books.py.
"""

import datetime as dt
import logging
import os

import pandas as pd
from booktrends.config import BASE_DIR, pasta_do_mes
from booktrends.logging_setup import configurar_logging
from booktrends.load.csv_writer import salvar_historico
from booktrends.transform.merge_google_books import merge

logger = logging.getLogger(__name__)



def carregar_prioridade():
    """
    IDs dos livros conhecidos da última base de análise (etapas/tratar.py),
    dos mais lidos para os menos lidos, incluindo os works duplicados que
    foram juntados em cada obra. Na primeira rodada o arquivo ainda não
    existe e a fila segue só pelo want_to_read.
    """
    caminho = BASE_DIR / "processed" / "livros_analise.csv"
    if not caminho.exists():
        logger.info("Sem %s ainda: fila do Google Books só por want_to_read", caminho)
        return []
    analise = pd.read_csv(caminho, encoding="utf-8-sig", usecols=lambda c: c in {"id_livro", "ids_agrupados", "leitores"})
    if "leitores" in analise.columns:
        analise = analise.sort_values("leitores", ascending=False)
    ids = []
    for linha in analise.itertuples(index=False):
        agrupados = getattr(linha, "ids_agrupados", None)
        ids.extend(str(agrupados).split("; ") if isinstance(agrupados, str) else [linha.id_livro])
    return list(dict.fromkeys(ids))   # sem repetir, mantendo a ordem


def main():
    # falha cedo se a chave não estiver configurada
    if not os.environ.get("GOOGLE_BOOKS_API_KEY"):
        logger.error(
            "GOOGLE_BOOKS_API_KEY não encontrada. "
            "Defina no .env ou exporte a variável antes de rodar."
        )
        return

    entrada = BASE_DIR / "processed" / "livros.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python -m booktrends.etapas.coletar' primeiro.", entrada)
        return

    df = pd.read_csv(entrada, encoding="utf-8-sig")
    logger.info("Lendo %d livros de %s", len(df), entrada)

    df_merged = merge(df, prioridade=carregar_prioridade())

    saida = BASE_DIR / "processed" / "livros_merged.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(saida, index=False, encoding="utf-8-sig")

    hoje = dt.date.today()
    salvar_historico(
        df_merged, pasta_do_mes("historico", hoje) / f"livros_merged_{hoje:%Y-%m}.csv"
    )

    # feedback: quantos foram efetivamente enriquecidos
    colunas_gb = [c for c in df_merged.columns if c.startswith("gb_")]
    enriquecidos = int(df_merged[colunas_gb].notna().any(axis=1).sum()) if colunas_gb else 0
    logger.info(
        "-> %s (%d linhas, %d colunas; %d enriquecidos pelo Google Books)",
        saida,
        len(df_merged),
        len(df_merged.columns),
        enriquecidos,
    )


if __name__ == "__main__":
    configurar_logging()
    main()
