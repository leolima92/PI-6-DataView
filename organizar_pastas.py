"""
Move os arquivos antigos (soltos) para as pastas mensais.

Antes, tudo ficava direto em raw/, historico/ e logs/. Agora cada mês tem
sua pasta (raw/AAAA-MM/, historico/AAAA-MM/, logs/AAAA-MM/). Rode uma vez
para arrumar o que já existe:

    python organizar_pastas.py

Nada é apagado sem antes estar copiado no destino:
- raw:       se o arquivo já existir no destino, o antigo fica onde está;
- historico: se já existir no destino, os dois são combinados (sem duplicar
             livro + data_coleta) e só então o antigo é removido;
- logs:      se já existir no destino, o antigo é anexado ao final dele.

Os consolidados (historico/livros_consolidado.csv etc.) continuam na raiz
de historico/, porque juntam todos os meses.
"""

import logging
import re
import shutil

import pandas as pd

from config import BASE_DIR
from load.csv_writer import salvar_historico
from logging_setup import configurar_logging

logger = logging.getLogger(__name__)

# subpasta -> padrão do nome (grupo "mes" = AAAA-MM)
PADROES = {
    "raw": re.compile(r"^openlibrary_(?P<mes>\d{4}-\d{2})-\d{2}\.csv$"),
    "historico": re.compile(r"^livros_(?:merged_)?(?P<mes>\d{4}-\d{2})\.csv$"),
    "logs": re.compile(r"^(?:coleta|run_daily)_(?P<mes>\d{4}-\d{2})-\d{2}\.log$"),
}


def _mover(origem, destino, subpasta):
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), str(destino))
        logger.info("movido: %s -> %s", origem, destino)
        return

    if subpasta == "historico":
        df = pd.read_csv(origem, encoding="utf-8-sig")
        salvar_historico(df, destino)
        origem.unlink()
        logger.info("combinado: %s -> %s", origem, destino)
    elif subpasta == "logs":
        with open(destino, "a", encoding="utf-8") as saida:
            saida.write(origem.read_text(encoding="utf-8", errors="replace"))
        origem.unlink()
        logger.info("anexado: %s -> %s", origem, destino)
    else:
        logger.warning("já existe, mantido no lugar: %s (destino %s)", origem, destino)


def main():
    movidos = 0
    for subpasta, padrao in PADROES.items():
        pasta = BASE_DIR / subpasta
        if not pasta.is_dir():
            continue
        # só arquivos soltos na raiz da subpasta
        for arquivo in sorted(p for p in pasta.iterdir() if p.is_file()):
            achado = padrao.match(arquivo.name)
            if not achado:
                continue
            _mover(arquivo, pasta / achado["mes"] / arquivo.name, subpasta)
            movidos += 1

    logger.info("Organização concluída: %d arquivo(s) tratados em %s", movidos, BASE_DIR)


if __name__ == "__main__":
    configurar_logging()
    main()
