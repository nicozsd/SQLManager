# Analytics 5.0

O SQLManager 5.0 introduz uma camada analítica separada do fluxo transacional. A proposta desta versão é permitir BI operacional, datasets semânticos e consultas agregadas sem usar o `AutoRouter` CRUD como engine de analytics.

## Objetivos

- Separar leitura analítica da escrita transacional.
- Permitir datasets semânticos com medidas e hierarquias.
- Suportar autodiscovery dos models existentes.
- Expor endpoints analíticos próprios.
- Integrar cache orientado a dataset e medida.

## Componentes

### Metadata

- `DataSource`: descreve a origem física ou lógica do dataset.
- `Dataset`: define dimensões, medidas, filtros padrão e TTL de cache.
- `Measure`: representa agregações como `count`, `sum`, `avg`, `min` e `max`.
- `Hierarchy`: modela hierarquias de navegação, como Ano > Mês > Dia.
- `SecurityPolicy`: aplica filtros obrigatórios e valores permitidos.

### Registry

O `AnalyticsRegistry` centraliza os datasets disponíveis e pode autodetectar classes em módulos como:

- `model.TablePack`
- `src.model.TablePack`
- `model.ViewPack`
- `src.model.ViewPack`

Cada dataset autodetectado recebe uma `Measure` padrão chamada `records`.

### Executor

O `DatasetExecutor` monta SQL agregado diretamente a partir do metadata do dataset. Ele valida dimensões, medidas e filtros, compila o `WHERE` usando os próprios operadores do SQLManager e executa a consulta pela conexão configurada.

### Router

O `AnalyticsRouter` expõe endpoints para consulta, catálogo e operação:

- `GET /analytics/catalog`
- `GET /analytics/datasets`
- `GET /analytics/datasets/{dataset_name}`
- `POST /analytics/query/{dataset_name}`
- `GET /analytics/materializations`
- `POST /analytics/materializations/{job_name}/run`
- `GET /analytics/ui`

Ele suporta Flask, FastAPI, Starlette e apps com `register_route`.

### Materialização

O `MaterializationScheduler` permite aquecer datasets recorrentes usando a mesma semântica do executor.

- jobs podem ser registrados em runtime ou via `analytics_config`
- execucao manual por endpoint ou programada em thread daemon
- opcionalmente invalida o dataset antes de recalcular
- reaproveita o `DataPulseCache` para manter os agregados quentes

## Configuração

```python
from SQLManager import CoreConfig

CoreConfig.configure_from_dict({
    "db_server": "localhost",
    "db_database": "AnalyticsDB",
    "db_user": "sa",
    "db_password": "secret",
    "analytics_config": {
        "enabled": True,
        "url_prefix": "analytics",
        "auto_discover_datasets": True,
        "datasets_modules": [
            "model.TablePack",
            "model.ViewPack",
        ],
        "cache_ttl": 180,
        "materializations": [
            {
                "name": "Tickets",
                "dataset_name": "Tickets",
                "payload": {
                    "dimensions": ["STATUS"],
                    "measures": ["records", "total_hours"],
                    "include_total": True,
                },
                "interval_seconds": 300,
                "invalidate_first": True,
            }
        ],
        "auto_start_materialization": True,
    },
})
```

## Exemplo de Dataset Semântico

```python
from SQLManager import Dataset, DataSource, Measure, Hierarchy, SecurityPolicy

TicketDataset = (
    Dataset(
        name="Tickets",
        source=DataSource(name="Tickets", model=TicketsTable),
        dimensions=["STATUS", "PRIORITY", "CREATEDDATE"],
        default_order_by="CREATEDDATE",
        cache_ttl=300,
    )
    .add_measure(Measure(name="records", aggregation="count"))
    .add_measure(Measure(name="total_hours", aggregation="sum", field="DURATIONHOURS"))
    .add_hierarchy(Hierarchy(name="calendar", levels=["YEAR", "MONTH", "DAY"]))
)

TicketDataset.security_policy = SecurityPolicy(
    name="support_rls",
    required_filters={"COMPANYID": None},
)
```

## Exemplo de Query

```python
from SQLManager.analytics.query import DatasetExecutor

executor = DatasetExecutor(db)
result = executor.execute("Tickets", {
    "dimensions": ["STATUS"],
    "measures": ["records", "total_hours"],
    "filters": {
        "CREATEDDATE_gte": "2026-01-01",
        "COMPANYID_eq": 10,
    },
    "include_total": True,
})
```

## Recomendações de Uso

- Use views analíticas ou tabelas agregadas como fonte do dataset sempre que possível.
- Separe o pool de leitura pesada do pool transacional.
- Use `AnalyticsRouter` para consultas BI e mantenha o `AutoRouter` para CRUD e integração operacional.
- Aplique `SecurityPolicy` quando houver RLS ou filtros mandatórios por tenant/empresa.
- Cacheie datasets quentes, não datasets gigantes inteiros.
- Use `/analytics/catalog` e `/analytics/ui` como porta de entrada para exploração semântica.
- Use o backend `database` do `DataPulseCache` quando precisar escalar horizontalmente sem Redis.

## Limites Deliberados da 5.0

- Não há modelador visual completo de métricas com drag and drop.
- A UI embutida e propositalmente leve e focada em operacao e validacao de datasets.
- O executor ainda depende do banco e da estrutura física do model de origem.
- O foco é BI operacional e APIs analíticas, não uma ferramenta self-service completa.