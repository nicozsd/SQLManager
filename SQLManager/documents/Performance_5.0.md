# Performance 5.0

Este documento responde a pergunta correta: em quais cenarios o SQLManager 5.0 pode ser mais rapido que o Power BI e como provar isso com numeros.

## Resposta curta

Nao e tecnicamente honesto afirmar que o SQLManager e sempre mais rapido que o Power BI em qualquer selecao.

O que da para afirmar matematicamente e isto:

- contra Power BI em `DirectQuery`, o SQLManager tem menos camadas entre o cliente e o banco, entao o limite inferior de latencia tende a ser menor
- contra Power BI em `Import`, o VertiPaq roda em memoria e pode ser mais rapido que consultas diretas ao banco
- com `DataPulseCache` quente, o SQLManager pode ficar mais rapido que ambos em consultas repetidas sobre o mesmo recorte

## Modelo matematico

### SQLManager sem cache

Para uma consulta indexada seletiva, a latencia pode ser aproximada por:

$$
T_{sqlm} = T_{rede} + T_{driver} + T_{parse} + T_{plan} + T_{seek} + T_{fetch} + T_{serialize}
$$

Em uma busca por indice B-tree, o custo dominante do acesso ao banco tende a seguir:

$$
T_{seek} \propto O(\log_B N) + O(k)
$$

onde:

- $N$ e a cardinalidade da tabela
- $B$ e o branching factor do indice
- $k$ e o numero de linhas retornadas

### SQLManager com cache quente

Quando a consulta cai no `DataPulseCache`, o custo vira:

$$
T_{sqlm-cache-hit} = T_{hash} + T_{lookup} + T_{deserialize}
$$

Na pratica, se o payload estiver em memoria local, esse caminho tende a ser muito menor que uma ida completa ao banco.

### Power BI DirectQuery

No `DirectQuery`, o Power BI adiciona camadas semanticas e de visualizacao:

$$
T_{pbi-dq} = T_{visual} + T_{dax} + T_{gateway} + T_{fonte}
$$

Como $T_{fonte}$ contem essencialmente a mesma consulta ao banco, o SQLManager tende a levar vantagem quando:

$$
T_{visual} + T_{dax} + T_{gateway} > T_{sqlm-overhead}
$$

Isso e comum em APIs de leitura, lookups e dashboards operacionais com filtros simples.

### Power BI Import

No `Import`, o Power BI trabalha sobre dados comprimidos em memoria:

$$
T_{pbi-import} = T_{visual} + T_{vertipaq} + T_{measure}
$$

Para agregacoes e slicing sobre modelo ja carregado em memoria, esse caminho pode ser menor que o SQLManager direto no banco. Por isso, a afirmacao universal de superioridade seria falsa.

## Regra pratica correta

- Se a comparacao for `SQLManager vs Power BI DirectQuery`, o SQLManager pode ser mais rapido em selecoes simples e consultas operacionais.
- Se a comparacao for `SQLManager vs Power BI Import`, o Power BI pode ser mais rapido em analise interativa sobre modelo carregado em memoria.
- Se a comparacao for `SQLManager com cache quente vs qualquer modo sem cache equivalente`, o SQLManager pode vencer em consultas repetidas.

## Como provar no seu ambiente

Use o harness interno de benchmark:

```python
from SQLManager.analytics.query import DatasetExecutor
from SQLManager.benchmarks import benchmark_dataset_query

executor = DatasetExecutor(db)
result = benchmark_dataset_query(
    executor,
    'Tickets',
    {
        'dimensions': ['STATUS'],
        'measures': ['records'],
        'filters': {'COMPANYID_eq': 10},
        'include_total': True,
    },
    iterations=100,
    warmup=10,
)

print(result.to_dict())
```

Compare isso com o `Performance Analyzer` do Power BI usando:

- mesmo banco
- mesmo filtro
- mesma cardinalidade de retorno
- mesma janela de tempo
- mesmo indice
- mesma infraestrutura

Olhe principalmente para:

- `avg_ms`
- `median_ms`
- `p95_ms`
- `p99_ms`

## O que ja foi otimizado na 5.0

- cache de resultado por dataset e versao no `DataPulseCache`
- backend `database` para compartilhamento horizontal sem Redis
- materializacao para aquecer consultas recorrentes
- cache de metadata do dataset no `DatasetExecutor` para evitar recomputacao por request

## Como deixar mais rapido que quase qualquer stack operacional

- indexe todas as colunas de filtro de alta seletividade
- crie indices compostos na ordem real dos filtros e ordenacoes
- use tabelas agregadas ou views materializadas para consultas BI repetidas
- mantenha `include_total=False` quando o total nao for necessario
- aqueça datasets quentes com `MaterializationScheduler`
- use `DataPulseCache` com backend `memory` ou `database` conforme a topologia
- evite `SELECT *` em endpoints de uso intenso
- se estiver em SQL Server, considere `columnstore` para fatos analiticos grandes

## Conclusao correta

Se o objetivo for API de leitura e BI operacional, o SQLManager 5.0 pode sim ficar mais rapido que o Power BI em `DirectQuery` e em consultas repetidas com cache quente.

Se o objetivo for afirmar que ele e sempre mais rapido que o Power BI em qualquer selecao, essa afirmacao nao se sustenta matematicamente.