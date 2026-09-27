"""
Junta (merge) dados do Google Books na base de livros, por ISBN.
Regras (para respeitar a cota da API do Google Books):
- só consulta livros que têm ISBN;
- prioriza os mais populares (want_to_read) e limita a GB_MAX_LIVROS por rodada;
- guarda um cache em disco, então ISBNs já buscados não são reconsultados.
Os campos gb_* são majoritariamente atributos estáticos do livro (sinopse,
categorias etc.), mas o resultado do merge é gravado tanto no snapshot
(processed/livros_merged.csv) quanto no histórico acumulado
(historico/livros_merged_{AAAA-MM}.csv, ver merge.py), para manter também
a série temporal de nota/avaliações junto com os campos gb_*.
"""

import json
import logging
import time
import pandas as pd
from config import BASE_DIR, GB_MAX_LIVROS, GB_PAUSA_SEGUNDOS
from extract.googlebooks import buscar_por_isbn, campos_google

logger = logging.getLogger(__name__)

CACHE_PATH = BASE_DIR / "cache" / "googlebooks.json"


def _carregar_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def merge(df_livros):
    """Recebe a tabela de livros (Open Library) e devolve uma cópia com
    as colunas gb_* preenchidas para os livros consultados."""
    cache = _carregar_cache()

    # só livros com ISBN, priorizando os mais populares
    com_isbn = df_livros[df_livros["isbn"].notna()].copy()
    if "want_to_read" in com_isbn.columns:
        com_isbn = com_isbn.sort_values(
            "want_to_read", ascending=False, na_position="last"
        )
    alvos = com_isbn.head(GB_MAX_LIVROS)

    logger.info(
        "Consultando o Google Books para %d livros "
        "(de %d no total; limite GB_MAX_LIVROS=%d)",
        len(alvos),
        len(df_livros),
        GB_MAX_LIVROS,
    )

    por_livro = {}
    consultas_novas = 0

    for _, linha in alvos.iterrows():
        isbn = str(linha["isbn"])

        if isbn in cache:
            campos = cache[isbn]
        else:
            campos = campos_google(buscar_por_isbn(isbn))
            cache[isbn] = campos
            consultas_novas += 1
            time.sleep(GB_PAUSA_SEGUNDOS)
            if consultas_novas % 50 == 0:
                _salvar_cache(cache)  # salva progresso periodicamente
                logger.info("... %d consultas novas", consultas_novas)

        por_livro[linha["id_livro"]] = campos

    _salvar_cache(cache)
    logger.info(
        "Concluído: %d consultas novas, %d vindas do cache.",
        consultas_novas,
        len(alvos) - consultas_novas,
    )

    df_gb = pd.DataFrame.from_dict(por_livro, orient="index")
    df_gb.index.name = "id_livro"
    df_gb = df_gb.reset_index()

    return df_livros.merge(df_gb, on="id_livro", how="left")