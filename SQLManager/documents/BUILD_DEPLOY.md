# Guia de Build e Deploy - SQLManager

Este documento descreve como preparar e distribuir o SQLManager com código ofuscado para proteger a propriedade intelectual.

## Índice

1. [Visão Geral](#visão-geral)
2. [Build Ofuscado](#build-ofuscado)
3. [Teste Local](#teste-local)
4. [Publicação no GitHub](#publicação-no-github)
5. [Desabilitação Temporária](#desabilitação-temporária)

---

## Visão Geral

O SQLManager utiliza **ofuscação de bytecode** para proteger o código-fonte durante a distribuição. O processo funciona assim:

1. **Desenvolvimento:** Código normal em `SQLManager/`
2. **Build:** Script compila `.py` → `.pyc` (bytecode)
3. **Distribuição:** Usuários recebem código ofuscado via `pip install`
4. **Execução:** Python executa bytecode normalmente

**Vantagens:**
- ✅ Protege lógica de negócio
- ✅ Dificulta engenharia reversa
- ✅ Funciona sem dependências extras
- ✅ Compatível com pip/virtualenv

**Limitações:**
- ⚠️ Não é criptografia (bytecode pode ser descompilado com ferramentas avançadas)
- ⚠️ Performance idêntica ao código normal
- ⚠️ Debug mais difícil para usuários finais

---

## Build Ofuscado

### Método 1: Build Automático (setup.py)

O setup.py já está configurado para ofuscar automaticamente durante o build.

```powershell
# 1. Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# 2. Fazer build (ofusca automaticamente)
python setup.py build

# 3. Criar distribuição
python setup.py sdist bdist_wheel

# Build fica em:
# dist/SQLManager-4.2.2.tar.gz         (código ofuscado)
# dist/SQLManager-4.2.2-py3-none-any.whl
```

**Variável de controle:**
```powershell
# Desabilitar ofuscação temporariamente
$env:OBFUSCATE_BUILD = "0"
python setup.py build

# Reabilitar (padrão)
$env:OBFUSCATE_BUILD = "1"
```

### Método 2: Script Standalone

Use o script `build_obfuscated.py` para mais controle:

```powershell
# Executar build ofuscado
python build_obfuscated.py

# Resultado:
# dist/SQLManager/  ← Código ofuscado
# dist/setup.py
# dist/README.md
```

**Estrutura do build:**
```
dist/
├── SQLManager/
│   ├── __init__.py          (mantido legível - imports)
│   ├── CoreConfig.pyc       (bytecode ofuscado)
│   ├── CoreConfig.py        (wrapper minificado)
│   ├── connection/
│   │   ├── database_connection.pyc
│   │   └── database_connection.py
│   └── controller/
│       ├── TableController.pyc
│       └── TableController.py
├── setup.py
└── README.md
```

---

## Teste Local

Antes de publicar, teste o pacote ofuscado localmente:

```powershell
# 1. Criar ambiente de teste limpo
python -m venv .venv_test
.\.venv_test\Scripts\Activate.ps1

# 2. Instalar build ofuscado
cd dist
pip install -e .

# 3. Testar importação
python -c "from SQLManager import CoreConfig; print('✅ Importação OK')"

# 4. Testar funcionalidade básica
python
```

```python
from SQLManager import CoreConfig
from SQLManager.connection import database_connection

# Configurar (use .env de teste)
CoreConfig.configure()

# Testar conexão
db = database_connection()
db.connect()
print("✅ Conexão OK")

# Testar query
results = db.doQuery("SELECT 1 as test")
print(f"✅ Query OK: {results}")

db.disconnect()
```

**Verificar se está ofuscado:**

```powershell
# Abrir um arquivo .py qualquer (exceto __init__.py)
cat dist\SQLManager\CoreConfig.py

# Deve mostrar apenas:
# # SQLManager - Código Ofuscado
# # Avalon Tecnologia © 2026
# exec(__import__('importlib.util').util...)
```

---

## Publicação no GitHub

### Pré-requisitos

1. **SSH configurada** (veja README.md)
2. **Repositório privado** (Avalon-Tecnologia/SQLManager)
3. **Build testado** localmente

### Workflow Completo

```powershell
# 1. Garantir que está na branch main
git checkout main
git pull origin main

# 2. Fazer build ofuscado
python setup.py build
python setup.py sdist bdist_wheel

# 3. Commitar código fonte (NÃO o build)
git add SQLManager/ setup.py README.md
git commit -m "v4.2.2 - Atualização com ofuscação automática"

# 4. Tag da versão
git tag v4.2.2
git push origin main --tags

# 5. Usuários instalam diretamente via SSH
# pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git
```

**Importante:**
- ✅ **Commite:** Código fonte original em `SQLManager/`
- ❌ **Não commite:** Pasta `dist/`, `build/`, `.eggs/`
- 📦 **Build acontece:** No `pip install` do usuário (setup.py faz ofuscação)

### Como Funciona na Instalação

Quando o usuário executa:
```bash
pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git
```

**O pip faz:**
1. Clona o repositório
2. Executa `python setup.py build` (ofusca código)
3. Instala no `.venv` do usuário (código ofuscado)
4. Executa `CustomInstallCommand` (gera modelos)

**O usuário recebe:**
- Código ofuscado em `.venv/Lib/site-packages/SQLManager/`
- Documentação completa (README.md)
- Funcionalidade 100% preservada

---

## Desabilitação Temporária

Para desenvolvedores autorizados que precisam do código legível:

### Opção 1: Desabilitar via Variável

```powershell
# Durante desenvolvimento
$env:OBFUSCATE_BUILD = "0"
pip install -e .

# Reinstalar sem ofuscação (modo editable)
pip install --force-reinstall --no-deps -e .
```

### Opção 2: Branch Separada

```powershell
# Criar branch de desenvolvimento
git checkout -b dev-readable

# Editar setup.py
# Comentar linha: 'build_py': ObfuscatedBuildCommand

# Desenvolver normalmente
# NÃO fazer merge desta branch no main!
```

### Opção 3: Clone Direto (Apenas Desenvolvedores)

```powershell
# Clonar repositório
git clone git@github.com:Avalon-Tecnologia/SQLManager.git
cd SQLManager

# Usar diretamente (sem instalar)
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python seu_projeto.py
```

---

## Controle de Acesso

### Gerenciar Permissões (GitHub)

```
Repositório → Settings → Manage Access

✅ Desenvolvedores: Write (podem ver código-fonte)
✅ Clientes: Read (instalam via pip, recebem ofuscado)
❌ Público: Sem acesso (repositório privado)
```

### Auditoria de Instalações

```powershell
# Adicionar logging no setup.py (opcional)
class CustomInstallCommand(install):
    def run(self):
        import socket
        import datetime
        log_msg = f"{datetime.datetime.now()} - {socket.gethostname()}"
        # Enviar para analytics/logging interno
        install.run(self)
```

---

## Checklist de Release

- [ ] Código testado e funcionando
- [ ] Versão atualizada em `setup.py`
- [ ] README.md atualizado
- [ ] Build local testado (`python setup.py build`)
- [ ] Ofuscação verificada (`cat build/lib/SQLManager/CoreConfig.py`)
- [ ] Testes passando
- [ ] Git commit + tag (`git tag v4.2.2`)
- [ ] Push para main (`git push origin main --tags`)
- [ ] Testar instalação via SSH em ambiente limpo
- [ ] Documentar breaking changes (se houver)

---

## Troubleshooting

### Build não ofusca

**Sintoma:** Código legível em `build/lib/`

**Solução:**
```powershell
# Verificar variável
echo $env:OBFUSCATE_BUILD  # Deve ser "1" ou vazio

# Forçar rebuild
rm -r build/ dist/
python setup.py build
```

### ImportError após ofuscação

**Sintoma:** `ModuleNotFoundError: No module named 'SQLManager.xxx'`

**Solução:**
```powershell
# Verificar __init__.py não foi ofuscado
cat build/lib/SQLManager/__init__.py
# Deve estar legível

# Se estiver ofuscado, corrigir build_obfuscated.py:
# Linha 57: if file.endswith('.py') and file != '__init__.py':
```

### Performance degradada

**Sintoma:** Código mais lento após ofuscação

**Diagnóstico:**
```python
import timeit

# Testar função
timeit.timeit('CoreConfig.configure()', setup='from SQLManager import CoreConfig', number=1000)
```

**Nota:** Bytecode Python tem performance **idêntica** ao código normal. Se houver diferença, o problema é outro.

---

## Recursos Adicionais

- [Python Bytecode - Docs Oficiais](https://docs.python.org/3/library/py_compile.html)
- [GitHub SSH - Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [pip install from Git](https://pip.pypa.io/en/stable/topics/vcs-support/)

---

**Dúvidas?** Entre em contato: nicolas.santos@avalontecnologia.com.br
