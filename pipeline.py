import logging
import time
import datetime as dt
import pandas as pd
import requests
from config import BASE_DIR, GENEROS, ORDENACOES, PAUSA_SEGUNDOS, pasta_do_mes
from helpers import lista_para_texto
from extract.openlibrary import coletar_genero
from transform.normalizar import preparar_dados
from load.csv_writer import salvar_csv, salvar_historico

logger = logging.getLogger(__name__)


def main():
    hoje = dt.date.today()
    data_coleta = hoje.isoformat()
    mes = hoje.strftime("%Y-%m")

    logger.info("BOOK TRENDS — OPEN LIBRARY")
    logger.info("Data da coleta: %s", data_coleta)

    brutos = []
    for ordenacao, max_paginas in ORDENACOES.items():
        for nome_genero, termo in GENEROS.items():
            logger.info("Gênero: %s (ordenação: %s)", nome_genero, ordenacao)
            try:
                brutos.extend(coletar_genero(nome_genero, termo, ordenacao, max_paginas))
            except (requests.RequestException, RuntimeError):
                # "key" é a série principal: se ela falhar, a coleta falha.
                # As amostras extras são complemento e não derrubam a coleta.
                if ordenacao == "key":
                    raise
                logger.exception(
                    "Falha na amostra extra %s/%s; seguindo sem ela.", nome_genero, ordenacao
                )
            time.sleep(PAUSA_SEGUNDOS)

    if not brutos:
        logger.warning("Nenhum livro coletado. Encerrando.")
        return

    logger.info("Registros brutos coletados: %d", len(brutos))

    df_raw = pd.DataFrame(brutos)
    for coluna in df_raw.columns:
        df_raw[coluna] = df_raw[coluna].apply(lista_para_texto)
    salvar_csv(df_raw, pasta_do_mes("raw", hoje) / f"openlibrary_{data_coleta}.csv")

    df_livros, df_generos = preparar_dados(brutos, data_coleta)
    salvar_csv(df_livros, BASE_DIR / "processed" / "livros.csv")
    salvar_csv(df_generos, BASE_DIR / "processed" / "livros_generos.csv")
    salvar_historico(df_livros, pasta_do_mes("historico", hoje) / f"livros_{mes}.csv")

    logger.info("COLETA FINALIZADA")
    logger.info("Livros únicos: %d", len(df_livros))
    logger.info("Relações livro/gênero: %d", len(df_generos))
    logger.info("Registros brutos: %d", len(df_raw))
    logger.info("Arquivos gerados em: %s", BASE_DIR.resolve())
