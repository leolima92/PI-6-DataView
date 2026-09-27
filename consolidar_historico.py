"""
Consolida o histórico mensal num único CSV, pronto para o Power BI.

historico/ guarda um arquivo por mês (livros_AAAA-MM.csv,
livros_merged_AAAA-MM.csv). Esse script junta todos os meses em:

    historico/livros_consolidado.csv
    historico/livros_merged_consolidado.csv

Nenhum arquivo mensal é apagado ou sobrescrito — a consolidação só lê e
gera esses dois arquivos extras. Rode sempre que quiser atualizar a base
que alimenta o BI (ex.: no fim de run_diario.py, ou manualmente):

    python consolidar_historico.py
"""

import logging
import re

import pandas as pd

from config import BASE_DIR
from logging_setup import configurar_logging

logger = logging.getLogger(__name__)

PADRAO_BASE = re.compile(r"^livros_\d{4}-\d{2}\.csv$")
PADRAO_MERGED = re.compile(r"^livros_merged_\d{4}-\d{2}\.csv$")


def _consolidar(pasta, padrao, saida):
    arquivos = sorted(p for p in pasta.glob("*.csv") if padrao.match(p.name))

    if not arquivos:
        logger.warning("Nenhum arquivo encontrado para o padrão %s em %s", padrao.pattern, pasta)
        return

    partes = [pd.read_csv(arq, encoding="utf-8-sig") for arq in arquivos]
    combinado = pd.concat(partes, ignore_index=True)

    combinado = combinado.drop_duplicates(
        subset=["id_livro", "data_coleta"], keep="last"
    ).sort_values(["data_coleta", "id_livro"]).reset_index(drop=True)

    combinado.to_csv(saida, index=False, encoding="utf-8-sig")
    logger.info(
        "-> %s (%d meses combinados, %d linhas no total)",
        saida,
        len(arquivos),
        len(combinado),
    )


def main():
    pasta = BASE_DIR / "historico"
    _consolidar(pasta, PADRAO_BASE, pasta / "livros_consolidado.csv")
    _consolidar(pasta, PADRAO_MERGED, pasta / "livros_merged_consolidado.csv")


if __name__ == "__main__":
    configurar_logging()
    main()
