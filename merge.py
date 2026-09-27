"""
Combina a base coletada com dados do Google Books (merge por ISBN).
Uso (a partir da raiz do projeto), DEPOIS de rodar a coleta:
    python merge.py
Lê  processed/livros.csv  e gera  processed/livros_merged.csv (snapshot,
sobrescrito a cada rodada), acrescentando as colunas gb_* (sinopse,
categorias, nota, etc.), e acumula em
historico/livros_merged_{AAAA-MM}.csv para manter série histórica.
"""

import datetime as dt
import logging
import os

import pandas as pd
from dotenv import load_dotenv
from config import BASE_DIR
from logging_setup import configurar_logging
from load.csv_writer import salvar_historico
from transform.google_books import merge

logger = logging.getLogger(__name__)

load_dotenv()


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
        logger.error("Não encontrei %s. Rode 'python coletar.py' primeiro.", entrada)
        return

    df = pd.read_csv(entrada, encoding="utf-8-sig")
    logger.info("Lendo %d livros de %s", len(df), entrada)

    df_merged = merge(df)

    saida = BASE_DIR / "processed" / "livros_merged.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(saida, index=False, encoding="utf-8-sig")

    mes = dt.date.today().strftime("%Y-%m")
    salvar_historico(df_merged, BASE_DIR / "historico" / f"livros_merged_{mes}.csv")

    # feedback: quantos foram efetivamente enriquecidos
    enriquecidos = df_merged["gb_titulo"].notna().sum() if "gb_titulo" in df_merged else 0
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
