"""
Coleta diária completa: Open Library (coletar) + merge Google Books +
consolidação do histórico + tratamento + títulos em pt + classificação dos perfis de popularidade +
curva de sobrevivência.

Pensado para rodar agendado, 1x por dia. Ver scripts/run_daily.ps1 e o
README para registrar no Agendador de Tarefas do Windows.

Uso manual:
    python run_diario.py

O log de cada execução é gravado em
<BASE_DIR>/logs/AAAA-MM/coleta_AAAA-MM-DD.log (ver logging_setup.py).
"""

import datetime as dt
import logging
import sys

from booktrends.logging_setup import configurar_logging
from booktrends.etapas.coletar import main as coletar
from booktrends.etapas.merge import main as merge_google_books
from booktrends.etapas.consolidar import main as consolidar_historico
from booktrends.etapas.tratar import main as tratar_dados
from booktrends.etapas.traduzir_titulos import main as traduzir_titulos
from booktrends.etapas.perfis import main as analisar_perfis
from booktrends.etapas.sobrevivencia import main as curva_sobrevivencia

logger = logging.getLogger(__name__)


def main() -> int:
    arquivo_log = configurar_logging()
    inicio = dt.datetime.now()
    logger.info("=== Coleta diária iniciada em %s ===", f"{inicio:%Y-%m-%d %H:%M:%S}")
    logger.info("Log desta execução: %s", arquivo_log)

    try:
        coletar()
        merge_google_books()
        consolidar_historico()
        tratar_dados()
        traduzir_titulos()
        analisar_perfis()
        curva_sobrevivencia()
    except Exception:
        logger.exception("ERRO na coleta diária")
        return 1

    fim = dt.datetime.now()
    logger.info(
        "=== Concluída em %s (duração %s) ===",
        f"{fim:%Y-%m-%d %H:%M:%S}",
        fim - inicio,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
