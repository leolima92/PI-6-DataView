"""
Tratamento do histórico consolidado antes da análise e da visualização.

limpar          -> só IDs de obra (W), tipos certos, nulos consistentes
chave_obra      -> título + autor normalizados, para achar obras duplicadas
deduplicar      -> junta works duplicados da Open Library numa obra só
marcar_conhecidos -> flag "conhecido" (MIN_LEITORES ou MIN_EDICOES)
tratar          -> roda tudo e devolve (histórico tratado, foto atual)

A Open Library tem muitos works duplicados para o mesmo livro (ex.: um
work por edição antiga). Isso divide os leitores entre cópias e às vezes
dá ao livro o ano de uma reedição. Aqui as cópias viram uma obra só:
leitores, avaliações e edições são somados e o ano é o menor entre elas.
"""

import logging
import re
import unicodedata

import numpy as np
import pandas as pd

from config import ANO_MAX_PUBLICACAO, MIN_EDICOES, MIN_LEITORES

logger = logging.getLogger(__name__)

COLUNAS_LEITORES = ["want_to_read", "currently_reading", "already_read"]
COLUNAS_INTEIRAS = [
    "ano_publicacao", "paginas", "qtd_avaliacoes", "qtd_edicoes",
    *COLUNAS_LEITORES, "cover_id",
]
# somadas quando works duplicados viram uma obra só
COLUNAS_SOMA = ["qtd_avaliacoes", "qtd_edicoes", *COLUNAS_LEITORES]


def _texto_normalizado(valor):
    """Minúsculas, sem acento, sem subtítulo/parênteses e sem pontuação."""
    if not isinstance(valor, str) or not valor.strip():
        return ""
    texto = unicodedata.normalize("NFKD", valor)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    # "(Lord of the Isles 2)" e subtítulo saem, mas só se sobrarem 2+
    # palavras: "Novels (Black House / Talisman)" não pode virar "novels"
    curto = re.sub(r"[\(\[].*?[\)\]]", " ", texto).split(":")[0]
    if len(re.findall(r"[a-z0-9]+", curto)) >= 2:
        texto = curto
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def autor_principal(autor):
    """'Kazuo Umezu; Umezu Kazuo; ...' -> 'Kazuo Umezu'."""
    if not isinstance(autor, str) or not autor.strip():
        return None
    return autor.split(";")[0].strip()


def chave_obra(df):
    """Título + 1º autor normalizados. Sem autor, a chave é o próprio ID."""
    titulo = df["titulo"].map(_texto_normalizado)
    autor = df["autor_principal"].map(_texto_normalizado)
    chave = titulo + "|" + autor
    sem_chave = (titulo == "") | (autor == "")
    return chave.where(~sem_chave, "id|" + df["id_livro"])


def _juntar_textos(valores):
    """Une textos separados por '; ' sem repetir, em ordem alfabética."""
    itens = set()
    for valor in valores.dropna():
        itens.update(p.strip() for p in str(valor).split(";") if p.strip())
    return "; ".join(sorted(itens)) if itens else None


