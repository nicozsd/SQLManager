# DataPulseCache, Lookup e WebSocket

O SQLManager agora possui um cache interno chamado `DataPulseCache`. Ele funciona em memória, usa o nome da tabela como chave principal e reduz leituras repetidas no banco para consultas feitas pelo `SelectManager`, pelo `AutoRouter` e por rotas de lookup.

## Como funciona

O cache é ativado por padrão. Cada consulta gera uma assinatura com tabela, versão da tabela, SQL montado, parâmetros e paginação. Quando ocorre insert, update ou delete pelos managers do SQLManager, a tabela afetada é invalidada e os próximos selects voltam ao banco para renovar os dados.

O cache não substitui o banco e não precisa de serviço externo. Ele foi criado para ter comportamento parecido com Redis dentro do próprio processo, mas recebeu outro nome para evitar dependência e confusão operacional.

## Configuração

```python
CoreConfig.configure_router({
    "enable_dynamic_routes": True,
    "enable_websocket": True,
    "data_pulse_cache": {
        "enabled": True,
        "ttl": 45,
        "max_entries": 2000
    }
})
```

Campos:

- `enabled`: ativa ou desativa o cache interno.
- `ttl`: tempo de vida das consultas em segundos.
- `max_entries`: limite total de entradas mantidas em memória.

## WebSocket

Quando `enable_websocket` está ativo, o AutoRouter cria o `WebSocketManager` se receber um app Flask compatível ou usa o objeto `socketio` fornecido. O manager agora aceita adaptadores com `emit`, `publish`, `broadcast`, `send_json` ou `send`, além de Flask-SocketIO e python-socketio.

Eventos emitidos:

- `db_notification`
- `db_data_sync`
- `connection_response`
- `subscribed`
- `unsubscribed`

As escritas invalidam o `DataPulseCache` antes dos próximos selects e continuam disparando os broadcasts.

## Lookup Configurado

As rotas de lookup são configuradas no AutoRouter. Elas aceitam `limit`, `page`, `batch` e `q`. O retorno segue o formato `status`, `data` e, quando `batch` é verdadeiro, `total`.

```python
CoreConfig.configure_router({
    "enable_dynamic_routes": True,
    "url_suffix": "manager",
    "lookup_routes": {
        "purchtable-lookup": {
            "path": "/purchtable-lookup",
            "table": "PurchTable_lkp",
            "columns": [
                "RECID",
                "REFERENCE",
                "PURCHID_NW",
                "REF_NUMBER",
                "PURCHDATE",
                "TRANSDATE",
                "VENDACCOUNT",
                "PURCHLINE"
            ],
            "search_columns": ["REFERENCE", "REF_NUMBER"],
            "order_by": "RECID",
            "ttl": 60
        },
        "productstable-lookup": {
            "path": "/productstable-lookup",
            "table": "ProductsTable",
            "columns": [
                "RECID",
                "ITEMID_SN",
                "ITEMID_NW",
                "ITEMNAME",
                "BRANDID",
                "CATEGORYID",
                "RAWMATERIAL",
                "EANID",
                "PURCH_UNITID",
                "MASTER_PACK",
                "ISDISABLE"
            ],
            "search_columns": ["ITEMNAME", "ITEMID_SN", "ITEMID_NW", "EANID"],
            "order_by": "RECID",
            "ttl": 60
        },
        "incotermtable-lookup": {
            "path": "/incotermtable-lookup",
            "table": "IncotermTable",
            "columns": ["RECID", "INCOTERMID", "[KEY]", "DESCRIPTION"],
            "search_columns": ["INCOTERMID", "[KEY]", "DESCRIPTION"],
            "order_by": "RECID",
            "ttl": 60
        }
    }
})
```

Também é possível configurar lookup dentro de uma tabela:

```python
CoreConfig.configure_router({
    "enable_dynamic_routes": True,
    "tables": {
        "ProductsTable": {
            "lookup": {
                "columns": ["RECID", "ITEMID_NW", "ITEMNAME"],
                "search_columns": ["ITEMID_NW", "ITEMNAME"],
                "order_by": "RECID"
            }
        }
    }
})
```

Nesse modo, a rota dinâmica da tabela também aceita o caminho `lookup`.

## Acesso ao Cache

```python
from SQLManager import data_pulse_cache

stats = data_pulse_cache.stats()
data_pulse_cache.invalidate_table("ProductsTable")
data_pulse_cache.clear()
```

