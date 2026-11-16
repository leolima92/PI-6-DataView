# Gráfico de edições × leitores por perfil

## Objetivo

Visualizar a relação entre a quantidade de edições e a quantidade de leitores das obras, distinguindo os diferentes perfis de popularidade.

Implementação referente à issue #11 do Projeto Integrador Book Trends.

## Fonte dos dados

O gráfico utiliza o arquivo:

`processed/perfis_livros.csv`

A base analisada contém 9.241 obras.

Dessas, 9.224 são representadas no gráfico. As outras 17 possuem valores incompatíveis com a escala logarítmica.

## Perfis representados

- Clássico vivo
- Fenômeno recente
- Esquecido
- Redescoberto / em alta
- Estável

Os livros classificados como Estável são apresentados com menor opacidade para destacar visualmente os quatro perfis principais.

## Características da visualização

- Gráfico de dispersão interativo.
- Escala logarítmica nos eixos X e Y.
- Uma cor por perfil de popularidade.
- Tooltips com título, autor, gênero, período, edições e leitores.
- Filtros combinados por gênero literário e período.
- Contador dinâmico de livros exibidos.
- Destaques de obras selecionadas.
- Exportação em HTML independente.

## Obras destacadas

- 1984 — George Orwell.
- O Alquimista — Paulo Coelho.
- The Brown Fairy Book — Andrew Lang.
- The Crimson Fairy Book — Andrew Lang.
- É assim que acaba (It Ends With Us) — Colleen Hoover.

Os destaques são identificados pelo ID da obra na Open Library.

## Como executar

Na raiz do projeto, instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Execute o módulo:

```powershell
python -m booktrends.etapas.grafico_edicoes_leitores
```

O arquivo HTML será gerado em:

`analise/graficos/edicoes_leitores_perfil.html`

O HTML pode ser aberto diretamente no navegador, sem necessidade de servidor.

## Limitações

- Os 17 registros com zero leitores não são representados na escala logarítmica, mas permanecem na base original.
- Os perfis dependem da classificação produzida pelo pipeline.
- Algumas classificações de gênero podem não corresponder à categorização literária convencional.
- A relação entre edições e leitores é descritiva e não demonstra causalidade.
- A visualização utiliza os dados disponíveis no momento da geração e precisa ser executada novamente para incorporar atualizações do CSV.

## Reutilização

A função `criar_grafico()` retorna um objeto Plotly que pode ser utilizado em outras aplicações Python.

A versão HTML permite incorporar a visualização às próximas etapas do projeto, incluindo o painel final.