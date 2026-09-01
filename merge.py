""""
Combina a base coletada com dados do Google Books (merge por ISBN).
Uso (a partir da raiz do projeto), DEPOIS de rodar a coleta:
    python merge.py
Lê  processed/livros.csv  e gera  processed/livros_merged.csv,
acrescentando as colunas gb_* (sinopse, categorias, nota, etc.).
"""

import pandas as pd
from config import BASE_DIR
from transform.google_books import merge


def main():
    entrada = BASE_DIR / "processed" / "livros.csv"
    if not entrada.exists():
        print(f"Não encontrei {entrada}. Rode 'python coletar.py' primeiro.")
        return

    df = pd.read_csv(entrada, encoding="utf-8-sig")
    df_merged = merge(df)

    saida = BASE_DIR / "processed" / "livros_merged.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(saida, index=False, encoding="utf-8-sig")

    print(
        f"\n-> {saida} "
        f"({len(df_merged)} linhas, {len(df_merged.columns)} colunas)"
    )


if __name__ == "__main__":
    main()