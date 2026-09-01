import time
import datetime as dt
import pandas as pd
from config import BASE_DIR, GENEROS, PAUSA_SEGUNDOS
from helpers import lista_para_texto
from extract.openlibrary import coletar_genero
from transform.normalizar import preparar_dados
from load.csv_writer import salvar_csv, salvar_historico

def main():
    hoje = dt.date.today()
    data_coleta = hoje.isoformat()
    mes = hoje.strftime("%Y-%m")

    print("BOOK TRENDS — OPEN LIBRARY")
    print(f"Data da coleta: {data_coleta}\n")

    brutos = []
    for nome_genero, termo in GENEROS.items():
        print(f"\nGênero: {nome_genero}")
        brutos.extend(coletar_genero(nome_genero, termo))
        time.sleep(PAUSA_SEGUNDOS)

    if not brutos:
        print("Nenhum livro coletado. Encerrando.")
        return

    print("Registros brutos coletados:", len(brutos))

    df_raw = pd.DataFrame(brutos)
    for coluna in df_raw.columns:
        df_raw[coluna] = df_raw[coluna].apply(lista_para_texto)
    salvar_csv(df_raw, BASE_DIR / "raw" / f"openlibrary_{data_coleta}.csv")

    df_livros, df_generos = preparar_dados(brutos, data_coleta)
    salvar_csv(df_livros, BASE_DIR / "processed" / "livros.csv")
    salvar_csv(df_generos, BASE_DIR / "processed" / "livros_generos.csv")
    salvar_historico(df_livros, BASE_DIR / "historico" / f"livros_{mes}.csv")

    print("COLETA FINALIZADA")
    print(f"Livros únicos: {len(df_livros)}")
    print(f"Relações livro/gênero: {len(df_generos)}")
    print(f"Registros brutos: {len(df_raw)}")
    print("\nArquivos gerados em:")
    print(BASE_DIR.resolve())