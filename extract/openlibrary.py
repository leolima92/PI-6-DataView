"""
Coleta paginada na Search API da Open Library.

buscar_pagina  -> uma requisição, com retry/backoff
coletar_genero -> pagina um gênero inteiro
"""

import logging
import time
import requests
from config import (
    URL,
    FIELDS,
    LIMIT_POR_PAGINA,
    MAX_PAGINAS,
    PAUSA_SEGUNDOS,
    TIMEOUT,
    MAX_RETRIES,
    SESSION,
)

logger = logging.getLogger(__name__)


def buscar_pagina(termo_subject, page, ordenacao="key"):
    """
    Executa uma requisição na Search API da Open Library.

    Possui retry/backoff para HTTP 429/500/502/503/504 e erros de conexão.
    """
    params = {
        "q": f'subject:"{termo_subject}"',
        "fields": FIELDS,
        "limit": LIMIT_POR_PAGINA,
        "page": page,
        # "key" deixa a paginação determinística; ver ORDENACOES no config
        "sort": ordenacao,
    }

    for tentativa in range(MAX_RETRIES):
        try:
            response = SESSION.get(URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as erro:
            espera = min(60, 2 ** tentativa)
            logger.warning("erro de rede: %s; nova tentativa em %ss", erro, espera)
            time.sleep(espera)
            continue

        # SUCESSO
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                raise RuntimeError(
                    "Open Library retornou resposta inválida em vez de JSON."
                )

        # RATE LIMIT / ERROS TEMPORÁRIO
        if response.status_code in (429, 500, 502, 503, 504):
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    espera = float(retry_after)
                except ValueError:
                    espera = 2 ** tentativa
            else:
                espera = 2 ** tentativa

            espera = min(60, espera)
            logger.warning(
                "HTTP %s; nova tentativa em %ss", response.status_code, espera
            )
            time.sleep(espera)
            continue
        # OUTROS ERROS HTTP
        response.raise_for_status()
    raise RuntimeError(
        f"Falha após todas as tentativas (subject={termo_subject}, page={page})"
    )

def coletar_genero(nome_genero, termo_subject, ordenacao="key", max_paginas=MAX_PAGINAS):
    """Percorre as páginas de determinado gênero numa ordenação."""
    docs = []

    for page in range(1, max_paginas + 1):
        dados = buscar_pagina(termo_subject, page, ordenacao)
        lote = dados.get("docs", [])

        if not lote:
            logger.info("%s [%s]: não existem mais resultados.", nome_genero, ordenacao)
            break

        # guarda o gênero e a ordenação da consulta em cada doc
        for doc in lote:
            doc["_genero"] = nome_genero
            doc["_amostra"] = ordenacao

        docs.extend(lote)

        # Search API usa num_found; numFound fica como fallback
        total = dados.get("num_found", dados.get("numFound", 0))

        logger.info(
            "%s [%s]: página %s (+%d registros | acumulado %d | disponíveis %s)",
            nome_genero,
            ordenacao,
            page,
            len(lote),
            len(docs),
            total,
        )

        # acabaram os resultados
        if total and len(docs) >= total:
            break

        if len(lote) < LIMIT_POR_PAGINA:
            break

        time.sleep(PAUSA_SEGUNDOS)

    return docs
