"""
Consulta ao Google Books API (busca por ISBN).

buscar_por_isbn   -> volumeInfo do 1º volume que casa com o ISBN, ou None
buscar_edicoes_pt -> volumeInfo das edições em português (título + autor)
campos_google     -> extrai do volumeInfo apenas as colunas gb_* do projeto

Quando o Google Books não responde (429/5xx/erro de rede depois de todas as
tentativas, ou 403 de cota), as funções de busca levantam GoogleBooksIndisponivel
em vez de devolver None. Assim quem chama distingue "livro não encontrado"
de "API fora do ar" e não grava a falha no cache como se fosse resposta.
"""

import logging
import random
import time
import requests
from booktrends.config import (
    GOOGLE_BOOKS_URL,
    GOOGLE_BOOKS_API_KEY,
    GB_ESPERA_RETRY,
    TIMEOUT,
    MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class GoogleBooksIndisponivel(Exception):
    """O Google Books não respondeu (sobrecarga, erro de rede ou cota)."""


# Sessão própria — a SESSION do config carrega headers da Open Library.
SESSION_GB = requests.Session()
SESSION_GB.headers.update({"Accept": "application/json"})


def _consultar(params, descricao):
    """
    GET no Google Books com retry/backoff em 429/5xx e erros de rede.
    Devolve a lista de itens (vazia se não achou). Se todas as tentativas
    falharem, levanta GoogleBooksIndisponivel.
    """
    params = dict(params)
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    ultimo_erro = None
    for tentativa in range(MAX_RETRIES):
        ultima = tentativa == MAX_RETRIES - 1
        try:
            resp = SESSION_GB.get(GOOGLE_BOOKS_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as erro:
            ultimo_erro = f"erro de rede: {erro}"
            if ultima:
                break
            espera = _espera(tentativa)
            logger.warning(
                "erro de rede (GB): %s; nova tentativa em %.0fs", erro, espera
            )
            time.sleep(espera)
            continue

        if resp.status_code == 200:
            try:
                dados = resp.json()
            except ValueError:
                return []
            return dados.get("items") or []

        if resp.status_code in (429, 500, 502, 503, 504):
            # 503 do Google Books ("backendFailed") é falha do lado deles:
            # espera mais (5s, 10s, 20s...) em vez de bater de novo em 1s
            ultimo_erro = f"HTTP {resp.status_code}"
            if ultima:
                break
            espera = _espera(tentativa)
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    espera = min(60, max(espera, float(retry_after)))
                except ValueError:
                    pass
            logger.warning(
                "HTTP %s (GB); nova tentativa em %.0fs", resp.status_code, espera
            )
            time.sleep(espera)
            continue

        # 403 no Google Books normalmente é estouro de cota / limite:
        # não adianta tentar as próximas consultas hoje.
        if resp.status_code == 403:
            raise GoogleBooksIndisponivel(
                "HTTP 403 — provável limite de cota. "
                "Confira a API key ou reduza GB_MAX_LIVROS."
            )

        resp.raise_for_status()

    raise GoogleBooksIndisponivel(
        f"{descricao}: sem resposta após {MAX_RETRIES} tentativas ({ultimo_erro})"
    )


def buscar_por_isbn(isbn):
    """
    Consulta o Google Books por ISBN e retorna o volumeInfo do 1º
    resultado, ou None se o Google Books responder que não achou.
    """
    itens = _consultar({"q": f"isbn:{isbn}"}, f"ISBN {isbn}")
    if not itens:
        return None
    return itens[0].get("volumeInfo", {})


def buscar_edicoes_pt(titulo, autor):
    """
    Busca no Google Books edições em português de um livro (título + autor).
    Devolve a lista de volumeInfo com language == "pt" (pode ser vazia).
    """
    termos = [f'intitle:"{titulo}"']
    if autor:
        termos.append(f'inauthor:"{autor}"')
    params = {"q": " ".join(termos), "langRestrict": "pt", "maxResults": 10, "printType": "books"}
    itens = _consultar(params, f"título pt de {titulo!r}")
    volumes = [i.get("volumeInfo", {}) for i in itens]
    return [v for v in volumes if str(v.get("language", "")).lower().startswith("pt")]


def _espera(tentativa):
    """Backoff exponencial com um pouco de aleatoriedade (máx. 60s)."""
    return min(60, GB_ESPERA_RETRY * 2 ** tentativa) + random.uniform(0, 1)


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