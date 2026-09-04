import logging
import time
import datetime as dt
import pandas as pd
from config import BASE_DIR, GENEROS, PAUSA_SEGUNDOS
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
    for nome_genero, termo in GENEROS.items():
        logger.info("Gênero: %s", nome_genero)
        brutos.extend(coletar_genero(nome_genero, termo))
        time.sleep(PAUSA_SEGUNDOS)

    if not brutos:
        logger.warning("Nenhum livro coletado. Encerrando.")
        return

    logger.info("Registros brutos coletados: %d", len(brutos))

    df_raw = pd.DataFrame(brutos)
    for coluna in df_raw.columns:
        df_raw[coluna] = df_raw[coluna].apply(lista_para_texto)
    salvar_csv(df_raw, BASE_DIR / "raw" / f"openlibrary_{data_coleta}.csv")

    df_livros, df_generos = preparar_dados(brutos, data_coleta)
    salvar_csv(df_livros, BASE_DIR / "processed" / "livros.csv")
    salvar_csv(df_generos, BASE_DIR / "processed" / "livros_generos.csv")
    salvar_historico(df_livros, BASE_DIR / "historico" / f"livros_{mes}.csv")

    logger.info("COLETA FINALIZADA")
    logger.info("Livros únicos: %d", len(df_livros))
    logger.info("Relações livro/gênero: %d", len(df_generos))
    logger.info("Registros brutos: %d", len(df_raw))
    logger.info("Arquivos gerados em: %s", BASE_DIR.resolve())
