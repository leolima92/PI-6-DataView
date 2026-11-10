"""
Classifica cada livro num perfil de popularidade ao longo do tempo.

Pergunta do projeto: por que alguns livros continuam sendo lidos décadas
depois de publicados, enquanto outros desaparecem do interesse dos leitores?

Lê historico/livros_tratado.csv (gerado por tratar.py), usa só as obras
conhecidas e publicadas até ANO_MAX_PUBLICACAO, compara a primeira e a
última coleta de cada livro e grava:

    processed/perfis_livros.csv               (foto atual, para o Power BI)
    analise/AAAA-MM/perfis_AAAA-MM-DD.csv     (cópia datada, por mês)

Uso:
    python analise_perfis.py

Cada livro é comparado com os livros do mesmo PERÍODO de publicação
(décadas; as antigas são juntadas até ter MIN_LIVROS_PERIODO livros): um
livro de 1950 com 200 edições é comparado com outros de 1950, não com um
de 2015. pct_leitores_periodo e pct_edicoes_periodo vão de 0 a 1 (posição
do livro dentro do período).

Perfis (limiares em PCT_* / ANO_* abaixo):
- Clássico vivo:          antigo, entre os mais reeditados e mais lidos do período
- Esquecido:              antigo, reeditado acima da mediana, mas entre os menos lidos do período
- Redescoberto / em alta: antigo e entre os que mais ganharam leitores (por 30 dias)
- Fenômeno recente:       recente e entre os 10% mais lidos do período
- Estável:                o resto — conhecido, sem destaque

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
from transform.titulos import aplicar_titulos

logger = logging.getLogger(__name__)

MIN_LIVROS_PERIODO = 50     # décadas antigas são juntadas até ter isso
PCT_ALTO = 0.75             # "entre os mais" = quartil de cima do período
PCT_BAIXO = 0.25            # "entre os menos" = quartil de baixo do período
PCT_FENOMENO = 0.90         # fenômeno recente: top 10% de leitores do período
PCT_ESQUECIDO_EDICOES = 0.50  # esquecido: edições acima da mediana do período...
                              # ...e leitores no quartil de baixo (PCT_BAIXO)
PCT_EM_ALTA = 0.90          # top 10% de crescimento (por 30 dias)
ANO_CLASSICO = 1976         # publicado há 50+ anos
ANO_ANTIGO = 1996           # publicado há 30+ anos
ANO_RECENTE = 1997          # "recente" a partir daqui
MIN_GANHO = 3               # em alta: pelo menos 3 leitores novos

COLUNAS_LEITORES = ["want_to_read", "currently_reading", "already_read"]


def _leitores(df):
    return df[COLUNAS_LEITORES].fillna(0).sum(axis=1)


def periodos(ano, minimo=MIN_LIVROS_PERIODO):
    """
    Agrupa os anos em períodos: cada década vira um período, mas as décadas
    antigas (com poucos livros) são juntadas, da mais antiga para a mais
    nova, até somar `minimo` livros. A última sobra é juntada ao anterior.
    Devolve uma Series de rótulos ("até 1899", "1900–1929", "1950s"...).
    """
    decada = (ano // 10 * 10).astype("Int64")
    contagem = decada.value_counts().sort_index()

    grupos, atual, soma = [], [], 0
    for dec, n in contagem.items():
        atual.append(dec)
        soma += n
        if soma >= minimo:
            grupos.append(atual)
            atual, soma = [], 0
    if atual:
        if grupos:
            grupos[-1].extend(atual)
        else:
            grupos.append(atual)

    rotulos = {}
    for i, g in enumerate(grupos):
        ini, fim = min(g), max(g) + 9
        if len(g) == 1:
            rotulo = f"{ini}s"
        elif i == 0:
            rotulo = f"até {fim}"
        else:
            rotulo = f"{ini}–{fim}"
        rotulos.update({dec: rotulo for dec in g})
    return decada.map(rotulos)


def classificar(hist):
    """Recebe o histórico tratado e devolve uma linha por livro com o perfil."""
    hist = hist.copy()
    for flag in ("conhecido", "no_periodo"):
        if flag in hist.columns:
            hist = hist[hist[flag].astype(str).str.lower() == "true"]
    hist["leitores"] = _leitores(hist)
    hist = hist.sort_values("data_coleta")
    ultima_coleta = hist["data_coleta"].max()

    # drop_duplicates (e não groupby.first/last) para não misturar colunas
    # de coletas diferentes quando há valores vazios
    primeiro = hist.drop_duplicates("id_livro", keep="first").set_index("id_livro")
    df = hist.drop_duplicates("id_livro", keep="last").set_index("id_livro")

    df["data_primeira_coleta"] = primeiro["data_coleta"]
    df["leitores_inicio"] = primeiro["leitores"]
    df["dias_acompanhado"] = (
        pd.to_datetime(df["data_coleta"]) - pd.to_datetime(df["data_primeira_coleta"])
    ).dt.days
    # crescimento só vale para quem está na última coleta e foi visto em
    # pelo menos 2 datas: senão a janela de comparação muda de livro a livro
    comparavel = (df["data_coleta"] == ultima_coleta) & (df["dias_acompanhado"] > 0)
    df["ganho_leitores"] = (df["leitores"] - df["leitores_inicio"]).where(comparavel)
    # +5 no denominador suaviza livros com poucos leitores (1 -> 2 não é +100%)
    df["crescimento_pct"] = df["ganho_leitores"] / (df["leitores_inicio"] + 5) * 100
    df["crescimento_pct_30d"] = df["crescimento_pct"] / df["dias_acompanhado"] * 30

    # posição de cada livro dentro do seu período de publicação (0 a 1)
    ano = df["ano_publicacao"]
    df["periodo"] = periodos(ano)
    por_periodo = df.groupby("periodo")
    df["pct_leitores_periodo"] = por_periodo["leitores"].rank(pct=True).round(3)
    df["pct_edicoes_periodo"] = por_periodo["qtd_edicoes"].rank(pct=True).round(3)

    pl, pe = df["pct_leitores_periodo"], df["pct_edicoes_periodo"]
    lim_crescimento = df["crescimento_pct_30d"].quantile(PCT_EM_ALTA)
    em_alta = (df["crescimento_pct_30d"] >= lim_crescimento) & (df["ganho_leitores"] >= MIN_GANHO)
    logger.info(
        "Períodos: %s | em alta: crescimento >= %.1f%% em 30 dias",
        ", ".join(f"{p} ({n})" for p, n in df["periodo"].value_counts(sort=False).sort_index().items()),
        lim_crescimento,
    )

    # cada regra sobrescreve as anteriores: a última da lista tem prioridade
    df["perfil"] = "Estável"
    regras = [
        ("Fenômeno recente", (ano >= ANO_RECENTE) & (pl >= PCT_FENOMENO)),
        ("Redescoberto / em alta", (ano <= ANO_ANTIGO) & em_alta),
        ("Esquecido", (ano <= ANO_ANTIGO) & (pe >= PCT_ESQUECIDO_EDICOES) & (pl <= PCT_BAIXO)),
        ("Clássico vivo", (ano <= ANO_CLASSICO) & (pe >= PCT_ALTO) & (pl >= PCT_ALTO)),
    ]
    for nome, mascara in regras:
        df.loc[mascara, "perfil"] = nome

    df["idade"] = dt.date.today().year - ano
    colunas = [
        "titulo", "autor_principal", "ano_publicacao", "idade", "genero_principal", "genero_fonte",
        "generos", "qtd_edicoes",
        "nota_media", "qtd_avaliacoes", *COLUNAS_LEITORES, "leitores",
        "data_primeira_coleta", "data_coleta", "dias_acompanhado", "leitores_inicio",
        "ganho_leitores", "crescimento_pct", "crescimento_pct_30d",
        "periodo", "pct_leitores_periodo", "pct_edicoes_periodo", "perfil",
    ]
    colunas += ["tem_pt", "amostra", "ids_agrupados"]
    return df[[c for c in colunas if c in df.columns]].reset_index()


def main():
    entrada = BASE_DIR / "historico" / "livros_tratado.csv"
    if not entrada.exists():
        logger.error("Não encontrei %s. Rode 'python tratar.py' primeiro.", entrada)
        return

    hist = pd.read_csv(entrada, encoding="utf-8-sig", low_memory=False)
    perfis = aplicar_titulos(classificar(hist))

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
