# Issues [#6-UpdateModel Remodel](https://github.com/nickzsd/SQLManager/issues/6) - SQLManager

## O que foi feito
Foi realizada uma grande refatoração do sistema de atualização de modelos (`_model_update.py`), separando responsabilidades e tornando o código mais modular, organizado e manutenível. O código que estava em um único arquivo monolítico (~970 linhas) foi dividido em módulos especializados.

## Estrutura Criada

### **Pasta `_model/generators/`**
Contém definições de templates para elementos obrigatórios do sistema:

- **`edts.py`**: Define EDTs obrigatórios (Recid, RefRecid, TransDate, CreateDateTime)
- **`enums.py`**: Define Enums obrigatórios (DataType, NoYes)
- **`tables.py`**: Define Tables obrigatórias do sistema
- **`__init__.py`**: Exporta os dicionários `Ensures` de cada módulo

### **Pasta `_model/managers/`**
Contém gerenciadores para cada tipo de modelo:

- **`edts_mngs.py`**: Classe `EDT_Manager` para gerenciar EDTs
- **`enum_mngs.py`**: Classe `Enum_Manager` para gerenciar Enums
- **`table_mngs.py`**: Classe `Table_Manager` para gerenciar Tables
- **`view_mngs.py`**: Classe `View_Manager` para gerenciar Views
- **`__init__.py`**: Exporta todas as classes Manager

### **Arquivo `_model/_utils.py`**
Funções utilitárias para o sistema de atualização:

- `_clear_init_files_pre_import()`: Limpa arquivos __init__.py antes de importar
- `stepInfo()`: Exibe informações formatadas de cada passo da atualização

### **Arquivo `_model/__init__.py`**
Novo arquivo de inicialização que:

- Gerencia importação de dependências (python-dotenv)
- Configura ArgumentParser para aceitar parâmetros via linha de comando
- Carrega configurações do .env ou argumentos CLI
- Define paths do projeto
- Exporta todos os módulos necessários

## Novas Funcionalidades

### **1. Configuração via Linha de Comando**
Agora é possível executar o model update sem arquivo `.env`, passando parâmetros diretamente:

```powershell
python -m SQLManager._model._model_update --server xxx --database xxx --user xxx --password xxx --driver "ODBC Driver 17 for SQL Server"
```

**Parâmetros disponíveis:**
- `--server`: Servidor do banco de dados
- `--database`: Nome do banco de dados
- `--user`: Usuário do banco de dados
- `--password`: Senha do banco de dados
- `--driver`: Driver ODBC (padrão: "ODBC Driver 17 for SQL Server")

### **2. Sistema de Templates (Ensures)**
Elementos obrigatórios agora são definidos como templates em arquivos generators:

```python
# Em generators/edts.py
Ensures = {
    "Recid": '''código da classe Recid''',
    "TransDate": '''código da classe TransDate''',
    # ...
}
```

### **3. Método `ensurer`**
Novo método na classe `ModelUpdater` que garante a existência de arquivos obrigatórios:

```python
def ensurer(self, ref_Path: Path, content: str):
    '''Garante que arquivo exista com conteúdo específico'''
    if not ref_Path.exists():
        # Cria o arquivo
    else:
        # Confirma que já existe
```

## Mudanças Principais

### **_model_update.py**
```python
# ANTES: ~970 linhas com tudo em um arquivo
# - Funções soltas (ensure_datatype_enum, ensure_recid_edt)
# - Classes Manager dentro do arquivo
# - Configuração hardcoded

# DEPOIS: ~200 linhas focadas apenas na orquestração
from . import *

class ModelUpdater:
    def ensurer(self, ref_Path: Path, content: str):
        # Novo método para garantir arquivos obrigatórios
        
    def run(self):
        # Agora usa templates dos generators
        utils.stepInfo("00.1", "Garantindo Enums obrigatórios")
        for enum in enums.values():
            self.ensurer(self.enums_path, enum)
        
        utils.stepInfo("00.2", "Garantindo EDTs obrigatórios")
        for edt in EDTs.values():
            self.ensurer(self.edts_path, edt)
```

### **setup.py**
```python
install_requires=[
    "pyodbc>=4.0.0",
    "python-dotenv>=0.19.0",  # <- Nova dependência
],
```

### **README.md**
Adicionada seção explicando configuração sem `.env`:

```markdown
> **Se não houver `.env`**  
> Utilizar os parametros diretamento no comando CMD/Powershell
>**Parametros:**  
>- `--server`: Servidor do banco de dados.
> - `--database`: Banco de dados.
> - `--user`: Usuário do banco de dados.
> - `--password`: Senha do banco de dados.
> - `--driver`: Driver ODBC para SQL Server
```

## Benefícios

1. **Modularidade**: Código dividido em responsabilidades claras (generators, managers, utils)
2. **Manutenibilidade**: Mais fácil encontrar e modificar funcionalidades específicas
3. **Extensibilidade**: Adicionar novos EDTs/Enums obrigatórios é simples - basta editar os generators
4. **Flexibilidade**: Configuração via .env OU linha de comando
5. **Organização**: Estrutura de pastas clara e intuitiva
6. **Reutilização**: Managers podem ser importados e usados em outros contextos

## Principais Métodos dos Managers

### **EDT_Manager**
- `_scan_existing_edts()`: Escaneia EDTs existentes no diretório
- `_update_edts_init()`: Atualiza __init__.py do módulo EDTs

### **Enum_Manager**
- `_scan_existing_enums()`: Escaneia Enums existentes no diretório
- `_update_enums_init()`: Atualiza __init__.py do módulo Enums

### **Table_Manager**
- `_scan_existing_tables()`: Escaneia Tables existentes no diretório
- `_update_tables()`: Atualiza Tables baseadas no banco de dados
- `_update_tables_init()`: Atualiza __init__.py do módulo Tables
- `_update_single_table()`: Atualiza/Cria tabela específica
- `_update_existing_table()`: Atualiza tabela preservando métodos customizados
- `_generate_table_class()`: Gera código Python para classe de tabela
- `_detect_field_type()`: Detecta tipo apropriado de campo (EDT, Enum ou padrão)

### **View_Manager**
- `_scan_existing_views()`: Escaneia Views existentes no diretório
- `_update_views()`: Atualiza Views baseadas no banco de dados
- `_update_views_init()`: Atualiza __init__.py do módulo Views
- `_update_single_view()`: Atualiza/Cria view específica
- `_update_existing_view()`: Atualiza view preservando métodos customizados
- `_generate_View_class()`: Gera código Python para classe de view
- `_detect_field_type()`: Detecta tipo apropriado de campo (EDT, Enum ou padrão)

> **AVISO**: Todas as atualizações preservam completamente os métodos customizados e personalizações, atualizando apenas ENUMs ou EDTs faltantes.

## Compatibilidade
Todas as funcionalidades anteriores foram mantidas. A refatoração foi 100% compatível com código existente.