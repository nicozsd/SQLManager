"""
Script para preparar o pacote ofuscado do SQLManager via PyArmor.

Uso:
    python build_wheel_obfuscated.py

Gera: dist/obfuscated_package/ (código fonte ofuscado pronto para pip install)
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
    obfuscated_dir = dist_dir / 'obfuscated_package'
    
    print("="*60)
    print("SQLManager - Build Ofuscado com PyArmor")
    print("="*60)
    print()
    
    # 1. Limpar builds anteriores
    print("[1/3] Limpando builds anteriores...")
    for dir_to_clean in [dist_dir, build_dir, base_dir / 'SQLManager.egg-info']:
        if dir_to_clean.exists():
            shutil.rmtree(dir_to_clean)
    
    # 2. Ofuscar com PyArmor
    print("\n[2/3] Ofuscando código fonte com PyArmor...")
    
    pyarmor_path = shutil.which("pyarmor")
    if not pyarmor_path:
        print("[ERRO] Comando 'pyarmor' não encontrado no PATH.")
        print("[DICA] Instale a biblioteca com: pip install pyarmor")
        return 1

    # pyarmor gen -O <saida> -r <entrada>
    pyarmor_cmd = [
        pyarmor_path, "gen", 
        "-O", str(obfuscated_dir / "SQLManager"), 
        "-r", 
        "SQLManager"
    ]
    
    result = subprocess.run(pyarmor_cmd, cwd=base_dir, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERRO] Falha ao ofuscar com PyArmor:")
        print(result.stderr or result.stdout)
        return 1
        
    print("  [OK] Código ofuscado com sucesso via PyArmor!")
    
    # 3. Preparar diretório para instalação
    print("\n[3/3] Preparando pacote para instalação...")
    
    obfuscated_dir.mkdir(parents=True, exist_ok=True)
    
    # Copia arquivos essenciais para a pasta gerada, para que o pip install funcione nela
    files_to_copy = ['setup.py', 'README.md', 'requirements.txt.example']
    for file_name in files_to_copy:
        src_file = base_dir / file_name
        if src_file.exists():
            shutil.copy2(src_file, obfuscated_dir / file_name)
            
    print("  [OK] Arquivos de configuração copiados.")
    
    # 4. Automático: Chamar o pip install do pacote recém-ofuscado
    print("\n[4/4] Instalando pacote ofuscado localmente (pip install)...")
    pip_install_cmd = [sys.executable, "-m", "pip", "install", ".", "--force-reinstall"]
    
    install_result = subprocess.run(pip_install_cmd, cwd=obfuscated_dir, capture_output=True, text=True)
    if install_result.returncode == 0:
        print("  [OK] Instalação concluída com sucesso no seu ambiente!")
    else:
        print("  [AVISO] Erro ao instalar via pip:")
        print(install_result.stderr)

    print()
    print("="*60)
    print(f"[SUCESSO] Pacote ofuscado criado com sucesso!")
    print(f"Diretório pronto: {obfuscated_dir}")
    print("="*60)
    print()
    print("COMO DISTRIBUIR PARA SEUS CLIENTES DE FORMA SEGURA:")
    print("1. No terminal, entre na pasta gerada:  cd dist/obfuscated_package")
    print("2. Inicie o git e suba para uma branch separada chamada 'release':")
    print("   git init && git add . && git commit -m 'Deploy ofuscado'")
    print("   git push -f git@github.com:Avalon-Tecnologia/SQLManager.git HEAD:release")
    print("\n3. O cliente vai instalar baixando direto dessa branch ofuscada:")
    print("   pip install git+ssh://git@github.com/Avalon-Tecnologia/SQLManager.git@release")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
