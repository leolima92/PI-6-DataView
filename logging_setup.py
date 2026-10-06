"""
Configuração central de logging do Book Trends.

Chame ``configurar_logging()`` uma única vez, no início da execução
(``run_diario.py``, ``coletar.py`` ou ``merge.py``). A partir daí todo
módulo usa ``logging.getLogger(__name__)`` e a saída vai para:

- o console (stdout);
- um arquivo datado em ``<BASE_DIR>/logs/AAAA-MM/coleta_AAAA-MM-DD.log``.

``BASE_DIR`` vem do ``config`` (por padrão ``G:/Meu Drive/book-trends``),
então o log fica na mesma pasta dos CSVs. Rodar de novo no mesmo dia
acrescenta no mesmo arquivo, sem apagar o que já estava lá.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from config import BASE_DIR

_FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATA_HORA = "%Y-%m-%d %H:%M:%S"
_configurado = False


def _pasta_de_logs() -> Path:
    """Pasta de logs do mês dentro do BASE_DIR (``logs/AAAA-MM``); cai para
    ``./logs/AAAA-MM`` se o BASE_DIR (ex.: o Google Drive) não estiver
    acessível."""
    mes = f"{dt.date.today():%Y-%m}"
    try:
        alvo = Path(BASE_DIR) / "logs" / mes
        alvo.mkdir(parents=True, exist_ok=True)
        return alvo
    except OSError:
        alvo = Path(__file__).resolve().parent / "logs" / mes
        alvo.mkdir(parents=True, exist_ok=True)
        return alvo


def configurar_logging(nivel: int = logging.INFO) -> Path:
    """Configura o logger raiz (idempotente) e devolve o caminho do arquivo
    de log usado nesta execução."""
    global _configurado

    arquivo = _pasta_de_logs() / f"coleta_{dt.date.today():%Y-%m-%d}.log"

    if _configurado:
        return arquivo

    formatador = logging.Formatter(_FORMATO, datefmt=_DATA_HORA)

    console = logging.StreamHandler()
    console.setFormatter(formatador)

    em_arquivo = logging.FileHandler(arquivo, mode="a", encoding="utf-8")
    em_arquivo.setFormatter(formatador)

    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    raiz.addHandler(console)
    raiz.addHandler(em_arquivo)

    _configurado = True
    return arquivo
