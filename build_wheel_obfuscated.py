"""
Script para criar wheel ofuscado do SQLManager para distribuição.

Uso:
    python build_wheel_obfuscated.py

Gera: dist/sqlmanager-4.2.2-py3-none-any.whl (ofuscado)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    # Diretórios
    base_dir = Path(__file__).parent
    dist_dir = base_dir / 'dist'
    build_dir = base_dir / 'build'
    
    # Verifica variável de ambiente para desabilitar ofuscação
    skip_obfuscate = os.getenv('OBFUSCATE_BUILD', '1') == '0'
    
    print("="*60)
    print("SQLManager - Build Wheel" + (" (SEM ofuscação)" if skip_obfuscate else " Ofuscado"))
    print("="*60)
    print()
    
    # 1. Limpar builds anteriores
    print("[1/3] Limpando builds anteriores...")
    for dir_to_clean in [dist_dir, build_dir, base_dir / 'SQLManager.egg-info']:
        if dir_to_clean.exists():
            shutil.rmtree(dir_to_clean)
    
    # 2. Criar wheel
    print("\n[2/3] Criando wheel...")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        cwd=base_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"[ERRO] Erro ao criar wheel:")
        print(result.stderr)
        print("\n[DICA] Instale build: pip install build")
        return 1
    
    # 3. Encontrar o wheel gerado
    print("\n[3/3] Localizando wheel gerado...")
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        print("[ERRO] Nenhum wheel encontrado em dist/")
        return 1
    
    wheel_file = wheels[0]
    print(f"[OK] Encontrado: {wheel_file.name}")
    
    # 4. Ofuscação (OPCIONAL - desabilitado por padrão)
    if not skip_obfuscate:
        print("\n[EXTRA] Ofuscando wheel...")
        try:
            import zipfile
            extract_dir = build_dir / "wheel_extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(wheel_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            sqlmanager_dir = extract_dir / "SQLManager"
            if sqlmanager_dir.exists():
                count = ofuscate_directory(sqlmanager_dir)
                print(f"  [OK] {count} arquivos ofuscados")
            
            wheel_file.unlink()
            
            with zipfile.ZipFile(wheel_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(extract_dir)
                        zip_ref.write(file_path, arcname)
        except Exception as e:
            print(f"  [AVISO] Erro na ofuscação: {e}")
            print("  Criando wheel SEM ofuscação...")
    
    print()
    print("="*60)
    print(f"[SUCESSO] Wheel criado com sucesso!")
    print(f"Arquivo: {wheel_file}")
    print("="*60)
    print()
    print("Para instalar:")
    print(f"  pip install {wheel_file}")
    print("  OU")
    print(f"  pip install git+https://github.com/nicozsd/SQLManager.git")
    print()
    
    return 0

def ofuscate_directory(directory: Path) -> int:
    """
    Ofusca todos os arquivos .py no diretório.
    Retorna número de arquivos processados.
    """
    count = 0
    import py_compile
    
    for root, dirs, files in os.walk(directory):
        # Ignorar __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                
                try:
                    # Remove comentários
                    content = remove_comments_safe(file_path)
                    
                    # Escreve versão ofuscada
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Compila para bytecode otimizado
                    py_compile.compile(str(file_path), optimize=2, doraise=True)
                    
                    count += 1
                    
                except Exception as e:
                    print(f"  [AVISO] Erro em {file}: {e}")
    
    return count

def remove_comments_safe(filepath: Path) -> str:
    """Remove apenas linhas de comentário completas (começam com #)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    result = []
    for line in lines:
        stripped = line.lstrip()
        # Remove apenas linhas que são 100% comentário
        if stripped.startswith('#') and not stripped.startswith('#!'):
            continue
        result.append(line)
    
    # Header
    header = "# SQLManager - Codigo Ofuscado v4.2.2\n# Avalon Tecnologia (C) 2026\n\n"
    return header + ''.join(result)

if __name__ == '__main__':
    sys.exit(main())
