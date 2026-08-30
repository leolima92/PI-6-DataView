"""
Coleta paginada na Search API da Open Library.

buscar_pagina  -> uma requisição, com retry/backoff
coletar_genero -> pagina um gênero inteiro
"""

import time

import requests

from ..config import (
    URL,
    FIELDS,
    LIMIT_POR_PAGINA,
    MAX_PAGINAS,
    PAUSA_SEGUNDOS,
    TIMEOUT,
    MAX_RETRIES,
    SESSION,
)


def buscar_pagina(termo_subject, page):
    """
    Executa uma requisição na Search API da Open Library.

    Possui retry/backoff para HTTP 429/500/502/503/504 e erros de conexão.
    """
    params = {
        "q": f'subject:"{termo_subject}"',
        "fields": FIELDS,
        "limit": LIMIT_POR_PAGINA,
        "page": page,
        # deixa a paginação mais determinística
        "sort": "key",
    }

    for tentativa in range(MAX_RETRIES):
        try:
            response = SESSION.get(URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as erro:
            espera = min(60, 2 ** tentativa)
            print(f"      erro de rede: {erro}; nova tentativa em {espera}s")
            time.sleep(espera)
            continue

        # ------------------------------------------------------------------
        # SUCESSO
        # ------------------------------------------------------------------
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                raise RuntimeError(
                    "Open Library retornou resposta inválida em vez de JSON."
                )

        # ------------------------------------------------------------------
        # RATE LIMIT / ERROS TEMPORÁRIOS
        # ------------------------------------------------------------------
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
            print(f"      HTTP {response.status_code}; nova tentativa em {espera}s")
            time.sleep(espera)
            continue

        # ------------------------------------------------------------------
        # OUTROS ERROS HTTP
        # ------------------------------------------------------------------
        response.raise_for_status()

    raise RuntimeError(
        f"Falha após todas as tentativas (subject={termo_subject}, page={page})"
    )


def coletar_genero(nome_genero, termo_subject):
    """Percorre as páginas de determinado gênero."""
    docs = []

    for page in range(1, MAX_PAGINAS + 1):
        dados = buscar_pagina(termo_subject, page)
        lote = dados.get("docs", [])

        if not lote:
            print(f"    {nome_genero}: não existem mais resultados.")
            break

        # guarda o gênero da consulta em cada doc
        for doc in lote:
            doc["_genero"] = nome_genero

        docs.extend(lote)

        # Search API usa num_found; numFound fica como fallback
        total = dados.get("num_found", dados.get("numFound", 0))

        print(
            f"    {nome_genero}: página {page} "
            f"(+{len(lote)} registros | acumulado {len(docs)} | "
            f"disponíveis {total})"
        )

        # acabaram os resultados
        if total and len(docs) >= total:
            break

        if len(lote) < LIMIT_POR_PAGINA:
            break

        time.sleep(PAUSA_SEGUNDOS)

    return docs
