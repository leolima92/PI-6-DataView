#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enriquece a base coletada com dados do Google Books.

Uso (a partir da raiz do projeto), DEPOIS de rodar a coleta:
    python enriquecer.py

Lê  processed/livros.csv  e gera  processed/livros_enriquecido.csv,
acrescentando as colunas gb_* (sinopse, categorias, nota, etc.).
"""

import pandas as pd

from config import BASE_DIR
from transform.enriquecer import enriquecer


def main():
    entrada = BASE_DIR / "processed" / "livros.csv"
    if not entrada.exists():
        print(f"Não encontrei {entrada}. Rode 'python coletar.py' primeiro.")
        return

    df = pd.read_csv(entrada, encoding="utf-8-sig")
    df_enriquecido = enriquecer(df)

    saida = BASE_DIR / "processed" / "livros_enriquecido.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df_enriquecido.to_csv(saida, index=False, encoding="utf-8-sig")

    print(
        f"\n-> {saida} "
        f"({len(df_enriquecido)} linhas, {len(df_enriquecido.columns)} colunas)"
    )


if __name__ == "__main__":
    main()