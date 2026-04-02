# Início Rápido - SQLManager Privado

Este documento mostra os comandos essenciais para configurar e usar o SQLManager.

---

## 📋 Pré-requisitos

- Python 3.8+
- Git instalado
- Acesso ao repositório privado Avalon-Tecnologia/SQLManager
- Banco de dados SQL Server configurado

---

## 1️. Configurar SSH (Primeira Vez)

### Windows PowerShell

```powershell
# Gerar chave SSH
ssh-keygen -t ed25519 -C "seu.email@empresa.com"
# Pressione Enter 3 vezes

# Copiar chave pública
Get-Content ~\.ssh\id_ed25519.pub | Set-Clipboard

# Adicionar no GitHub:
# https://github.com/settings/keys
# Clicar "New SSH key" e colar

# Testar conexão
ssh -T git@github.com
# Esperado: "Hi username! You've successfully authenticated..."
```

### Linux/Mac

```bash
# Gerar chave
ssh-keygen -t ed25519 -C "seu.email@empresa.com"

# Copiar chave (Mac)
cat ~/.ssh/id_ed25519.pub | pbcopy

# Copiar chave (Linux)
cat ~/.ssh/id_ed25519.pub | xclip

# Adicionar no GitHub e testar (mesmo do Windows)
```

**Detalhes completos:** [SSH_SETUP.md](SSH_SETUP.md)

---

## 2️⃣ Criar Projeto (Novo)

```powershell
# Criar pasta do projeto
mkdir MeuProjeto
cd MeuProjeto

# Criar estrutura básica
mkdir src
New-Item -ItemType File -Path .env

# Editar .env (suas credenciais)
notepad .env
```

**Conteúdo do .env:**
```env
DB_SERVER=localhost
DB_DATABASE=MeuBanco
DB_USER=sa
DB_PASSWORD=SuaSenha123
DB_DRIVER=ODBC Driver 17 for SQL Server
```

---

## 3️⃣ Instalar SQLManager

### Opção A: Instalação Direta

```powershell
# Criar ambiente virtual
python -m venv .venv

# Ativar (Windows)
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate

# Instalar SQLManager
pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git

# Verificar
python -c "from SQLManager import CoreConfig; print('✅ Instalado')"
```

### Opção B: Via requirements.txt (Recomendado)

```powershell
# Copiar exemplo
copy .venv\Lib\site-packages\requirements.txt.example requirements.txt

# Editar e adicionar suas dependências
notepad requirements.txt

# Instalar tudo
pip install -r requirements.txt
```

---

## 4️⃣ Configurar Projeto

### Criar arquivo principal (app.py)

```powershell
New-Item -ItemType File -Path app.py
notepad app.py
```

**Conteúdo mínimo:**

```python
import os
from dotenv import load_dotenv
from SQLManager import CoreConfig
from SQLManager.connection import database_connection

# Carregar .env
load_dotenv()

# Configurar SQLManager
CoreConfig.configure(
    db_server=os.getenv('DB_SERVER'),
    db_database=os.getenv('DB_DATABASE'),
    db_user=os.getenv('DB_USER'),
    db_password=os.getenv('DB_PASSWORD')
)

# Testar conexão
def test_connection():
    db = database_connection()
    db.connect()
    results = db.doQuery("SELECT 'SQLManager OK!' as message")
    print(results[0]['message'])
    db.disconnect()

if __name__ == '__main__':
    test_connection()
```

### Executar teste

```powershell
python app.py
# Esperado: SQLManager OK!
```

---

## 5️⃣ Gerar Modelos do Banco

```powershell
# Gerar automaticamente
python -m SQLManager._model._model_update

# Resultado:
# src/model/EDTs/    ← Tipos de dados
# src/model/enum/    ← Enumerações
# src/model/tables/  ← Tabelas do banco
# src/model/views/   ← Views do banco
```

**Verificar:**

