"""
Consulta ao Google Books API (busca por ISBN).

buscar_por_isbn -> volumeInfo do 1º volume que casa com o ISBN, ou None
campos_google   -> extrai do volumeInfo apenas as colunas gb_* do projeto
"""

import logging
import time
import requests
from config import (
    GOOGLE_BOOKS_URL,
    GOOGLE_BOOKS_API_KEY,
    TIMEOUT,
    MAX_RETRIES,
)

logger = logging.getLogger(__name__)

# Sessão própria — a SESSION do config carrega headers da Open Library.
SESSION_GB = requests.Session()
SESSION_GB.headers.update({"Accept": "application/json"})


def buscar_por_isbn(isbn):
    """
    Consulta o Google Books por ISBN e retorna o volumeInfo do 1º
    resultado (ou None se não achar). Retry/backoff em 429/5xx.
    """
    params = {"q": f"isbn:{isbn}"}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    for tentativa in range(MAX_RETRIES):
        try:
            resp = SESSION_GB.get(GOOGLE_BOOKS_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as erro:
            espera = min(60, 2 ** tentativa)
            logger.warning(
                "erro de rede (GB): %s; nova tentativa em %ss", erro, espera
            )
            time.sleep(espera)
            continue

        if resp.status_code == 200:
            try:
                dados = resp.json()
            except ValueError:
                return None
            itens = dados.get("items")
            if not itens:
                return None
            return itens[0].get("volumeInfo", {})

        if resp.status_code in (429, 500, 502, 503, 504):
            espera = min(60, 2 ** tentativa)
            logger.warning(
                "HTTP %s (GB); nova tentativa em %ss", resp.status_code, espera
            )
            time.sleep(espera)
            continue

        # 403 no Google Books normalmente é estouro de cota / limite.
        if resp.status_code == 403:
            logger.error(
                "HTTP 403 (GB) — provável limite de cota. "
                "Use uma API key ou reduza GB_MAX_LIVROS."
            )
            return None

        resp.raise_for_status()

    return None


def campos_google(volume_info):
    """Extrai do volumeInfo apenas as colunas gb_* usadas no projeto."""
    if not volume_info:
        return {}

    categorias = volume_info.get("categories") or []
    if isinstance(categorias, list):
        categorias = "; ".join(categorias)

    return {
        "gb_descricao": volume_info.get("description"),
        "gb_categorias": categorias,
        "gb_nota_media": volume_info.get("averageRating"),
        "gb_qtd_avaliacoes": volume_info.get("ratingsCount"),
        "gb_paginas": volume_info.get("pageCount"),
        "gb_editora": volume_info.get("publisher"),
        "gb_data_publicacao": volume_info.get("publishedDate"),
        "gb_link": volume_info.get("infoLink"),
    }