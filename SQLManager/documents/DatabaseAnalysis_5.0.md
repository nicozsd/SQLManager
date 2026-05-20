# Database Analysis 5.0

O `DatabaseAnalysisController` adiciona uma analise opcional de qualidade do banco dentro da camada de model do SQLManager.

Ele foi pensado para responder perguntas como:

- este banco esta fraco para transacoes?
- este banco esta razoavel para BI operacional?
- existem indices duplicados?
- existem FKs sem indice de apoio?
- quais indices eu deveria criar primeiro?
- qual o ganho estimado se eu aplicar determinada recomendacao?

## O que ele analisa

- tabelas e volume estimado de linhas
- presenca de primary key
- presenca de indice clustered quando o dialeto suporta isso
- catalogo de indices existentes com campos e colunas includas
- foreign keys sem cobertura por indice
- indices duplicados
- recomendacoes baseadas em padroes de consulta opcionais

## Onde usar

```python
from SQLManager import DatabaseAnalysisController

analysis = DatabaseAnalysisController(db)
report = analysis.analyze_database(
    query_patterns=[
        {
            "table": "SALESLINE",
            "filters_eq": ["COMPANYID", "STATUS"],
            "range_filters": ["CREATEDDATE"],
            "order_by": ["CREATEDDATE"],
            "include": ["AMOUNT"],
            "frequency": 12,
            "workload": "transaction",
        }
    ]
)

for row in report["grid"]:
    print(row["table"], row["index"], row["fields"], row["estimated_gain_pct"])
```

## Estrutura do report

O retorno principal inclui:

- `summary`: score transacional, score BI, contagem de tabelas, indices, constraints e issues
- `tables`: catalogo resumido por tabela
- `columns`: colunas mapeadas por tabela
- `indexes`: indices existentes com campos
- `foreign_keys`: relacoes catalogadas
- `constraints`: constraints encontradas
- `issues`: problemas encontrados
- `recommendations`: DDLs sugeridos e ganho estimado
- `grid`: formato pronto para UI ou tabela no host

## Grid esperado

Cada linha do `grid` segue o formato:

- `table`
- `index`
- `fields`
- `included_fields`
- `kind`
- `category`
- `workload`
- `estimated_gain_pct`
- `severity`
- `reason`
- `ddl`
- `action`

Isso atende o fluxo visual do tipo:

`tabela -> index -> campos -> ganho estimado`

## Ganho estimado

O campo `estimated_gain_pct` e uma heuristica, nao uma garantia.

Ele considera principalmente:

- volume estimado da tabela
- frequencia informada do padrao de consulta
- tipo de workload (`transaction`, `bi` ou `hybrid`)
- numero de colunas chave sugeridas

Em outras palavras: ele serve para priorizacao, nao para prometer performance real sem benchmark.

## Dry Run e aplicacao

Por padrao, use o report como recomendacao.

Se quiser transformar em plano de execucao:

```python
planned = analysis.apply_recommendations(report["recommendations"], dry_run=True)
```

Se quiser executar explicitamente no banco:

```python
executed = analysis.apply_recommendations(report["recommendations"], dry_run=False)
```

## Limites atuais

- nao substitui o plano de execucao real do banco
- nao estima fragmentacao fisica nem skew estatistico
- nao cria indices temporarios automaticos durante `SELECT`
- nao consulta DMV de missing indexes em profundidade
- o ganho percentual e heuristico

## Proximo nivel possivel

Se quiser evoluir isso depois, os proximos passos naturais sao:

- capturar workload real de `SELECT` no SQLManager e alimentar recomendacoes automaticamente
- integrar DMVs de SQL Server para missing indexes e waits
- adicionar score por schema, tenant e modulo
- expor o report em UI com filtros e ordenacao