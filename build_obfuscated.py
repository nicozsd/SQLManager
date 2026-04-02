"""
Script para ofuscação do código SQLManager antes da distribuição.
Criado para proteger a propriedade intelectual do código.
"""

import os
import py_compile
import shutil
import sys
from pathlib import Path

def obfuscate_directory(source_dir, target_dir):
    """
    Compila todos os arquivos .py para .pyc (bytecode) e remove o código fonte.
    """
    print(f"🔒 Ofuscando {source_dir}...")
    
    # Criar diretório de destino
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    # Percorrer todos os arquivos
    for root, dirs, files in os.walk(source_dir):
        # Ignorar __pycache__ e outros diretórios desnecessários
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.venv', 'tests', 'documents']]
        
        # Calcular caminho relativo
        rel_path = os.path.relpath(root, source_dir)
        target_path = os.path.join(target_dir, rel_path) if rel_path != '.' else target_dir
        
        # Criar diretório no destino
        Path(target_path).mkdir(parents=True, exist_ok=True)
        
        for file in files:
            source_file = os.path.join(root, file)
            
            if file.endswith('.py'):
                # Compilar para bytecode
                target_file = os.path.join(target_path, file.replace('.py', '.pyc'))
                try:
                    py_compile.compile(source_file, cfile=target_file, doraise=True)
                    print(f"  ✓ {file} -> {os.path.basename(target_file)}")
                except Exception as e:
                    print(f"  ✗ Erro ao compilar {file}: {e}")
                    # Em caso de erro, copiar o original
                    shutil.copy2(source_file, os.path.join(target_path, file))
            
            elif file in ['__init__.py', 'py.typed', 'LICENSE', 'README.md']:
                # Copiar arquivos essenciais sem modificação
                shutil.copy2(source_file, os.path.join(target_path, file))
                print(f"  → {file} (copiado)")

def create_minimal_py_files(target_dir):
    """
    Cria arquivos .py mínimos que importam os .pyc correspondentes.
    Necessário para que o Python encontre os módulos.
    """
    print("\n📝 Criando wrappers mínimos...")
    
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.pyc') and not file.startswith('__init__'):
                pyc_path = os.path.join(root, file)
                py_name = file.replace('.pyc', '.py')
                py_path = os.path.join(root, py_name)
                
                # Criar um .py que simplesmente importa o bytecode
                module_name = py_name.replace('.py', '')
                with open(py_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Ofuscado - SQLManager v4.2.2\n")
                    f.write(f"# Propriedade da Avalon Tecnologia\n")
                    f.write(f"exec(compile(open(__file__.replace('.py', '.pyc'), 'rb').read()[16:], __file__, 'exec'))\n")
                
                print(f"  ✓ Wrapper criado: {py_name}")

def update_init_files(target_dir):
    """
    Mantém arquivos __init__.py legíveis mas remove implementação sensível.
    """
    print("\n🔧 Atualizando arquivos __init__.py...")
    
    for root, dirs, files in os.walk(target_dir):
        if '__init__.py' in files:
            init_path = os.path.join(root, '__init__.py')
            
            # Ler o conteúdo original
            with open(init_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Manter apenas imports, remover implementações
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Manter imports e definições de __all__
                if (line.strip().startswith('from ') or 
                    line.strip().startswith('import ') or 
                    line.strip().startswith('__all__') or
                    line.strip() == '' or
                    line.strip().startswith('#')):
                    cleaned_lines.append(line)
            
            # Escrever versão limpa
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned_lines))
            
            print(f"  ✓ {os.path.relpath(init_path, target_dir)}")

def main():
    # Definir diretórios
    base_dir = Path(__file__).parent
    source_dir = base_dir / 'SQLManager'
    target_dir = base_dir / 'dist' / 'SQLManager'
    
    # Limpar diretório de destino se existir
    if target_dir.exists():
        print("🗑️  Limpando build anterior...")
        shutil.rmtree(target_dir.parent)
    
    print("=" * 60)
    print("🔐 SQLManager - Build Ofuscado")
    print("=" * 60)
    print()
    
    # Ofuscar código
    obfuscate_directory(str(source_dir), str(target_dir))
    
    # Criar wrappers
    create_minimal_py_files(str(target_dir))
    
    # Atualizar __init__.py
    update_init_files(str(target_dir))
    
    # Copiar setup.py e README
    print("\n📋 Copiando arquivos de distribuição...")
    shutil.copy2(base_dir / 'setup.py', base_dir / 'dist' / 'setup.py')
    shutil.copy2(base_dir / 'README.md', base_dir / 'dist' / 'README.md')
    
    print()
    print("=" * 60)
    print("✅ Build concluído com sucesso!")
    print(f"📦 Pacote ofuscado em: {target_dir.parent}")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print("1. Testar o pacote: cd dist && pip install -e .")
    print("2. Fazer commit: git add dist/ && git commit -m 'Build ofuscado'")
    print("3. Fazer push: git push origin main")

if __name__ == '__main__':
    main()
