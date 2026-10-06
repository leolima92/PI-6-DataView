"""
Classifica cada livro num perfil de popularidade ao longo do tempo.

Pergunta do projeto: por que alguns livros continuam sendo lidos décadas
depois de publicados, enquanto outros desaparecem do interesse dos leitores?

Lê historico/livros_consolidado.csv (gerado por consolidar_historico.py),
compara a primeira e a última coleta de cada livro e grava:

    processed/perfis_livros.csv               (foto atual, para o Power BI)
    analise/AAAA-MM/perfis_AAAA-MM-DD.csv     (cópia datada, por mês)

Uso:
    python analise_perfis.py

Perfis (limiares em PERCENTIL / ANO_* abaixo):
- Clássico vivo:          antigo, muito reeditado e ainda muito lido
- Esquecido:              antigo e muito reeditado, mas quase sem leitores hoje
- Redescoberto / em alta: antigo e ganhando leitores rápido no período
- Fenômeno recente:       recente, muito lido mesmo com poucas edições
- Cauda longa:            o resto (a maioria) — pouca leitura

"Leitores" = want_to_read + currently_reading + already_read.
Nº de edições funciona como medida de relevância passada (só é reeditado o
que teve procura); leitores medem o interesse atual.
"""

import datetime as dt
import logging

import pandas as pd

from config import BASE_DIR, pasta_do_mes
from load.csv_writer import salvar_csv
from logging_setup import configurar_logging

logger = logging.getLogger(__name__)

PERCENTIL = 0.90            # "muito" = top 10%
ANO_CLASSICO = 1976         # publicado há 50+ anos
ANO_ANTIGO = 1996           # publicado há 30+ anos
ANO_RECENTE = 1997          # "recente" a partir daqui
MAX_LEITORES_ESQUECIDO = 2
MIN_CRESCIMENTO = 0.10      # +10% de leitores no período...
MIN_GANHO = 3               # ...e pelo menos 3 leitores novos

COLUNAS_LEITORES = ["want_to_read", "currently_reading", "already_read"]


def _leitores(df):
    return df[COLUNAS_LEITORES].fillna(0).sum(axis=1)


def classificar(hist):
    """Recebe o histórico consolidado e devolve uma linha por livro com o perfil."""
    hist = hist.copy()
    hist["leitores"] = _leitores(hist)
    hist = hist.sort_values("data_coleta")

    # drop_duplicates (e não groupby.first/last) para não misturar colunas
    # de coletas diferentes quando há valores vazios
    primeiro = hist.drop_duplicates("id_livro", keep="first").set_index("id_livro")
    df = hist.drop_duplicates("id_livro", keep="last").set_index("id_livro")

    df["data_primeira_coleta"] = primeiro["data_coleta"]
    df["leitores_inicio"] = primeiro["leitores"]
    df["ganho_leitores"] = df["leitores"] - df["leitores_inicio"]
    df["crescimento_pct"] = df["ganho_leitores"] / (df["leitores_inicio"] + 5) * 100

    # limiares calculados só na amostra "key" (sem viés de popularidade),
    # quando a coluna existir; senão em todos
    base = df
    if "amostra" in df.columns:
        sem_vies = df["amostra"].fillna("key").str.contains("key")
        if sem_vies.any():
            base = df[sem_vies]
    lim_edicoes = base["qtd_edicoes"].quantile(PERCENTIL)
    lim_leitores = base["leitores"].quantile(PERCENTIL)
    logger.info(
        "Limiares (P%d): edições >= %.0f, leitores >= %.0f",
        PERCENTIL * 100, lim_edicoes, lim_leitores,
    )

    ano = df["ano_publicacao"]
    muito_editado = df["qtd_edicoes"] >= lim_edicoes
    muito_lido = df["leitores"] >= lim_leitores
    em_alta = (
        (df["leitores_inicio"] >= 3)
        & (df["crescimento_pct"] >= MIN_CRESCIMENTO * 100)
        & (df["ganho_leitores"] >= MIN_GANHO)
    )

    # cada regra sobrescreve as anteriores: a última da lista tem prioridade
    df["perfil"] = "Cauda longa"
    regras = [
        ("Fenômeno recente", (ano >= ANO_RECENTE) & muito_lido & ~muito_editado),
        ("Redescoberto / em alta", (ano <= ANO_ANTIGO) & em_alta),
        ("Esquecido", (ano <= ANO_ANTIGO) & muito_editado & (df["leitores"] <= MAX_LEITORES_ESQUECIDO)),
        ("Clássico vivo", (ano <= ANO_CLASSICO) & muito_lido & muito_editado),
    ]
    for nome, mascara in regras:
        df.loc[mascara, "perfil"] = nome

    df["idade"] = dt.date.today().year - ano
    colunas = [
        "titulo", "autor", "ano_publicacao", "idade", "generos", "qtd_edicoes",
        "nota_media", "qtd_avaliacoes", *COLUNAS_LEITORES, "leitores",
        "data_primeira_coleta", "data_coleta", "leitores_inicio",
        "ganho_leitores", "crescimento_pct", "perfil",
    ]
    if "amostra" in df.columns:
        colunas.append("amostra")
    return df[colunas].reset_index()


def main():
    entrada = BASE_DIR / "historico" / "livros_consolidado.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python consolidar_historico.py' primeiro.", entrada)
        return

    hist = pd.read_csv(entrada, encoding="utf-8-sig")
    perfis = classificar(hist)

    hoje = dt.date.today()
    salvar_csv(perfis, BASE_DIR / "processed" / "perfis_livros.csv")
    salvar_csv(perfis, pasta_do_mes("analise", hoje) / f"perfis_{hoje.isoformat()}.csv")

    resumo = perfis.groupby("perfil").agg(
        livros=("id_livro", "size"),
        leitores=("leitores", "sum"),
        ganho=("ganho_leitores", "sum"),
    )
    resumo["pct_leitores"] = resumo["leitores"] / resumo["leitores"].sum() * 100
    resumo["pct_ganho"] = resumo["ganho"] / resumo["ganho"].sum().clip(min=1) * 100
    logger.info("Perfis:\n%s", resumo.round(1).to_string())


if __name__ == "__main__":
    configurar_logging()
    main()
