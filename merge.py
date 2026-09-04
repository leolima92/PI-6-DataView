"""
Combina a base coletada com dados do Google Books (merge por ISBN).
Uso (a partir da raiz do projeto), DEPOIS de rodar a coleta:
    python merge.py
Lê  processed/livros.csv  e gera  processed/livros_merged.csv,
acrescentando as colunas gb_* (sinopse, categorias, nota, etc.).
"""

import logging

import pandas as pd
from config import BASE_DIR
from logging_setup import configurar_logging
from transform.google_books import merge

logger = logging.getLogger(__name__)


def main():
    entrada = BASE_DIR / "processed" / "livros.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python coletar.py' primeiro.", entrada)
        return

    df = pd.read_csv(entrada, encoding="utf-8-sig")
    df_merged = merge(df)

    saida = BASE_DIR / "processed" / "livros_merged.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(saida, index=False, encoding="utf-8-sig")

    logger.info(
        "-> %s (%d linhas, %d colunas)",
        saida,
        len(df_merged),
        len(df_merged.columns),
    )


if __name__ == "__main__":
    configurar_logging()
    main()
