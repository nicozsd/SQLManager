# Configuração Rápida de SSH para SQLManager

Este guia mostra como configurar acesso SSH ao repositório privado SQLManager.

## Para Usuários Windows

### 1. Abrir PowerShell

```powershell
# Como Administrador ou usuário normal
```

### 2. Verificar se já tem chave SSH

```powershell
ls ~/.ssh/

# Se existir id_ed25519.pub ou id_rsa.pub, você já tem uma chave
# Pule para o passo 4
```

### 3. Gerar Nova Chave SSH

```powershell
# Substituir pelo seu email
ssh-keygen -t ed25519 -C "seu.email@empresa.com"

# Pressione Enter 3 vezes:
# 1. Enter = Salva em C:\Users\SeuNome\.ssh\id_ed25519
# 2. Enter = Sem senha (opcional, pode definir senha)
# 3. Enter = Confirma sem senha
```

**Saída esperada:**
```
Generating public/private ed25519 key pair.
Your identification has been saved in C:\Users\SeuNome/.ssh/id_ed25519
Your public key has been saved in C:\Users\SeuNome/.ssh/id_ed25519.pub
The key fingerprint is:
SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx seu.email@empresa.com
```

### 4. Copiar Chave Pública

```powershell
# Copiar para área de transferência
Get-Content ~\.ssh\id_ed25519.pub | Set-Clipboard

# Ou visualizar e copiar manualmente
cat ~/.ssh/id_ed25519.pub
```

**Exemplo de chave pública:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKqP8+o2V... seu.email@empresa.com
```

### 5. Adicionar no GitHub

1. Acesse: https://github.com/settings/keys
2. Clique em **"New SSH key"**
3. **Title:** `Meu Computador - Trabalho` (nome descritivo)
4. **Key:** Cole a chave copiada
5. Clique em **"Add SSH key"**
6. Confirme sua senha do GitHub se solicitado

### 6. Testar Conexão

```powershell
ssh -T git@github.com
```

**Saída esperada:**
```
Hi SeuUsuario! You've successfully authenticated, but GitHub does not provide shell access.
```

Se aparecer:
```
The authenticity of host 'github.com (140.82.121.3)' can't be established.
ED25519 key fingerprint is SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Digite: `yes` e pressione Enter.

### 7. Instalar SQLManager

```powershell
# Criar ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar via SSH
pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git
```

---

## Para Usuários Linux/Mac

### 1. Abrir Terminal

### 2. Gerar Chave SSH

```bash
ssh-keygen -t ed25519 -C "seu.email@empresa.com"

# Pressione Enter 3 vezes (sem senha)
```

### 3. Copiar Chave Pública

```bash
# Mac
cat ~/.ssh/id_ed25519.pub | pbcopy

# Linux
cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard

# Ou visualizar e copiar manualmente
cat ~/.ssh/id_ed25519.pub
```

### 4. Adicionar no GitHub

Mesmo processo do Windows (passo 5 acima).

### 5. Testar Conexão

```bash
ssh -T git@github.com
# Esperado: Hi SeuUsuario! You've successfully authenticated...
```

### 6. Instalar SQLManager

```bash
# Criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar via SSH
pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git
```

---

## Troubleshooting Comum

### Erro: "Permission denied (publickey)"

**Causa:** GitHub não encontrou sua chave SSH.

**Solução:**
```powershell
# Verificar se a chave existe
cat ~/.ssh/id_ed25519.pub

# Se não existir, gerar nova (passo 3)
ssh-keygen -t ed25519 -C "seu.email@empresa.com"

# Adicionar ao ssh-agent
ssh-add ~/.ssh/id_ed25519

# Adicionar no GitHub novamente
```

### Erro: "Host key verification failed"

**Causa:** Primeira conexão ao GitHub.

**Solução:**
```powershell
# Adicionar GitHub aos hosts conhecidos
ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

# Ou aceitar manualmente:
ssh -T git@github.com
# Digite: yes
```

### Erro: "Repository not found"

**Causa:** Você não tem acesso ao repositório privado.

**Solução:**
- Entre em contato com o administrador
- Verifique se sua conta GitHub foi adicionada ao repositório
- URL correta: `git@github.com:Avalon-Tecnologia/SQLManager.git`

### Erro: "Could not resolve hostname"

**Causa:** Problema de conexão de internet.

**Solução:**
```powershell
# Testar conexão
ping github.com

# Verificar configuração SSH
cat ~/.ssh/config

# Se necessário, criar config:
echo "Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519" > ~/.ssh/config
```

---

## Verificação Final

Antes de encerrar, confirme:

- [ ] Chave SSH gerada: `ls ~/.ssh/id_ed25519*`
- [ ] Chave adicionada no GitHub: https://github.com/settings/keys
- [ ] Teste de conexão passou: `ssh -T git@github.com`
- [ ] Instalação funcionou: `pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git`
- [ ] Importação funciona: `python -c "from SQLManager import CoreConfig; print('OK')"`

---

## Múltiplas Chaves SSH (Avançado)

Se você usa SSH para múltiplas contas GitHub:

### 1. Criar Config SSH

```powershell
# Criar arquivo config
New-Item -ItemType File -Path ~/.ssh/config -Force

# Editar com notepad
notepad ~/.ssh/config
```

### 2. Adicionar Configuração

```
# Conta Pessoal
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_personal

# Conta Trabalho (Avalon)
Host github-avalon
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_avalon
```

### 3. Gerar Chave para Trabalho

```powershell
ssh-keygen -t ed25519 -C "trabalho@empresa.com" -f ~/.ssh/id_ed25519_avalon
```

### 4. Instalar com Host Customizado

```powershell
pip install git+ssh://git@github-avalon/Avalon-Tecnologia/SQLManager.git
```

---

## Segurança

### ✅ Boas Práticas

- Use senha na chave SSH (mais seguro)
- Não compartilhe chave privada (`id_ed25519`)
- Pode compartilhar chave pública (`id_ed25519.pub`)
- Revogue chaves antigas no GitHub
- Use chaves específicas por projeto

### ❌ Evite

- Salvar chave privada na nuvem
- Enviar chave privada por email
- Usar mesma chave em múltiplos computadores
- Commitar chaves no Git

---

**Precisa de ajuda?** nicolas.santos@avalontecnologia.com.br
