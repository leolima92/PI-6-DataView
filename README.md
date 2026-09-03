# Book Trends

Coleta e acompanhamento da **popularidade de livros ao longo do tempo**.
A cada execução é gerado um *snapshot* das métricas de cada livro (quantas
pessoas querem ler, estão lendo, já leram, nota média etc.), e esses snapshots
são guardados no histórico — o que permite estudar como a popularidade
**cresce ao longo do tempo**.

Duas fontes:

- **[Open Library](https://openlibrary.org/)** — base principal: catálogo,
  métricas de leitura e nota média, por gênero.
- **[Google Books](https://developers.google.com/books)** — enriquecimento por
  ISBN: sinopse, categorias, editora, data de publicação (colunas `gb_*`).

O projeto é um pequeno pipeline **ETL** (Extract → Transform → Load) que salva
tudo em CSV, pronto para visualizar em Power BI, Python ou Tableau.

---

## Pipeline

```text
Open Library (search.json)
        │  GET paginado por gênero          (python coletar.py)
        ▼
   JSON bruto  ──►  raw/openlibrary_AAAA-MM-DD.csv
        │  normalização
        ▼
   processed/livros.csv           (foto mais recente)
   processed/livros_generos.csv   (relação livro × gênero)
        │  histórico
        ▼
   historico/livros_AAAA-MM.csv   (snapshots do mês)

Google Books (volumes)
        │  GET por ISBN, com cache          (python merge.py)
        ▼
   processed/livros_merged.csv    (livros.csv + colunas gb_*)
        │
        ▼
   Power BI / Python / Tableau
```

`python run_diario.py` executa as duas etapas em sequência.

---

## Estrutura do projeto

```text
PI-6-DataView/
├── coletar.py                 # ponto de entrada da coleta Open Library
├── merge.py                   # ponto de entrada do merge Google Books
├── run_diario.py              # coletar + merge em sequência (uso agendado)
├── pipeline.py                # orquestra extract → transform → load
├── config.py                  # constantes, gêneros, campos, sessão HTTP
├── helpers.py                 # primeiro, lista_para_texto, escolher_isbn
├── extract/
│   ├── openlibrary.py         # buscar_pagina, coletar_genero        (EXTRACT)
│   └── googlebooks.py         # buscar_por_isbn, campos_google        (EXTRACT)
├── transform/
│   ├── normalizar.py          # normalizar, preparar_dados            (TRANSFORM)
│   └── google_books.py        # merge por ISBN, cache em disco        (TRANSFORM)
├── load/
│   └── csv_writer.py          # salvar_csv, salvar_historico          (LOAD)
├── scripts/
│   └── run_daily.ps1          # wrapper para o Agendador de Tarefas
├── requirements.txt
└── .env.example               # copie para .env
```

Para mexer em algo, vá direto ao lugar:

| Quero mudar…                             | Arquivo                       |
| --------------------------------------- | ----------------------------- |
| Gêneros, pasta de saída, ritmo, cota GB | `config.py`                   |
| Paginação / rate limit / requisições    | `extract/openlibrary.py`      |
| Consulta ao Google Books                | `extract/googlebooks.py`      |
| Esquema, limpeza, junções               | `transform/normalizar.py`     |
| Regras do merge por ISBN                | `transform/google_books.py`   |
| Formato/gravação dos CSVs               | `load/csv_writer.py`          |

---

## Requisitos

- Python 3.9+
- Dependências:

```bash
pip install -r requirements.txt
```

(`pandas`, `requests`, `python-dotenv`.)

### `.env`

Copie `.env.example` para `.env` e preencha:

```ini
# Chave da API do Google Books (https://console.cloud.google.com/apis/credentials)
GOOGLE_BOOKS_API_KEY=sua_chave_aqui

# Pasta onde os CSVs são salvos. Opcional.
# Sem isso, usa ./data na raiz do projeto.
# BOOK_TRENDS_DIR=G:/Meu Drive/book-trends
```

O `.env` **não** é versionado. Sem `GOOGLE_BOOKS_API_KEY` a coleta da Open
Library funciona normalmente; o Google Books fica limitado pela cota anônima
(e pode retornar HTTP 403).

---

## Como rodar

A partir da raiz do projeto:

```bash
python coletar.py     # 1) Open Library  -> processed/livros.csv
python merge.py        # 2) Google Books  -> processed/livros_merged.csv
```

Ou tudo de uma vez:

```bash
python run_diario.py
```

Os arquivos são gravados em `BASE_DIR` (ver `.env` acima). As subpastas
`raw/`, `processed/`, `historico/` e `cache/` são criadas automaticamente.

---

## Rodar 1x por dia (Windows)

O histórico deduplica por `id_livro + data_coleta` e o Google Books tem cache
em disco, então rodar diariamente constrói a série temporal sem retrabalho.

`scripts/run_daily.ps1` vai para a raiz do repo, roda `run_diario.py` e grava
um log datado em `logs/`. Para registrar no Agendador de Tarefas (PowerShell):

```powershell
schtasks /create /tn "BookTrends - Coleta Diaria" /sc daily /st 03:00 /f /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"CAMINHO\PARA\PI-6-DataView\scripts\run_daily.ps1\""
```

- Troque `03:00` pelo horário desejado (`/st HH:MM`).
- Testar agora: `schtasks /run /tn "BookTrends - Coleta Diaria"` e ver
  `logs\coleta_AAAA-MM-DD.log`.
- Remover: `schtasks /delete /tn "BookTrends - Coleta Diaria" /f`.
- O PC precisa estar ligado e o usuário logado no horário. Para rodar após uma
  execução perdida, marque *"Executar a tarefa assim que possível após perda de
  um início agendado"* nas propriedades da tarefa (não configurável via
  `schtasks`).

---

## Configuração

Tudo que costuma mudar está em `config.py`:

| Constante            | O que faz                                                          |
| -------------------- | ----------------------------------------------------------------- |
| `BASE_DIR`           | Pasta de saída — vem de `BOOK_TRENDS_DIR` (`.env`), senão `./data` |
| `CONTACT_EMAIL`      | E-mail de contato (vai no `User-Agent`, exigido pela Open Library) |
| `GENEROS`            | Mapa `nome do gênero → termo de busca` a coletar                  |
| `LIMIT_POR_PAGINA`   | Resultados por página (máx. 100)                                  |
| `MAX_PAGINAS`        | Páginas por gênero (padrão 20 → até ~2.000 livros por gênero)     |
| `PAUSA_SEGUNDOS`     | Pausa entre requisições (educação com a API)                     |
| `FIELDS`             | Campos pedidos à Open Library (inclui os de popularidade)        |
| `GOOGLE_BOOKS_API_KEY` | Chave da API do Google Books (lida do `.env`)                  |
| `GB_MAX_LIVROS`      | Máx. de livros consultados no Google Books por rodada (protege a cota) |
| `GB_PAUSA_SEGUNDOS`  | Pausa entre consultas ao Google Books                            |

---

## Arquivos gerados

| Arquivo                          | Conteúdo                                                        |
| -------------------------------- | ------------------------------------------------------------- |
| `raw/openlibrary_AAAA-MM-DD.csv` | Resposta bruta da Open Library (para auditoria)               |
| `processed/livros.csv`           | Uma linha por livro, no esquema do projeto (foto mais recente) |
| `processed/livros_generos.csv`   | Relação livro × gênero (um livro pode ter vários gêneros)     |
| `processed/livros_merged.csv`    | `livros.csv` + colunas `gb_*` do Google Books                 |
| `historico/livros_AAAA-MM.csv`   | Snapshots do mês — é o que permite estudar a tendência        |
| `cache/googlebooks.json`         | Cache de ISBNs já consultados no Google Books                 |

### Esquema de `livros.csv`

| Coluna              | Descrição                                            |
| ------------------- | ---------------------------------------------------- |
| `id_livro`          | ID do work na Open Library (ex.: `OL45804W`)         |
| `isbn`              | ISBN (preferência por ISBN-13)                       |
| `titulo`            | Título                                               |
| `autor` / `autor_id`| Autor(es) e respectivos IDs                          |
| `ano_publicacao`    | Ano da primeira publicação                           |
| `generos`           | Gêneros do livro (agrupados, separados por `;`)      |
| `editora`           | Editora                                              |
| `paginas`           | Nº mediano de páginas                                |
| `idioma`            | Idioma(s)                                            |
| `nota_media`        | Nota média (ratings)                                 |
| `qtd_avaliacoes`    | Quantidade de avaliações                             |
| `qtd_edicoes`       | Quantidade de edições                                |
| `want_to_read`      | Pessoas que querem ler                               |
| `currently_reading` | Pessoas lendo atualmente                             |
| `already_read`      | Pessoas que já leram                                 |
| `cover_id` / `url_capa` | ID e URL da capa                                 |
| `data_coleta`       | Data do snapshot (`AAAA-MM-DD`)                      |

### Colunas extras em `livros_merged.csv`

Vêm do Google Books, preenchidas só para os livros consultados (com ISBN,
priorizando os mais populares, até `GB_MAX_LIVROS` por rodada):

| Coluna               | Descrição                          |
| -------------------- | --------------------------------- |
| `gb_descricao`       | Sinopse                           |
| `gb_categorias`      | Categorias (separadas por `;`)    |
| `gb_nota_media`      | Nota média no Google Books        |
| `gb_qtd_avaliacoes`  | Quantidade de avaliações          |
| `gb_paginas`         | Nº de páginas                     |
| `gb_editora`         | Editora                           |
| `gb_data_publicacao` | Data de publicação                |
| `gb_link`            | Link para a página do volume      |

O histórico não duplica o mesmo livro na mesma `data_coleta`, então rodar a
coleta duas vezes no mesmo dia é seguro. A série temporal se forma pela
combinação `id_livro + data_coleta`.

---

## Observações importantes

- **User-Agent obrigatório.** A Open Library bloqueia coleta anônima. O
  `CONTACT_EMAIL` no `config.py` vira o `User-Agent` das requisições.
- **Campos de popularidade só vêm se pedir.** `ratings_*`,
  `want_to_read_count`, `currently_reading_count` e `already_read_count` só
  aparecem porque estão listados em `FIELDS`. Sem isso, essas colunas viriam
  vazias.
- **Cota do Google Books.** O merge só consulta livros com ISBN, prioriza os
  mais populares e para em `GB_MAX_LIVROS` por rodada. ISBNs já buscados ficam
  em `cache/googlebooks.json` e não são reconsultados. HTTP 403 geralmente é
  estouro de cota — use uma API key ou reduza `GB_MAX_LIVROS`.
- **A API não é para bases gigantes de uma vez.** A `search.json` limita
  paginação profunda; puxar dezenas de milhares num único run não é o caminho.
  Aqui a base cresce pelo **histórico**, sobre um conjunto focado de gêneros.
  Para um dump estático enorme, a via seria o dump mensal da Open Library.

---

## Fontes de dados

- [Open Library](https://openlibrary.org/), projeto do Internet Archive.
  Catálogo sob licença **CC0** (domínio público).
- [Google Books APIs](https://developers.google.com/books) — uso sujeito aos
  termos do serviço.
