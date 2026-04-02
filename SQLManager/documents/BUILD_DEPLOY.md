# Guia de Build e Deploy - SQLManager

Este documento descreve como preparar e distribuir o SQLManager com código ofuscado para proteger a propriedade intelectual.

## Índice

1. [Visão Geral](#visão-geral)
2. [Desenvolvimento Local](#desenvolvimento-local)
3. [Build Ofuscado](#build-ofuscado)
4. [Teste Local](#teste-local)
5. [Publicação e Distribuição](#publicação-e-distribuição)
6. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O SQLManager utiliza **ofuscação de bytecode** para proteger o código-fonte durante a distribuição. O processo funciona assim:

1. **Desenvolvimento:** Código normal em `SQLManager/`
2. **Build:** Script compila `.py` -> `.pyc` (bytecode) e remove comentários
3. **Distribuição:** Usuários instalam wheel ofuscado via `pip install`
4. **Execução:** Python executa bytecode normalmente

**Vantagens:**
- Protege lógica de negócio
- Dificulta engenharia reversa
- Funciona sem dependências extras
- Compatível com pip/virtualenv

**Limitações:**
- Não é criptografia (bytecode pode ser descompilado com ferramentas avançadas)
- Performance idêntica ao código normal
- Debug mais difícil para usuários finais

---

## Desenvolvimento Local

Para desenvolver e testar mudanças:

```bash
# Modo editable - código aberto, mudanças refletidas imediatamente
pip install -e .
```

Isso instala em modo "editable" - qualquer mudança no código é refletida imediatamente sem reinstalar.

**Importante:** Modo editable NÃO ofusca o código (aponta diretamente para fonte original).

---

## Build Ofuscado

### Criar Wheel Ofuscado

Use o script `build_wheel_obfuscated.py`:

```bash
python build_wheel_obfuscated.py
```

**O que o script faz:**
1. Limpa builds anteriores (`dist/`, `build/`)
2. Cria wheel normal usando `pip wheel`
3. Extrai o wheel
4. Ofusca código (remove comentários + compila bytecode)
5. Reempacota wheel ofuscado

**Saída:**
```
dist/sqlmanager-4.2.2-py3-none-any.whl  (ofuscado)
```

### Estrutura do Wheel Ofuscado

```
sqlmanager-4.2.2-py3-none-any.whl
├── SQLManager/
│   ├── __init__.py          (funcional)
│   ├── CoreConfig.py        (sem comentários)
│   ├── CoreConfig.pyc       (bytecode otimizado)
│   ├── connection/
│   │   ├── database_connection.py
│   │   └── database_connection.pyc
│   └── controller/
│       ├── TableController.py
│       └── TableController.pyc
└── SQLManager-4.2.2.dist-info/
```

---

## Teste Local

Antes de distribuir, teste o wheel ofuscado:

```bash
# 1. Criar ambiente limpo
python -m venv .venv_test
.\.venv_test\Scripts\Activate.ps1  # Windows
# source .venv_test/bin/activate   # Linux/Mac

# 2. Instalar wheel ofuscado
pip install dist/sqlmanager-4.2.2-py3-none-any.whl

# 3. Testar importação
python -c "from SQLManager import CoreConfig, AutoRouter; print('[OK] Importacao funcionando')"

# 4. Verificar ofuscação
python -c "import SQLManager; import os; f=os.path.join(os.path.dirname(SQLManager.__file__), 'CoreConfig.py'); print(open(f).readline())"
# Deve mostrar: # SQLManager - Codigo Ofuscado v4.2.2
```

### Teste Funcional Completo

```python
from SQLManager import CoreConfig
from SQLManager.connection import database_connection

# Configurar (use .env de teste)
CoreConfig.configure()

# Testar conexão
db = database_connection()
db.connect()
print("[OK] Conexao OK")

# Testar query
results = db.doQuery("SELECT 1 as test")
print(f"[OK] Query OK: {results}")

db.disconnect()
```

---

## Publicação e Distribuição

### Opção 1: GitHub Release (Recomendado)

```bash
# 1. Criar wheel ofuscado
python build_wheel_obfuscated.py

# 2. Adicionar ao Git
git add dist/sqlmanager-4.2.2-py3-none-any.whl
git commit -m "Release v4.2.2 - Build ofuscado"

# 3. Tag de versão
git tag v4.2.2
git push origin main --tags

# 4. Criar GitHub Release (manual na interface)
# - Fazer upload do .whl em Assets
```

**Usuários instalam:**
```bash
# Via URL direta do release
pip install https://github.com/Avalon-Tecnologia/SQLManager/releases/download/v4.2.2/sqlmanager-4.2.2-py3-none-any.whl

# Ou baixar e instalar localmente
pip install sqlmanager-4.2.2-py3-none-any.whl
```

### Opção 2: PyPI (Público ou Privado)

```bash
# Instalar twine
pip install twine

# Upload para PyPI
twine upload dist/sqlmanager-4.2.2-py3-none-any.whl

# Usuários instalam
pip install SQLManager
```

### Opção 3: Servidor Privado/Compartilhado

```bash
# Copiar wheel para servidor interno
scp dist/sqlmanager-4.2.2-py3-none-any.whl user@servidor:/shared/packages/

# Usuários instalam
pip install /shared/packages/sqlmanager-4.2.2-py3-none-any.whl
```

---

## Workflow Completo de Release

```bash
# 1. Desenvolver com código aberto
pip install -e .

# 2. Testar mudanças
python -m pytest
python test_manual.py

# 3. Atualizar versão
# - Editar version="4.2.2" em setup.py
# - Atualizar CHANGELOG.md

# 4. Criar wheel ofuscado
python build_wheel_obfuscated.py

# 5. Testar wheel em ambiente limpo
python -m venv .venv_test
.\.venv_test\Scripts\Activate.ps1
pip install dist/sqlmanager-4.2.2-py3-none-any.whl
python -c "from SQLManager import AutoRouter; print('[OK] Funcionando')"
deactivate

# 6. Commit e tag
git add dist/sqlmanager-4.2.2-py3-none-any.whl setup.py CHANGELOG.md
git commit -m "Release v4.2.2"
git tag v4.2.2
git push origin main --tags

# 7. Criar GitHub Release com o .whl
```

---

## Troubleshooting

### Build não gera wheel ofuscado

**Sintoma:** `dist/` vazio ou wheel sem ofuscação

**Solução:**
```bash
# Limpar totalmente
Remove-Item dist, build -Recurse -Force -ErrorAction SilentlyContinue

# Refazer build
python build_wheel_obfuscated.py
```

### ImportError após instalar wheel

**Sintoma:** `ModuleNotFoundError: No module named 'SQLManager.xxx'`

**Solução:**
```bash
# Verificar estrutura do wheel
unzip -l dist/sqlmanager-4.2.2-py3-none-any.whl | grep SQLManager

# Deve mostrar SQLManager/__init__.py, CoreConfig.py, etc.
```

### Código não está ofuscado

**Sintoma:** Arquivos .py com comentários completos

**Solução:**
```bash
# Verificar primeira linha do arquivo instalado
python -c "import SQLManager; print(open(SQLManager.__file__).readline())"

# Deve mostrar: # SQLManager - Codigo Ofuscado v4.2.2
```

### Performance degradada

**Nota:** Bytecode Python tem performance **idêntica** ao código fonte normal. Se houver diferença, verifique outros fatores (cache, network, etc).

---

## Controle de Acesso

### Repositório GitHub (Privado)

```
Settings -> Manage Access:

- Desenvolvedores Avalon: Admin (acesso a código-fonte)
- Parceiros: Read (baixam releases, recebem .whl ofuscado)
- Público: Sem acesso
```

### Acesso ao Código Fonte

Apenas para desenvolvedores autorizados:

```bash
# Clone com acesso SSH
git clone git@github.com:Avalon-Tecnologia/SQLManager.git
cd SQLManager

# Desenvolver diretamente (sem instalar)
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python seu_projeto.py
```

---

## Checklist de Release

- [ ] Código testado e funcionando
- [ ] Versão atualizada em `setup.py`
- [ ] CHANGELOG.md atualizado
- [ ] Build ofuscado criado (`python build_wheel_obfuscated.py`)
- [ ] Ofuscação verificada (primeira linha com header)
- [ ] Teste em ambiente limpo (venv separado)
- [ ] Testes automatizados passando
- [ ] Git commit + tag (`git tag v4.2.2`)
- [ ] Push para GitHub (`git push origin main --tags`)
- [ ] GitHub Release criado com .whl em Assets
- [ ] Documentar breaking changes (se houver)

---

## Recursos Adicionais

- [Python Bytecode - Docs Oficiais](https://docs.python.org/3/library/py_compile.html)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [pip wheel](https://pip.pypa.io/en/stable/cli/pip_wheel/)

---

**Dúvidas?** Entre em contato: nicolas.santos@avalontecnologia.com.br
