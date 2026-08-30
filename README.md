# Book Trends

Coleta e acompanhamento da **popularidade de livros ao longo do tempo** a partir
da [Open Library](https://openlibrary.org/). A cada execução é gerado um
*snapshot* das métricas de cada livro (quantas pessoas querem ler, estão lendo,
já leram, nota média etc.), e esses snapshots são guardados no histórico — o que
permite estudar como a popularidade **cresce mês a mês**.

O projeto é um pequeno pipeline **ETL** (Extract → Transform → Load) que salva
tudo em CSV, pronto para visualizar em Power BI, Python ou Tableau.

---

## Pipeline

```text
Open Library (search.json)
        │  GET paginado por gênero
        ▼
   JSON bruto  ──►  raw/openlibrary_AAAA-MM-DD.csv
        │  normalização
        ▼
   processed/livros.csv           (foto mais recente)
   processed/livros_generos.csv   (relação livro × gênero)
        │  histórico
        ▼
   historico/livros_AAAA-MM.csv   (snapshots do mês)
        │
        ▼
   Power BI / Python / Tableau
```

---

## Estrutura do projeto

```text
book-trends/
├── coletar.py                    # ponto de entrada: python coletar.py
└── booktrends/                   # pacote com o pipeline
    ├── config.py                 # constantes, gêneros, campos, sessão HTTP
    ├── common/
    │   └── utils.py              # primeiro, lista_para_texto, escolher_isbn
    ├── extract/
    │   └── openlibrary.py        # buscar_pagina, coletar_genero      (EXTRACT)
    ├── transform/
    │   └── normalizar.py         # normalizar, preparar_dados         (TRANSFORM)
    ├── load/
    │   └── csv_writer.py         # salvar_csv, salvar_historico       (LOAD)
    └── pipeline.py               # orquestra extract → transform → load
```

Cada estágio do ETL é uma pasta. Para mexer em algo, você vai direto ao lugar:

| Quero mudar…                          | Arquivo                        |
| ------------------------------------- | ------------------------------ |
| Gêneros, pasta de saída, e-mail, ritmo | `booktrends/config.py`         |
| Paginação / rate limit / requisições  | `booktrends/extract/openlibrary.py` |
| Esquema, limpeza, junções             | `booktrends/transform/normalizar.py` |
| Formato/gravação dos CSVs             | `booktrends/load/csv_writer.py` |

---

## Requisitos

- Python 3.9+
- Bibliotecas:

```bash
pip install requests pandas
```

---

## Como rodar

A partir da pasta que contém `coletar.py`:

```bash
python coletar.py
```

Os arquivos são gravados dentro da pasta definida em `BASE_DIR`
(`booktrends/config.py`). As subpastas `raw/`, `processed/` e `historico/`
são criadas automaticamente. Aponte `BASE_DIR` para a pasta sincronizada
com o Google Drive se quiser subir a base direto.

---

## Configuração

Tudo que costuma mudar está em `booktrends/config.py`:

| Constante          | O que faz                                                        |
| ------------------ | ---------------------------------------------------------------- |
| `BASE_DIR`         | Pasta onde os CSVs são salvos                                    |
| `CONTACT_EMAIL`    | E-mail de contato (vai no `User-Agent`, exigido pela Open Library) |
| `GENEROS`          | Mapa `nome do gênero → termo de busca` a coletar                 |
| `LIMIT_POR_PAGINA` | Resultados por página (máx. 100)                                 |
| `MAX_PAGINAS`      | Páginas por gênero (padrão 20 → até ~2.000 livros por gênero)    |
| `PAUSA_SEGUNDOS`   | Pausa entre requisições (educação com a API)                    |
| `FIELDS`           | Campos pedidos à API (inclui os de popularidade)                |

---

## Arquivos gerados

| Arquivo                          | Conteúdo                                                        |
| -------------------------------- | -------------------------------------------------------------- |
| `raw/openlibrary_AAAA-MM-DD.csv` | Resposta bruta da API (para auditoria)                         |
| `processed/livros.csv`           | Uma linha por livro, no esquema do projeto (foto mais recente) |
| `processed/livros_generos.csv`   | Relação livro × gênero (um livro pode ter vários gêneros)      |
| `historico/livros_AAAA-MM.csv`   | Snapshots do mês — é o que permite estudar a tendência         |

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

O histórico não duplica o mesmo livro na mesma `data_coleta`, então rodar a
coleta duas vezes no mesmo dia é seguro. Se quiser mais de um ponto por período,
rode em datas diferentes — a série temporal se forma pela combinação
`id_livro + data_coleta`.

---

## Observações importantes

- **User-Agent obrigatório.** A Open Library bloqueia coleta anônima. O
  `CONTACT_EMAIL` no `config.py` vira o `User-Agent` das requisições.
- **Campos de popularidade só vêm se pedir.** `ratings_*`,
  `want_to_read_count`, `currently_reading_count` e `already_read_count` só
  aparecem porque estão listados em `FIELDS`. Sem isso, essas colunas viriam
  vazias.
- **A API não é para bases gigantes de uma vez.** A `search.json` limita
  paginação profunda; puxar dezenas de milhares num único run não é o caminho.
  Aqui a base cresce pelo **histórico**, sobre um conjunto focado de gêneros.
  Para um dump estático enorme, a via seria o dump mensal da Open Library.

---
## Fonte de dados

Dados da [Open Library](https://openlibrary.org/), um projeto do Internet
Archive. Catálogo sob licença **CC0** (domínio público).
