from pathlib import Path
import requests
# PASTA DE SAÍDA
BASE_DIR = Path("./book-trends")

# IDENTIFICAÇÃO (a Open Library exige um User-Agent com contato)
CONTACT_EMAIL = "leonardolima2003@gmail.com"
USER_AGENT = f"BookTrends/0.1 (projeto academico; contato: {CONTACT_EMAIL})"

# GÊNEROS
GENEROS = {
    "Fantasia": "fantasy",
    "Romance": "romance",
    "Terror": "horror",
    "Mistério": "mystery",
    "Ficção científica": "science fiction",
    "Biografia": "biography",
    "História": "history",
}

# CONTROLE DA COLETA

LIMIT_POR_PAGINA = 100
# 20 páginas × 100 livros = até 2.000 resultados por gênero
MAX_PAGINAS = 20
# Pausa conservadora entre chamadas
PAUSA_SEGUNDOS = 1.0
TIMEOUT = 30
MAX_RETRIES = 5


# CAMPOS DA OPEN LIBRARY

FIELDS = ",".join(
    [
        "key",
        "title",
        "author_name",
        "author_key",
        "first_publish_year",
        "isbn",
        "publisher",
        "number_of_pages_median",
        "language",
        "edition_count",
        "ratings_average",
        "ratings_count",
        "want_to_read_count",
        "currently_reading_count",
        "already_read_count",
        "cover_i",
    ]
)

# API / SESSÃO
URL = "https://openlibrary.org/search.json"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": USER_AGENT,
        "email": CONTACT_EMAIL,
        "Accept": "application/json",
    }
)