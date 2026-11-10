"""
Busca os títulos em português das obras conhecidas e grava em
processed/livros_analise.csv (colunas titulo_exibicao, titulo_pt,
titulo_pt_fonte). Regras e fontes em transform/titulos.py.

Uso (a partir da raiz do projeto), DEPOIS de rodar o tratar.py:
    python traduzir_titulos.py

Cada rodada consulta até TITULOS_MAX_POR_RODADA obras novas (config.py),
das mais lidas para as menos lidas; o resto fica para as próximas rodadas.
Para preencher a base toda de uma vez, aumente esse limite e rode à mão.
"""

import logging

import pandas as pd

from config import BASE_DIR
from load.csv_writer import salvar_csv
from logging_setup import configurar_logging
from transform.titulos import aplicar_titulos, buscar_titulos

logger = logging.getLogger(__name__)


def main():
    caminho = BASE_DIR / "processed" / "livros_analise.csv"
    if not caminho.exists():
        logger.error("Não encontrei %s. Rode 'python tratar.py' primeiro.", caminho)
        return

    df = pd.read_csv(caminho, encoding="utf-8-sig", low_memory=False)
    cache = buscar_titulos(df)
    df = aplicar_titulos(df, cache)
    salvar_csv(df, caminho)

    fontes = df["titulo_pt_fonte"].fillna("pendente").value_counts()
    logger.info("Títulos na base de análise:\n%s", fontes.to_string())


if __name__ == "__main__":
    configurar_logging()
    main()
