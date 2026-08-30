import pandas as pd

def salvar_csv(df, caminho):
    """Sobrescreve um CSV."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"  -> {caminho} ({len(df)} linhas)")


def salvar_historico(df, caminho):
    """
    Adiciona o snapshot ao histórico, evitando duplicar o mesmo livro
    na mesma data de coleta. Assim, rodar o programa duas vezes no mesmo
    dia não duplica registros.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)

    if caminho.exists():
        antigo = pd.read_csv(caminho, encoding="utf-8-sig")
        combinado = pd.concat([antigo, df], ignore_index=True)
    else:
        combinado = df.copy()

    combinado = combinado.drop_duplicates(
        subset=["id_livro", "data_coleta"], keep="last"
    )

    combinado.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"  -> {caminho} ({len(combinado)} linhas no histórico)")
