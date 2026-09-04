"""
Ponto de entrada da coleta do Book Trends.

Uso (a partir da raiz do projeto):
    python coletar.py

Ajuste as configurações em config.py antes de rodar.
O log é gravado em <BASE_DIR>/logs/coleta_AAAA-MM-DD.log.
"""

from logging_setup import configurar_logging
from pipeline import main

if __name__ == "__main__":
    configurar_logging()
    main()
