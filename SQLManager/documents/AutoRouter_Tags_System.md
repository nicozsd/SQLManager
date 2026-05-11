# Sistema de Rotas com TAGs - AutoRouter

## Visão Geral

O **AutoRouter** agora organiza automaticamente todas as rotas em **TAGs** (grupos lógicos) para melhor organização e documentação. O modelo de agrupamento segue a estrutura:

```
Model
├── Tabelas (CRUD das tabelas)
├── Enums (Acesso aos Enums do projeto)
└── EDTs (Acesso aos EDTs do projeto)
```

## Estrutura de TAGs

### 1. **Model - Tabelas**
Rotas CRUD padrão para tabelas e views do banco de dados.

**Padrão de rotas:**
```
GET    /{suffix}/{table_name}              - Listar registros (com filtros e paginação)
POST   /{suffix}/{table_name}              - Criar novo registro
GET    /{suffix}/{table_name}/{id}         - Obter registro por ID
PATCH  /{suffix}/{table_name}/{id}         - Atualizar registro
DELETE /{suffix}/{table_name}/{id}         - Deletar registro
```

**Exemplo:**
```
GET    /manager/products               - Listar produtos
POST   /manager/products               - Criar produto
GET    /manager/products/123           - Obter produto 123
PATCH  /manager/products/123           - Atualizar produto 123
DELETE /manager/products/123           - Deletar produto 123
```

---

### 2. **Model - Enums**
Acesso aos Enums (Enumerações) do projeto com múltiplas operações.

**Padrão de rotas:**
```
GET  /{suffix}/enums/{enum_name}          - Retorna map completo (keys → labels)
GET  /{suffix}/enums/{enum_name}/keys     - Lista todas as chaves
GET  /{suffix}/enums/{enum_name}/values   - Lista todos os valores
GET  /{suffix}/enums/{enum_name}/labels   - Lista todos os labels
```

**Exemplo com Enum `NoYes`:**
```
GET /manager/enums/NoYes
↓ Response:
{
    "status": 200,
    "data": [
        { "value": 0, "label": "Não" },
        { "value": 1, "label": "Sim" }
    ],
    "meta": { "enum": "NoYes", "operation": "map" }
}

GET /manager/enums/NoYes/keys
↓ Response:
{
    "status": 200,
    "data": ["No", "Yes"],
    "meta": { "enum": "NoYes", "operation": "keys" }
}

GET /manager/enums/NoYes/values
↓ Response:
{
    "status": 200,
    "data": [0, 1],
    "meta": { "enum": "NoYes", "operation": "values" }
}

GET /manager/enums/NoYes/labels
↓ Response:
{
    "status": 200,
    "data": ["Não", "Sim"],
    "meta": { "enum": "NoYes", "operation": "labels" }
}
```

---

### 3. **Model - EDTs** 
Acesso aos EDTs (Enhanced Data Types) do projeto com validação e testes.

**Padrão de rotas:**
```
GET  /{suffix}/edts/{edt_name}          - Informações do EDT
GET  /{suffix}/edts/{edt_name}/validate - Valida um valor contra o EDT
GET  /{suffix}/edts/{edt_name}/test     - Testa conversões de tipo
```

**Exemplo com EDT `Recid`:**

#### Obter informações do EDT:
```
GET /manager/edts/Recid

Response:
{
    "status": 200,
    "data": {
        "name": "Recid",
        "regex_type": "onlyNumbers",
        "type_id": "int",
        "default_value": "0"
    },
    "meta": { "edt": "Recid", "operation": "info" }
}
```

#### Validar um valor:
```
GET /manager/edts/Recid/validate?value=12345

Response (válido):
{
    "status": 200,
    "data": {
        "valid": true,
        "value": "12345",
        "type": "int"
    },
    "meta": { "edt": "Recid", "operation": "validate" }
}

Response (inválido):
{
    "status": 400,
    "data": {
        "valid": false,
        "error": "Valor não corresponde ao padrão esperado"
    },
    "meta": { "edt": "Recid", "operation": "validate" }
}
```

#### Testar conversões de tipo:
```
GET /manager/edts/Recid/test?value=42

Response:
{
    "status": 200,
    "data": {
        "original": "42",
        "as_string": "42",
        "as_int": 42,
        "as_float": 42.0,
        "as_bool": true
    },
    "meta": { "edt": "Recid", "operation": "test" }
}
```

---

## Como Usar com Diferentes Frameworks

### Flask
As tags são adicionadas aos metadados do handler (acessível via `handler.tag`).

```python
app = Flask(__name__)
router = AutoRouter(db, app=app)

# As rotas são registradas automaticamente com tags
# Tags estarão disponíveis em ferramentas que as leem (ex: Swagger/OpenAPI)
```

### FastAPI
As tags são registradas nativamente no FastAPI e aparecem automaticamente na documentação Swagger.

```python
from fastapi import FastAPI
app = FastAPI()
router = AutoRouter(db, app=app)

# Acesse a documentação em: http://localhost:8000/docs
# As rotas estarão agrupadas por tags!
```

### Starlette
As tags são adicionadas aos metadados do handler.

```python
from starlette.applications import Starlette
app = Starlette()
router = AutoRouter(db, app=app)
```

---

## Métodos para Acessar as Rotas Organizadas

### `get_route_definitions()` - Todas as rotas com tags
```python
router = AutoRouter(db)
rotas = router.get_route_definitions()

# Cada rota tem:
# {
#     "path": "...",
#     "methods": [...],
#     "endpoint": "...",
#     "handler": ...,
#     "tag": "Model - Tabelas"  ← TAG aqui!
# }
```

### `get_routes_by_tag()` - Rotas agrupadas por TAG
```python
router = AutoRouter(db)
rotas_por_tag = router.get_routes_by_tag()

# Resultado:
# {
#     "Model - Tabelas": [...],
#     "Model - Enums": [...],
#     "Model - EDTs": [...]
# }
```

### `get_registered_routes()` - Compatibilidade com estrutura anterior
```python
router = AutoRouter(db)
rotas = router.get_registered_routes()

# Retorna rotas por tabela (com tags agora)
```

---

## Exemplo Completo com FastAPI

```python
from fastapi import FastAPI
from SQLManager import AutoRouter, database_connection

# Configurar conexão
db = database_connection(...)

# Criar app e router
app = FastAPI(title="SQLManager API")
router = AutoRouter(db, app=app)

# Listar rotas por TAG
print("Rotas organizadas por TAG:")
for tag, rotas in router.get_routes_by_tag().items():
    print(f"\n{tag}:")
    for rota in rotas:
        print(f"  {rota['methods']} {rota['path']}")

# Executar
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # Acesse: http://localhost:8000/docs
```

---

## Configuração em CoreConfig

As rotas com TAGs são geradas automaticamente. Você pode configurar:

```python
{
    "enable_dynamic_routes": True,
    "url_suffix": "manager",
    
    # EDTs e Enums são descobertos automaticamente
    # Nenhuma configuração especial necessária!
    
    "tables": {
        "Products": {
            "allowed_methods": ["GET", "POST", "PATCH", "DELETE"]
        }
    }
}
```

---

## Benefícios do Sistema de TAGs

✅ **Melhor organização** - Rotas agrupadas logicamente  
✅ **Documentação automática** - FastAPI/Swagger usam tags automaticamente  
✅ **Descoberta fácil** - Métodos para listar rotas por TAG  
✅ **Compatibilidade** - Funciona com Flask, FastAPI, Starlette  
✅ **WebSocket ready** - Tags funcionam com rotas WebSocket também  

---