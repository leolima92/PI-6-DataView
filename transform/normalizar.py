import pandas as pd
from helpers import primeiro, escolher_isbn

def normalizar(doc, data_coleta):
    """
    Converte um documento bruto da Open Library para o esquema
    utilizado pelo Book Trends.
    """
    # pode vir como "/works/OL45804W" ou "OL45804W"
    key = doc.get("key") or ""
    id_livro = key.split("/")[-1] if key else None

    # autores
    autores = doc.get("author_name") or []
    autor = "; ".join(autores) if isinstance(autores, list) else autores

    autores_ids = doc.get("author_key") or []
    autor_id = "; ".join(autores_ids) if isinstance(autores_ids, list) else autores_ids

    # idiomas
    idiomas = doc.get("language") or []
    idioma = "; ".join(idiomas) if isinstance(idiomas, list) else idiomas

    # capa
    cover_id = doc.get("cover_i")
    url_capa = (
        f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
    )

    return {
        "id_livro": id_livro,
        "isbn": escolher_isbn(doc.get("isbn")),
        "titulo": doc.get("title"),
        "autor_id": autor_id,
        "autor": autor,
        "ano_publicacao": doc.get("first_publish_year"),
        "genero": doc.get("_genero"),
        "amostra": doc.get("_amostra"),
        "editora": primeiro(doc.get("publisher")),
        "paginas": doc.get("number_of_pages_median"),
        "idioma": idioma,
        "nota_media": doc.get("ratings_average"),
        "qtd_avaliacoes": doc.get("ratings_count"),
        "qtd_edicoes": doc.get("edition_count"),
        "want_to_read": doc.get("want_to_read_count"),
        "currently_reading": doc.get("currently_reading_count"),
        "already_read": doc.get("already_read_count"),
        "cover_id": cover_id,
        "url_capa": url_capa,
        "data_coleta": data_coleta,
    }


def preparar_dados(brutos, data_coleta):
    """
    Cria:

    1) tabela principal de livros
    2) tabela livro x gênero

    Isso evita perder informação quando um livro aparece em vários gêneros.
    """
    linhas = [normalizar(doc, data_coleta) for doc in brutos]
    df_long = pd.DataFrame(linhas)

    # remove linhas sem id
    df_long = df_long[df_long["id_livro"].notna()].copy()

    # tabela livro x gênero
    df_generos = (
        df_long[["id_livro", "genero"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["id_livro", "genero"])
        .reset_index(drop=True)
    )

    # junta os gêneros de cada livro num único texto
    generos_agrupados = (
        df_generos.groupby("id_livro")["genero"]
        .apply(lambda valores: "; ".join(sorted(set(valores))))
        .rename("generos")
    )

    # ordenações (amostras) em que o livro apareceu, ex.: "key; readinglog"
    amostras_agrupadas = (
        df_long[["id_livro", "amostra"]]
        .dropna()
        .groupby("id_livro")["amostra"]
        .apply(lambda valores: "; ".join(sorted(set(valores))))
    )

    # uma linha por livro
    df_livros = (
        df_long.drop(columns=["genero", "amostra"])
        .drop_duplicates(subset=["id_livro"], keep="first")
        .merge(generos_agrupados, on="id_livro", how="left")
        .merge(amostras_agrupadas, on="id_livro", how="left")
        .reset_index(drop=True)
    )

    # tipos numéricos
    colunas_numericas = [
        "ano_publicacao",
        "paginas",
        "nota_media",
        "qtd_avaliacoes",
        "qtd_edicoes",
        "want_to_read",
        "currently_reading",
        "already_read",
    ]
    for coluna in colunas_numericas:
        if coluna in df_livros.columns:
            df_livros[coluna] = pd.to_numeric(df_livros[coluna], errors="coerce")

    return df_livros, df_generos
