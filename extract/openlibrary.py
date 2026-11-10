"""
Coleta paginada na Search API da Open Library.

buscar_pagina  -> uma requisição, com retry/backoff
coletar_genero -> pagina um gênero inteiro
edicoes_da_obra -> edições de um work (para achar títulos em português)
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
    ANO_MAX_PUBLICACAO,
)

logger = logging.getLogger(__name__)


def montar_query(termo_subject, idioma=None):
    """Monta o q= da Search API: gênero, idioma (opcional) e corte de ano."""
    partes = [f'subject:"{termo_subject}"']
    if idioma:
        partes.append(f"language:{idioma}")
    if ANO_MAX_PUBLICACAO:
        partes.append(f"first_publish_year:[* TO {ANO_MAX_PUBLICACAO}]")
    return " ".join(partes)


def _get_json(url, params, descricao):
    """GET na Open Library com retry/backoff em 429/5xx e erros de rede."""
    for tentativa in range(MAX_RETRIES):
        try:
            response = SESSION.get(url, params=params, timeout=TIMEOUT)
        except requests.RequestException as erro:
            espera = min(60, 2 ** tentativa)
            logger.warning("erro de rede: %s; nova tentativa em %ss", erro, espera)
            time.sleep(espera)
            continue

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                raise RuntimeError("Open Library retornou resposta inválida em vez de JSON.")

        if response.status_code in (429, 500, 502, 503, 504):
            retry_after = response.headers.get("Retry-After")
            try:
                espera = float(retry_after) if retry_after else 2 ** tentativa
            except ValueError:
                espera = 2 ** tentativa
            espera = min(60, espera)
            logger.warning("HTTP %s; nova tentativa em %ss", response.status_code, espera)
            time.sleep(espera)
            continue

        if response.status_code == 404:
            return None
        response.raise_for_status()
    raise RuntimeError(f"Falha após todas as tentativas ({descricao})")


def edicoes_da_obra(id_livro, limite=200, max_paginas=5):
    """
    Lista as edições de um work (/works/OL...W/editions.json), paginando
    até max_paginas. Para quando acha edições em português na página.
    Devolve lista de dicts {"titulo", "idiomas"}.
    """
    url = f"https://openlibrary.org/works/{id_livro}/editions.json"
    edicoes = []
    for pagina in range(max_paginas):
        dados = _get_json(url, {"limit": limite, "offset": pagina * limite}, f"edições de {id_livro}")
        entradas = (dados or {}).get("entries") or []
        lote = [
            {
                "titulo": e.get("title"),
                "idiomas": [str(l.get("key", "")).split("/")[-1] for l in e.get("languages") or []],
            }
            for e in entradas
        ]
        edicoes.extend(lote)
        if len(entradas) < limite or any("por" in e["idiomas"] for e in lote):
            break
        time.sleep(PAUSA_SEGUNDOS)
    return edicoes


def buscar_pagina(termo_subject, page, ordenacao="readinglog", idioma=None):
    """
    Executa uma requisição na Search API da Open Library.

    Possui retry/backoff para HTTP 429/500/502/503/504 e erros de conexão.
    """
    params = {
        "q": montar_query(termo_subject, idioma),
        "fields": FIELDS,
        "limit": LIMIT_POR_PAGINA,
        "page": page,
        # ver AMOSTRAS no config
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

def coletar_genero(
    nome_genero,
    termo_subject,
    ordenacao="readinglog",
    max_paginas=MAX_PAGINAS,
    idioma=None,
    nome_amostra=None,
):
    """Percorre as páginas de determinado gênero numa ordenação (e idioma)."""
    docs = []
    nome_amostra = nome_amostra or ordenacao

    for page in range(1, max_paginas + 1):
        dados = buscar_pagina(termo_subject, page, ordenacao, idioma)
        lote = dados.get("docs", [])

        if not lote:
            logger.info("%s [%s]: não existem mais resultados.", nome_genero, nome_amostra)
            break

        # guarda o gênero e a ordenação da consulta em cada doc
        for doc in lote:
            doc["_genero"] = nome_genero
            doc["_amostra"] = nome_amostra

        docs.extend(lote)

        # Search API usa num_found; numFound fica como fallback
        total = dados.get("num_found", dados.get("numFound", 0))

        logger.info(
            "%s [%s]: página %s (+%d registros | acumulado %d | disponíveis %s)",
            nome_genero,
            nome_amostra,
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