```powershell
ls src\model\tables\

# Deve listar suas tabelas:
# Products.py
# Categories.py
# Orders.py
# ...
```

---

## 6️⃣ Usar no Código

```python
from model import TablePack

# Instanciar tabela
from SQLManager.connection import database_connection
db = database_connection()
db.connect()

products = TablePack.Products(db)

# SELECT simples
for product in products.select():
    print(f"{product.NAME} - R$ {product.PRICE}")

# WHERE
for product in products.select().where(products.PRICE > 100):
    print(product.NAME)

# INSERT
products.NAME = "Novo Produto"
products.PRICE = 199.90
products.insert()

# UPDATE
products.select().where(products.RECID == 123).first()
products.PRICE = 179.90
products.update()

# DELETE
products.delete_from(where=products.ACTIVE == 0)

db.disconnect()
```

---

## 🔄 Atualizar SQLManager

```powershell
# Atualizar para versão mais recente
pip install --upgrade --force-reinstall git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git

# Regenerar modelos (se banco mudou)
python -m SQLManager._model._model_update
```

---

## 📦 Distribuir Projeto (Para Desenvolvedores)

Se você é desenvolvedor do SQLManager:

### 1. Fazer Build Ofuscado

```powershell
# Build automático (ofusca código)
python setup.py build
python setup.py sdist bdist_wheel
```

### 2. Testar Localmente

```powershell
# Criar ambiente de teste
python -m venv .venv_test
.\.venv_test\Scripts\Activate.ps1

# Instalar build local
cd dist
pip install -e .

# Testar
python -c "from SQLManager import CoreConfig; print('OK')"
```

### 3. Publicar no GitHub

```powershell
# Commitar mudanças (código fonte, NÃO o build)
git add SQLManager/ setup.py README.md
git commit -m "v4.2.2 - Nova funcionalidade"

# Tag da versão
git tag v4.2.2
git push origin main --tags
```

**Detalhes completos:** [BUILD_DEPLOY.md](BUILD_DEPLOY.md)

---

## 🛠️ Troubleshooting

### Não consegue conectar SSH

```powershell
ssh -T git@github.com
# Se falhar: seguir SSH_SETUP.md
```

### ImportError após instalar

```powershell
# Verificar instalação
pip show SQLManager

# Reinstalar
pip uninstall SQLManager
pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git
```

### Modelos não foram gerados

```powershell
# Executar manualmente
python -m SQLManager._model._model_update --server localhost --database MeuBanco --user sa --password senha
```

### Erro de conexão banco de dados

```powershell
# Verificar .env
cat .env

# Testar driver ODBC
odbcad32

# Listar drivers instalados
Get-OdbcDriver
```

---

## 📚 Documentação Completa

- [README.md](README.md) - Documentação principal
- [SSH_SETUP.md](SSH_SETUP.md) - Guia completo de SSH
- [BUILD_DEPLOY.md](BUILD_DEPLOY.md) - Build e publicação
- [SQLManager/controller/Instructions.md](SQLManager/controller/Instructions.md) - API Controllers
- [SQLManager/connection/Instructions.md](SQLManager/connection/Instructions.md) - API Connection

---

## 🆘 Suporte

**Email:** nicolas.santos@avalontecnologia.com.br  
**GitHub Issues:** https://github.com/Avalon-Tecnologia/SQLManager/issues

---

## ✅ Checklist de Setup

Antes de começar a desenvolver, confirme:

- [ ] SSH configurado e testado (`ssh -T git@github.com`)
- [ ] Ambiente virtual criado e ativado (`.venv`)
- [ ] SQLManager instalado (`pip show SQLManager`)
- [ ] Arquivo `.env` configurado
- [ ] Pasta `src/` criada
- [ ] Modelos gerados (`ls src/model/tables/`)
- [ ] Teste de conexão passou (`python app.py`)
- [ ] Importações funcionando (`from model import TablePack`)

**Tudo OK?** Você está pronto para desenvolver! 🎉
