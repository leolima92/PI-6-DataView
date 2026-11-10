from pathlib import Path
import os
import requests
from dotenv import load_dotenv

load_dotenv()
# PASTA DE SAÍDA
# Defina BOOK_TRENDS_DIR no .env para escolher onde os CSVs são salvos
# (ex.: BOOK_TRENDS_DIR=G:/Meu Drive/book-trends). Sem isso, usa ./data
# na raiz do projeto.
BASE_DIR = Path(os.getenv("BOOK_TRENDS_DIR") or Path(__file__).parent / "data")


def pasta_do_mes(subpasta, data):
    """Pasta mensal dentro do BASE_DIR, ex.: raw/2026-10."""
    return BASE_DIR / subpasta / f"{data:%Y-%m}"

# IDENTIFICAÇÃO (a Open Library exige um User-Agent com contato)
CONTACT_EMAIL = "leonardolima2003@gmail.com"
USER_AGENT = f"BookTrends/0.1 (projeto academico; contato: {CONTACT_EMAIL})"
# GÊNEROS
# nome canônico (vai para a coluna) -> termo usado no filtro subject:"..."
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

# AMOSTRAGEM
# Cada amostra = (ordenação da Search API, idioma ou None, nº de páginas).
# A coluna "amostra" guarda o nome da amostra de onde veio cada livro.
#
# "readinglog" traz os livros mais presentes nas estantes dos leitores, ou
# seja, livros conhecidos. Até nov/2026 a amostra principal era "key" (IDs
# mais antigos da Open Library), que trazia sobretudo livros obscuros, com
# 0 a 5 leitores, e foi desligada.
# "readinglog_pt" é a mesma ordenação, só com edições em português.
AMOSTRAS = {
    "readinglog": ("readinglog", None, MAX_PAGINAS),
    "readinglog_pt": ("readinglog", "por", 5),
}
# amostra obrigatória: se ela falhar, a coleta inteira falha
AMOSTRA_PRINCIPAL = "readinglog"

# Só coleta livros publicados até este ano (None = sem corte)
ANO_MAX_PUBLICACAO = 2020

# TRATAMENTO (tratar.py)
# Um livro só entra na base de análise se for "conhecido": tem pelo menos
# MIN_LEITORES leitores (want_to_read + currently_reading + already_read)
# OU pelo menos MIN_EDICOES edições. As edições seguram os clássicos
# esquecidos, que foram muito reeditados mas hoje têm poucos leitores.
MIN_LEITORES = 50
MIN_EDICOES = 20
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

# GOOGLE BOOKS (merge por ISBN)
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
GB_MAX_LIVROS = 500           # nº de livros a consultar por rodada (protege a cota)
GB_PAUSA_SEGUNDOS = 5.0       # pausa entre consultas ao Google Books
GB_ESPERA_RETRY = 5.0         # 1ª espera após 429/5xx; dobra a cada nova falha (máx. 60s)
GB_MAX_FALHAS_SEGUIDAS = 3    # ISBNs seguidos sem resposta antes de desistir do Google Books na rodada

# TÍTULOS EM PORTUGUÊS (traduzir_titulos.py)
TITULOS_MAX_POR_RODADA = 300  # obras novas consultadas por rodada (OL + Google Books)
TITULOS_GB_MAX = 200          # dessas, quantas podem ir ao Google Books (protege a cota)
