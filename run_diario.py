"""
Coleta diária completa: Open Library (coletar) + merge Google Books.

Pensado para rodar agendado, 1x por dia. Ver scripts/run_daily.ps1 e o
README para registrar no Agendador de Tarefas do Windows.

Uso manual:
    python run_diario.py
"""

import datetime as dt
import sys
import traceback

from pipeline import main as coletar
from merge import main as merge_google_books


def main() -> int:
    inicio = dt.datetime.now()
    print(f"=== Coleta diária iniciada em {inicio:%Y-%m-%d %H:%M:%S} ===")

    try:
        coletar()
        merge_google_books()
    except Exception:
        print("ERRO na coleta diária:", file=sys.stderr)
        traceback.print_exc()
        return 1

    fim = dt.datetime.now()
    print(f"=== Concluída em {fim:%Y-%m-%d %H:%M:%S} (duração {fim - inicio}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
