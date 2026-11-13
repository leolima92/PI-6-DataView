"""
Junta (merge) dados do Google Books na base de livros, por ISBN.
Regras (para respeitar a cota da API do Google Books):
- só consulta livros que têm ISBN;
- a fila de consultas começa pelos livros conhecidos da base de análise (a
  lista de prioridade, dos mais lidos para os menos lidos) e segue pelos
  outros, dos mais desejados (want_to_read) para os menos;
- GB_MAX_LIVROS limita só as consultas NOVAS da rodada: o que já está no
  cache é aplicado a todos os livros sem contar no limite, então a
  cobertura cresce a cada dia em vez de repetir os mesmos livros;
- guarda um cache em disco, então ISBNs já buscados não são reconsultados;
- falha da API (503 etc.) não entra no cache, então o ISBN é tentado de novo
  na próxima rodada; "não encontrado" entra, marcado com _nao_encontrado;
- depois de GB_MAX_FALHAS_SEGUIDAS ISBNs seguidos sem resposta, para de
  consultar na rodada e segue só com o que já está no cache.
Os campos gb_* são majoritariamente atributos estáticos do livro (sinopse,
categorias etc.), mas o resultado do merge é gravado tanto no snapshot
(processed/livros_merged.csv) quanto no histórico acumulado
(historico/livros_merged_{AAAA-MM}.csv, ver etapas/merge.py), para manter também
a série temporal de nota/avaliações junto com os campos gb_*.
"""

import json
import logging
import time
import pandas as pd
from booktrends.config import BASE_DIR, GB_MAX_LIVROS, GB_PAUSA_SEGUNDOS, GB_MAX_FALHAS_SEGUIDAS
from booktrends.extract.googlebooks import (
    GoogleBooksIndisponivel,
    buscar_por_isbn,
    campos_google,
)

logger = logging.getLogger(__name__)

CACHE_PATH = BASE_DIR / "cache" / "googlebooks.json"

# marca no cache um ISBN que o Google Books respondeu e não tinha
NAO_ENCONTRADO = {"_nao_encontrado": True}


def _no_cache(cache, isbn):
    """
    True se o ISBN já tem resposta válida no cache. Entradas vazias ({})
    vêm de versões antigas, que gravavam falha da API como se fosse
    "não encontrado"; essas são consultadas de novo uma vez.
    """
    return bool(cache.get(isbn))


def _carregar_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def ordenar_fila(df_livros, prioridade=None):
    """
    Livros com ISBN na ordem em que devem ser consultados: primeiro os da
    lista de prioridade (na ordem dela), depois os outros, dos mais
    desejados (want_to_read) para os menos.
    """
    com_isbn = df_livros[df_livros["isbn"].notna()].copy()
    posicao = {id_livro: i for i, id_livro in enumerate(prioridade or [])}
    com_isbn["_prioridade"] = com_isbn["id_livro"].map(posicao)
    com_isbn["_desejo"] = com_isbn["want_to_read"] if "want_to_read" in com_isbn.columns else 0
    com_isbn = com_isbn.sort_values(
        ["_prioridade", "_desejo"], ascending=[True, False], na_position="last"
    )
    return com_isbn.drop(columns=["_prioridade", "_desejo"])


def merge(df_livros, prioridade=None):
    """
    Recebe a tabela de livros (Open Library) e devolve uma cópia com as
    colunas gb_* preenchidas para os livros que já estão no cache ou que
    foram consultados nesta rodada.

    prioridade: IDs a consultar primeiro (ex.: os livros conhecidos da base
    de análise, dos mais lidos para os menos lidos).
    """
    cache = _carregar_cache()
    alvos = ordenar_fila(df_livros, prioridade)
    na_prioridade = alvos["id_livro"].isin(set(prioridade or []))

    logger.info(
        "Google Books: %d livros com ISBN (%d da lista de prioridade); "
        "até %d consultas novas nesta rodada (GB_MAX_LIVROS)",
        len(alvos),
        int(na_prioridade.sum()),
        GB_MAX_LIVROS,
    )

    por_livro = {}
    consultas_novas = 0
    do_cache = 0
    falhas = 0
    falhas_seguidas = 0
    interrompido = False

    for _, linha in alvos.iterrows():
        isbn = str(linha["isbn"])

        if _no_cache(cache, isbn):
            por_livro[linha["id_livro"]] = cache[isbn]
            do_cache += 1
            continue

        # o limite vale só para consultas novas; o cache continua sendo aplicado
        if interrompido or consultas_novas >= GB_MAX_LIVROS:
            continue

        try:
            volume = buscar_por_isbn(isbn)
        except GoogleBooksIndisponivel as erro:
            falhas += 1
            falhas_seguidas += 1
            logger.warning("Google Books sem resposta: %s", erro)
            if falhas_seguidas >= GB_MAX_FALHAS_SEGUIDAS:
                interrompido = True
                logger.warning(
                    "Google Books fora do ar: %d ISBNs seguidos sem resposta. "
                    "Parando as consultas nesta rodada; os ISBNs que faltaram "
                    "serão tentados na próxima.",
                    falhas_seguidas,
                )
            time.sleep(GB_PAUSA_SEGUNDOS)
            continue

        falhas_seguidas = 0
        campos = campos_google(volume) or dict(NAO_ENCONTRADO)
        cache[isbn] = campos
        por_livro[linha["id_livro"]] = campos
        consultas_novas += 1
        time.sleep(GB_PAUSA_SEGUNDOS)
        if consultas_novas % 50 == 0:
            _salvar_cache(cache)  # salva progresso periodicamente
            logger.info("... %d consultas novas", consultas_novas)

    _salvar_cache(cache)
    logger.info(
        "Concluído: %d consultas novas, %d vindas do cache, %d falhas da API%s.",
        consultas_novas,
        do_cache,
        falhas,
        " (interrompido)" if interrompido else "",
    )
    if prioridade:
        cobertos = sum(1 for i in set(prioridade) if por_livro.get(i) and not por_livro[i].get("_nao_encontrado"))
        pendentes = sum(1 for i in alvos.loc[na_prioridade, "isbn"].astype(str) if not _no_cache(cache, i))
        logger.info(
            "Livros da lista de prioridade: %d com dados do Google Books, %d ainda sem consulta",
            cobertos, pendentes,
        )

    # remove as marcas internas (ex.: _nao_encontrado) antes de virar coluna
    por_livro = {
        id_livro: {k: v for k, v in campos.items() if not k.startswith("_")}
        for id_livro, campos in por_livro.items()
    }
    if not any(por_livro.values()):
        return df_livros.copy()

    df_gb = pd.DataFrame.from_dict(por_livro, orient="index")
    df_gb.index.name = "id_livro"
    df_gb = df_gb.reset_index()

    return df_livros.merge(df_gb, on="id_livro", how="left")