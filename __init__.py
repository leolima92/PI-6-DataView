"""
Pacote de coleta do projeto Book Trends.

Pipeline ETL sobre a Search API da Open Library. Configuração e execução do processo de coleta de dados sobre livros, autores e gêneros.
Estrutura do pacote:
    config.py         -> constantes, gêneros e sessão HTTP
    common/           -> funções auxiliares (listas, ISBN)
    extract/          -> requisições paginadas às fontes (Open Library)
    transform/        -> normalização e montagem das tabelas
    load/             -> gravação em CSV (snapshot e histórico)
    pipeline.py       -> orquestra extract -> transform -> load

Ponto de entrada: o arquivo coletar.py na raiz do projeto.
"""
__version__ = "0.1.0"
