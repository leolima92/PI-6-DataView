"""
Títulos em português para as obras conhecidas.

Não usa tradução automática: título de livro traduzido ao pé da letra sai
errado ("Nineteen Eighty-Four" é "1984" no Brasil). O título vem de uma
edição real em português, nesta ordem:

1. Open Library: edições do próprio work com idioma "por"; fica o título
   mais frequente entre elas (só para obras com edição em pt, tem_pt).
2. Google Books: busca título + autor com langRestrict=pt; só aceita o
   volume se o sobrenome do autor bater.
3. Senão, fica o título original.

Colunas geradas: titulo_pt, titulo_pt_fonte (openlibrary / google_books /
original) e titulo_exibicao (titulo_pt, ou o original quando não há).

As respostas ficam em cache/titulos_pt.json, então cada obra é consultada
uma vez só; "não encontrado" também é guardado. Falha de API não entra no
cache: a obra é tentada de novo na próxima rodada.
"""

import json
import logging
import time
from collections import Counter

import pandas as pd

from config import (
    BASE_DIR,
    GB_MAX_FALHAS_SEGUIDAS,
    GB_PAUSA_SEGUNDOS,
    PAUSA_SEGUNDOS,
    TITULOS_GB_MAX,
    TITULOS_MAX_POR_RODADA,
)
from extract.googlebooks import GoogleBooksIndisponivel, buscar_edicoes_pt
from extract.openlibrary import edicoes_da_obra
from transform.tratamento import _texto_normalizado

logger = logging.getLogger(__name__)

CACHE_PATH = BASE_DIR / "cache" / "titulos_pt.json"
COLUNAS = ["titulo_pt", "titulo_pt_fonte", "titulo_exibicao"]


def _limpar_titulo(titulo):
    """Tira espaços extras e o ' / autor' que algumas edições trazem."""
    if not isinstance(titulo, str):
        return None
    titulo = titulo.split(" / ")[0]
    titulo = " ".join(titulo.split()).strip(" .;:/")
    return titulo or None


def escolher_titulo_ol(edicoes):
    """Título mais frequente entre as edições em português (ou None)."""
    titulos = [_limpar_titulo(e["titulo"]) for e in edicoes if "por" in e.get("idiomas", [])]
    titulos = [t for t in titulos if t]
    if not titulos:
        return None
    # conta pela forma normalizada, devolve a grafia mais comum dessa forma
    contagem = Counter(_texto_normalizado(t) or t.lower() for t in titulos)
    vencedor = contagem.most_common(1)[0][0]
    grafias = Counter(t for t in titulos if (_texto_normalizado(t) or t.lower()) == vencedor)
    return grafias.most_common(1)[0][0]


def _sobrenome(autor):
    partes = _texto_normalizado(autor).split()
    return partes[-1] if partes else ""


def escolher_titulo_gb(volumes, autor):
    """1º volume em pt cujo autor tem o mesmo sobrenome (ou None)."""
    sobrenome = _sobrenome(autor)
    for volume in volumes:
        autores = " ".join(volume.get("authors") or [])
        if sobrenome and sobrenome in _texto_normalizado(autores).split():
            titulo = _limpar_titulo(volume.get("title"))
            if titulo:
                return titulo
    return None


def carregar_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def buscar_titulos(df):
    """
    Consulta os títulos em pt das obras de df (livros_analise) que ainda não
    estão no cache, das mais lidas para as menos lidas. Respeita
    TITULOS_MAX_POR_RODADA consultas no total e TITULOS_GB_MAX no Google Books.
    """
    cache = carregar_cache()
    pendentes = df[~df["id_livro"].isin(cache.keys())].sort_values("leitores", ascending=False)
    alvos = pendentes.head(TITULOS_MAX_POR_RODADA)
    logger.info(
        "Títulos em pt: %d obras no cache, %d pendentes, consultando %d nesta rodada",
        len(cache), len(pendentes), len(alvos),
    )

    consultas_gb = 0
    falhas_gb_seguidas = 0
    gb_fora = False
    novos = {"openlibrary": 0, "google_books": 0, "original": 0}

    for n, linha in enumerate(alvos.itertuples(index=False), start=1):
        titulo_pt, fonte = None, None

        if bool(getattr(linha, "tem_pt", False)):
            try:
                titulo_pt = escolher_titulo_ol(edicoes_da_obra(linha.id_livro))
            except RuntimeError as erro:
                logger.warning("Open Library sem resposta para %s: %s", linha.id_livro, erro)
                continue  # não grava no cache: tenta de novo na próxima rodada
            fonte = "openlibrary" if titulo_pt else None
            time.sleep(PAUSA_SEGUNDOS)

        if not titulo_pt:
            if gb_fora or consultas_gb >= TITULOS_GB_MAX:
                continue  # sem Google Books nesta rodada: fica pendente
            try:
                volumes = buscar_edicoes_pt(linha.titulo, linha.autor_principal)
                falhas_gb_seguidas = 0
            except GoogleBooksIndisponivel as erro:
                falhas_gb_seguidas += 1
                logger.warning("Google Books sem resposta: %s", erro)
                if falhas_gb_seguidas >= GB_MAX_FALHAS_SEGUIDAS:
                    gb_fora = True
                    logger.warning("Google Books fora do ar; parando as consultas a ele nesta rodada.")
                continue
            consultas_gb += 1
            titulo_pt = escolher_titulo_gb(volumes, linha.autor_principal)
            fonte = "google_books" if titulo_pt else "original"
            time.sleep(GB_PAUSA_SEGUNDOS)

        cache[linha.id_livro] = {"titulo_pt": titulo_pt, "fonte": fonte}
        novos[fonte] += 1
        if n % 50 == 0:
            _salvar_cache(cache)
            logger.info("... %d de %d obras consultadas", n, len(alvos))

    _salvar_cache(cache)
    logger.info(
        "Títulos em pt nesta rodada: %d da Open Library, %d do Google Books, %d sem edição em pt",
        novos["openlibrary"], novos["google_books"], novos["original"],
    )
    return cache


def aplicar_titulos(df, cache=None):
    """Acrescenta titulo_pt, titulo_pt_fonte e titulo_exibicao a partir do cache."""
    cache = carregar_cache() if cache is None else cache
    df = df.drop(columns=[c for c in COLUNAS if c in df.columns])
    info = df["id_livro"].map(cache)
    df["titulo_pt"] = info.map(lambda i: i.get("titulo_pt") if isinstance(i, dict) else None)
    df["titulo_pt_fonte"] = info.map(lambda i: i.get("fonte") if isinstance(i, dict) else None)
    df["titulo_exibicao"] = df["titulo_pt"].fillna(df["titulo"])

    # deixa os títulos logo depois do original
    colunas = list(df.columns)
    for c in COLUNAS:
        colunas.remove(c)
    pos = colunas.index("titulo") + 1 if "titulo" in colunas else 0
    return df[colunas[:pos] + ["titulo_exibicao", "titulo_pt", "titulo_pt_fonte"] + colunas[pos:]]