def limpar(hist):
    df = hist.copy()

    # só works ("...W"); IDs de edição ("...M") são descartados
    ids = df["id_livro"].astype(str)
    eh_obra = ids.str.match(r"^OL\d+W$")
    if (~eh_obra).any():
        logger.info("Descartando %d linhas com ID que não é de obra (W)", (~eh_obra).sum())
    df = df[eh_obra].copy()

    for coluna in [*COLUNAS_INTEIRAS, "nota_media"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    # ano impossível (0, 9183...) vira vazio
    ano_atual = pd.Timestamp.today().year
    fora = (df["ano_publicacao"] <= 0) | (df["ano_publicacao"] > ano_atual)
    df.loc[fora, "ano_publicacao"] = np.nan

    # a Open Library omite o contador quando ele é zero
    df[COLUNAS_LEITORES] = df[COLUNAS_LEITORES].fillna(0)
    df["qtd_avaliacoes"] = df["qtd_avaliacoes"].fillna(0)
    # nota 0 com 0 avaliações não é nota: vira vazio
    df.loc[df["qtd_avaliacoes"] <= 0, "nota_media"] = np.nan

    df["titulo"] = df["titulo"].astype("string").str.strip()
    df["autor_principal"] = df["autor"].map(autor_principal)
    return df


def deduplicar(df):
    """Junta works duplicados (mesma chave de obra) numa linha por data."""
    df = df.copy()
    df["leitores"] = df[COLUNAS_LEITORES].sum(axis=1)
    df["chave_obra"] = chave_obra(df)

    # obra canônica = o work com mais leitores na última coleta em que apareceu
    ultima = df.sort_values("data_coleta").drop_duplicates("id_livro", keep="last")
    canonico = (
        ultima.sort_values(["leitores", "qtd_edicoes"], ascending=False)
        .drop_duplicates("chave_obra")
        .set_index("chave_obra")["id_livro"]
    )
    df["id_canonico"] = df["chave_obra"].map(canonico)
    df["_eh_canonico"] = df["id_livro"] == df["id_canonico"]

    ids_agrupados = df.groupby("id_canonico")["id_livro"].agg(
        lambda v: "; ".join(sorted(set(v)))
    )
    duplicados = (ids_agrupados.str.count(";") > 0).sum()
    logger.info("Obras com works duplicados juntados: %d", duplicados)

    # nota ponderada pelo nº de avaliações
    df["_nota_x_qtd"] = df["nota_media"].fillna(0) * df["qtd_avaliacoes"]

    # linha do work canônico primeiro, para "first" pegar os dados dele
    df = df.sort_values(["id_canonico", "data_coleta", "_eh_canonico"], ascending=[True, True, False])
    grupo = df.groupby(["id_canonico", "data_coleta"], sort=False)

    agregado = grupo.agg(
        {
            **{c: "sum" for c in COLUNAS_SOMA},
            "_nota_x_qtd": "sum",
            "ano_publicacao": "min",
        }
    )
    textos = grupo[[c for c in ("generos", "amostra", "idioma") if c in df.columns]].agg(_juntar_textos)
    fixos = [
        c for c in df.columns
        if c not in agregado.columns and c not in textos.columns
        and c not in ("id_livro", "id_canonico", "data_coleta", "_eh_canonico", "chave_obra")
    ]
    primeiros = grupo[fixos].first()

    out = pd.concat([primeiros, agregado, textos], axis=1).reset_index()
    out = out.rename(columns={"id_canonico": "id_livro"})
    out["nota_media"] = (out["_nota_x_qtd"] / out["qtd_avaliacoes"]).where(out["qtd_avaliacoes"] > 0).round(2)
    out["leitores"] = out[COLUNAS_LEITORES].sum(axis=1)
    out["ids_agrupados"] = out["id_livro"].map(ids_agrupados)
    return out.drop(columns=["_nota_x_qtd"])


def marcar_conhecidos(df):
    """
    Flags por obra, calculadas na última coleta de cada uma:
    conhecido   -> leitores >= MIN_LEITORES ou edições >= MIN_EDICOES
    no_periodo  -> publicado até ANO_MAX_PUBLICACAO
    tem_pt      -> tem edição em português
    """
    ultima = df.sort_values("data_coleta").drop_duplicates("id_livro", keep="last").set_index("id_livro")
    conhecido = (ultima["leitores"] >= MIN_LEITORES) | (ultima["qtd_edicoes"] >= MIN_EDICOES)
    no_periodo = ultima["ano_publicacao"].notna()
    if ANO_MAX_PUBLICACAO:
        no_periodo &= ultima["ano_publicacao"] <= ANO_MAX_PUBLICACAO
    tem_pt = ultima.get("idioma", pd.Series(index=ultima.index, dtype=object)).fillna("").str.contains(r"\bpor\b")

    df = df.copy()
    df["conhecido"] = df["id_livro"].map(conhecido)
    df["no_periodo"] = df["id_livro"].map(no_periodo)
    df["tem_pt"] = df["id_livro"].map(tem_pt)
    return df


def _tipar(df):
    for coluna in [*COLUNAS_INTEIRAS, "leitores"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce").round().astype("Int64")
    return df


def tratar(hist):
    """Devolve (histórico tratado, foto atual só com obras conhecidas do período)."""
    linhas_antes, obras_antes = len(hist), hist["id_livro"].nunique()

    df = _tipar(marcar_conhecidos(deduplicar(limpar(hist))))
    df = df.sort_values(["data_coleta", "id_livro"]).reset_index(drop=True)

    atual = df.drop_duplicates("id_livro", keep="last")
    atual = atual[atual["conhecido"] & atual["no_periodo"]]
    atual = atual.sort_values("leitores", ascending=False).reset_index(drop=True)

    logger.info(
        "Tratamento: %d linhas / %d obras -> %d linhas / %d obras (%d conhecidas no período, %d com edição em pt)",
        linhas_antes, obras_antes, len(df), df["id_livro"].nunique(),
        len(atual), int(atual["tem_pt"].sum()),
    )
    return df, atual
