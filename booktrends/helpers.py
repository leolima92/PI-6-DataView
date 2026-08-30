"""Funções de apoio usadas na transformação dos dados."""
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