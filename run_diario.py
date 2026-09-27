"""
Coleta diária completa: Open Library (coletar) + merge Google Books +
consolidação do histórico.

Pensado para rodar agendado, 1x por dia. Ver scripts/run_daily.ps1 e o
README para registrar no Agendador de Tarefas do Windows.

Uso manual:
    python run_diario.py

O log de cada execução é gravado em
<BASE_DIR>/logs/coleta_AAAA-MM-DD.log (ver logging_setup.py).
"""

import datetime as dt
import logging
import sys

from logging_setup import configurar_logging
from pipeline import main as coletar
from merge import main as merge_google_books
from consolidar_historico import main as consolidar_historico

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
