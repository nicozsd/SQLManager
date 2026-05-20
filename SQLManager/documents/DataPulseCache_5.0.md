# DataPulseCache 5.0

O `DataPulseCache` foi evoluído na 5.0 para suportar backends plugáveis, invalidação por tag e uso orientado a analytics.

## O que mudou

- Backend `memory` continua como padrão.
- Novo backend `database` para compartilhar cache e versionamento usando o mesmo banco da aplicação.
- Novo backend `redis` para cenários distribuídos.
- Invalidação por tabela, dataset e tags arbitrárias.
- `remember()` com single-flight local para evitar avalanche.
- Namespace configurável.
- Estatísticas de backend incorporadas ao `stats()`.

## Conceitos

### Namespace

Permite isolar ambientes ou workloads diferentes:

- `sqlmanager`
- `sqlmanager_bi`
- `helpdesk_prod`

### Tags

Cada item pode ser associado a tags como:

- nome da tabela (`SALESTABLE`)
- dataset lógico (`DATASET:SALES`)
- qualquer recorte interno de invalidação

### Versionamento

A chave da consulta inclui as versões atuais de tabela e dataset. Quando uma tabela ou dataset é invalidado, a próxima consulta passa a gerar outra assinatura.

## Configuração

### Via `CoreConfig`

```python
CoreConfig.configure(
    data_pulse_cache_enabled=True,
    data_pulse_cache_ttl=90,
    data_pulse_cache_max_entries=5000,
    data_pulse_cache_backend="database",
    data_pulse_cache_namespace="helpdesk_bi",
)
```

### Via ambiente

```env
SQLMANAGER_CACHE_ENABLED=true
SQLMANAGER_CACHE_TTL=90
SQLMANAGER_CACHE_MAX_ENTRIES=5000
SQLMANAGER_CACHE_BACKEND=database
SQLMANAGER_CACHE_NAMESPACE=helpdesk_bi
SQLMANAGER_CACHE_REDIS_URL=redis://localhost:6379/0
SQLMANAGER_CACHE_COMPRESSION_MIN_BYTES=8192
```

## Backend `database` sem Redis

Quando voce nao puder usar Redis, o backend `database` reaproveita a conexao principal do SQLManager para manter:

- cache compartilhado entre processos e workers
- versoes de tabela e dataset compartilhadas
- invalidacao horizontal sem custo extra de infraestrutura

Ele cria duas estruturas por namespace:

- `<NAMESPACE>_CACHE`
- `<NAMESPACE>_CACHE_VERSIONS`

O bind da conexao e automatico nos fluxos de `Select_Manager`, `RouterController` e `DatasetExecutor`.

### Quando usar

- `memory`: desenvolvimento local, testes e processo unico.
- `database`: multiprocesso ou multiplos workers sem Redis.
- `redis`: workloads de alta concorrencia e cache distribuido dedicado.

## Uso Básico

```python
from SQLManager import data_pulse_cache

cache_key = data_pulse_cache.make_query_key(
    ["SalesTable"],
    "analytics",
    {"dimensions": ["STATUS"], "page": 1},
    dataset="Sales"
)

response = data_pulse_cache.remember(
    "SalesTable",
    cache_key,
    lambda: expensive_query(),
    ttl=300,
    tags=[data_pulse_cache.dataset_key("Sales")]
)
```

## Invalidação

```python
from SQLManager import data_pulse_cache

data_pulse_cache.invalidate_table("SalesTable")
data_pulse_cache.invalidate_dataset("Sales")
data_pulse_cache.invalidate_tags(["DASHBOARD:MAIN", "TENANT:10"])
```

## Redis em Produção

Para ambientes horizontais:

- use `SQLManager[redis]`
- configure `SQLMANAGER_CACHE_BACKEND=redis`
- isole namespaces por ambiente
- invalide por dataset ao atualizar agregados materializados

## Boas Práticas

- Use `memory` em desenvolvimento e testes locais.
- Use `database` quando houver múltiplos workers/processos e voce quiser evitar custo extra.
- Use `redis` quando houver múltiplos workers/processos com maior pressao de throughput e menor latencia.
- Cacheie resultados quentes de lookup, agregados e metadata.
- Evite guardar datasets completos de cardinalidade muito alta.
- Monitore `stats()` periodicamente.