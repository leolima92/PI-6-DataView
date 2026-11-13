"""Funções de apoio para texto e campos da Open Library."""

import re
import unicodedata

def primeiro(valor):
    """
    Open Library retorna vários campos como lista.
    Retorna apenas o primeiro valor.
    """
    if isinstance(valor, list):
        return valor[0] if valor else None
    return valor


def lista_para_texto(valor):
    """
    Converte listas em texto separado por ";" para facilitar
    o armazenamento em CSV.
    """
    if isinstance(valor, list):
        return "; ".join(str(v) for v in valor)
    return valor


def escolher_isbn(isbns):
    """Prefere ISBN-13. Caso não exista, usa o primeiro ISBN disponível."""
    if not isbns:
        return None

    if not isinstance(isbns, list):
        isbns = [isbns]

    # limpa hífens/espaços apenas para verificar o tamanho
    for isbn in isbns:
        isbn_limpo = str(isbn).replace("-", "").replace(" ", "")
        if len(isbn_limpo) == 13:
            return str(isbn)

    return str(isbns[0])


def normalizar_texto(valor):
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
