"""
Exporta os dados do livro "Livros que desafiam o tempo" (issue #17).

Lê, do BASE_DIR:
    processed/perfis_livros.csv     (etapas/perfis.py)
    processed/livros_analise.csv    (etapas/tratar.py, para as capas)
    processed/sobrevivencia.csv     (etapas/sobrevivencia.py)

e grava  livro/dados.js  no repositório (window.DADOS = {...}). É um .js,
e não um .json, para o livro funcionar abrindo o index.html direto do
disco, sem servidor.

Uso (a partir da raiz do projeto), depois da rotina diária:
    python -m booktrends.etapas.exportar_livro

Não roda no run_diario.py de propósito: o arquivo fica versionado no
repositório (é o que o GitHub Pages publica), então só é atualizado
quando você quiser uma nova versão do livro.
"""

import json
import logging

import pandas as pd

from booktrends.config import BASE_DIR, REPO_DIR
from booktrends.logging_setup import configurar_logging

logger = logging.getLogger(__name__)

SAIDA = REPO_DIR / "livro" / "dados.js"

# ordem dos perfis no livro (e código curto usado em cada livro)
PERFIS = ["Clássico vivo", "Fenômeno recente", "Esquecido", "Redescoberto / em alta", "Estável"]

# livros citados no texto do livro: aparecem com rótulo nos gráficos e no
# índice remissivo. Os que não estiverem na base são ignorados.
DESTAQUES = {
    "Clássico vivo": ["OL1168083W", "OL66554W", "OL27482W", "OL10263W"],
    "Fenômeno recente": ["OL18020194W", "OL82563W", "OL28952677W"],
    "Esquecido": ["OL1088783W", "OL1088888W", "OL361466W"],
    "Redescoberto / em alta": ["OL796465W", "OL872932W", "OL10432709W"],
}
N_DESTAQUES_AUTO = 3  # se faltar destaque num perfil, completa com os mais lidos dele


def _int(valor):
    return None if pd.isna(valor) else int(valor)


def _destaques(perfis):
    """IDs citados por perfil: os fixos que existem + os mais lidos do perfil."""
    ids = set(perfis["id_livro"])
    saida = {}
    for perfil in PERFIS[:-1]:
        fixos = [i for i in DESTAQUES.get(perfil, []) if i in ids]
        bloco = perfis[perfis["perfil"] == perfil]
        # esquecido: os mais reeditados; os outros: os mais lidos
        chave = "qtd_edicoes" if perfil == "Esquecido" else "leitores"
        extras = [i for i in bloco.sort_values(chave, ascending=False)["id_livro"] if i not in fixos]
        saida[perfil] = (fixos + extras)[: max(len(fixos), N_DESTAQUES_AUTO)]
    return saida


def montar(perfis, analise, sobrevivencia):
    capas = analise.set_index("id_livro")["cover_id"] if "cover_id" in analise.columns else pd.Series(dtype=float)
    perfis = perfis.copy()
    perfis["cover_id"] = perfis["id_livro"].map(capas)

    destaques = _destaques(perfis)

    livros = [
        [
            r.id_livro,
            r.titulo_exibicao if isinstance(r.titulo_exibicao, str) else r.titulo,
            r.autor_principal if isinstance(r.autor_principal, str) else "",
            _int(r.ano_publicacao),
            r.genero_principal if isinstance(r.genero_principal, str) else "",
            _int(r.leitores),
            _int(r.qtd_edicoes),
            PERFIS.index(r.perfil) if r.perfil in PERFIS else len(PERFIS) - 1,
            _int(r.cover_id),
        ]
        for r in perfis.itertuples(index=False)
    ]

    resumo = []
    for perfil in PERFIS:
        bloco = perfis[perfis["perfil"] == perfil]
        resumo.append({
            "perfil": perfil,
            "livros": int(len(bloco)),
            "mediana_leitores": float(bloco["leitores"].median()),
            "mediana_edicoes": float(bloco["qtd_edicoes"].median()),
            "mediana_idade": float(bloco["idade"].median()),
            "pct_leitores": round(float(bloco["leitores"].sum() / perfis["leitores"].sum() * 100), 1),
        })

    sobrev = sobrevivencia[sobrevivencia["exibir"]].sort_values(["genero", "ordem"])
    curvas = {
        genero: [[r.faixa_idade, int(r.livros), float(r.pct_vivos)] for r in bloco.itertuples(index=False)]
        for genero, bloco in sobrev.groupby("genero")
    }

    meta = {
        "livros": int(len(perfis)),
        "primeira_coleta": str(perfis["data_primeira_coleta"].min()),
        "ultima_coleta": str(perfis["data_coleta"].max()),
        "limiar_vivo": float(sobrevivencia["limiar_leitores"].iloc[0]) if len(sobrevivencia) else None,
        "com_edicao_pt": int(perfis["tem_pt"].astype(str).str.lower().eq("true").sum()) if "tem_pt" in perfis else None,
        "campos_livro": ["id", "titulo", "autor", "ano", "genero", "leitores", "edicoes", "perfil", "capa"],
    }
    return {"meta": meta, "perfis": PERFIS, "livros": livros, "resumo": resumo,
            "destaques": destaques, "sobrevivencia": curvas}


def main():
    arquivos = {
        "perfis": BASE_DIR / "processed" / "perfis_livros.csv",
        "analise": BASE_DIR / "processed" / "livros_analise.csv",
        "sobrevivencia": BASE_DIR / "processed" / "sobrevivencia.csv",
    }
    faltando = [str(c) for c in arquivos.values() if not c.exists()]
    if faltando:
        logger.error("Faltam arquivos: %s. Rode 'python run_diario.py' primeiro.", ", ".join(faltando))
        return

    tabelas = {k: pd.read_csv(c, encoding="utf-8-sig", low_memory=False) for k, c in arquivos.items()}
    dados = montar(tabelas["perfis"], tabelas["analise"], tabelas["sobrevivencia"])

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    SAIDA.write_text(f"// gerado por booktrends/etapas/exportar_livro.py\nwindow.DADOS = {texto};\n", encoding="utf-8")
    logger.info("-> %s (%d livros, %.0f KB)", SAIDA, len(dados["livros"]), SAIDA.stat().st_size / 1024)


if __name__ == "__main__":
    configurar_logging()
    main()
