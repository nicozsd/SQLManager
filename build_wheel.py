"""
SQLManager Build System - Compilação e Ofuscação com Cython

Este script:
1. Gera arquivos .c a partir dos .py usando Cython
2. Compila para .pyd (Windows) ou .so (Linux)
3. Remove os arquivos .py originais do pacote
4. Empacota apenas os arquivos compilados no wheel

Uso:
    python build_wheel.py [--keep-py] [--clean]

Opções:
    --keep-py  : Mantém os arquivos .py originais (para debug)
    --clean    : Limpa build/dist antes de compilar
"""
import shutil
import subprocess
import sys
import os
from pathlib import Path


def get_package_dir():
    """Retorna o diretório do pacote SQLManager"""
    return Path(__file__).parent / "SQLManager"


def remove_py_files(package_dir: Path):
    """
    Remove todos os arquivos .py do pacote após compilação.
    Mantém apenas __init__.py e arquivos de teste.
    """
    removed = []
    kept = []

    for py_file in package_dir.rglob("*.py"):
        # Mantém __init__.py e testes
        if py_file.name == "__init__.py":
            kept.append(str(py_file))
            continue
        if "tests" in py_file.parts:
            kept.append(str(py_file))
            continue

        py_file.unlink()
        removed.append(str(py_file))

    print(f"\n[REMOVE] {len(removed)} arquivos .py removidos:")
    for f in removed[:20]:  # Mostra apenas primeiros 20
        print(f"  - {Path(f).relative_to(package_dir.parent)}")
    if len(removed) > 20:
        print(f"  ... e mais {len(removed) - 20} arquivos")

    print(f"[KEEP] {len(kept)} arquivos mantidos (__init__.py e testes)")
    return removed


def remove_generated_c_files(package_dir: Path):
    """Remove arquivos .c gerados pelo Cython (opcional, para manter repo limpo)"""
    removed = []
    for c_file in package_dir.rglob("*.c"):
        # Mantém apenas .c que estão no git (versionados)
        c_file.unlink()
        removed.append(str(c_file))

    if removed:
        print(f"\n[CLEAN] {len(removed)} arquivos .c removidos")
    return removed


def clean_build_dirs(base_dir: Path):
    """Limpa diretórios de build e dist"""
    for d in [base_dir / "dist", base_dir / "build"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"[CLEAN] {d} removido")


def build_wheel(base_dir: Path, keep_py: bool = False):
    """Constroi o wheel com os arquivos compilados"""
    print("\n" + "=" * 60)
    print("[BUILD] Gerando wheel com Cython...")
    print("=" * 60)

    subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        check=True,
        cwd=base_dir
    )

    dist_dir = base_dir / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    if wheels:
        print(f"\n[WHEEL] Criado: {wheels[0].name}")
        print(f"       Tamanho: {wheels[0].stat().st_size / 1024:.1f} KB")


def main():
    base_dir = Path(__file__).parent
    package_dir = get_package_dir()

    keep_py = "--keep-py" in sys.argv
    do_clean = "--clean" in sys.argv or True  # Default limpa

    print("=" * 60)
    print("SQLManager Build System - Cython Obfuscation")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Package: {package_dir}")
    print(f"Keep .py files: {keep_py}")
    print("-" * 60)

    # Limpa build anterior
    if do_clean:
        clean_build_dirs(base_dir)

    # Step 1: Compilar com Cython (gera .c e compila para .pyd/.so)
    print("\n[STEP 1] Compilando extensões Cython...")
    subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        check=True,
        cwd=base_dir
    )

    # Step 2: Verificar arquivos compilados
    compiled = list(package_dir.rglob("*.pyd")) + list(package_dir.rglob("*.so"))
    print(f"\n[COMPILED] {len(compiled)} arquivos compilados encontrados:")
    for f in compiled[:15]:
        print(f"  + {f.relative_to(package_dir.parent)}")
    if len(compiled) > 15:
        print(f"  ... e mais {len(compiled) - 15} arquivos")

    if not keep_py:
        # Step 3: Remover arquivos .py originais
        remove_py_files(package_dir)

    # Step 4: Build do wheel
    build_wheel(base_dir, keep_py)

    print("\n" + "=" * 60)
    print("[SUCCESS] Build concluído!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("  1. Verifique o wheel em: dist/*.whl")
    print("  2. Teste: pip install dist/SQLManager-*.whl")
    if not keep_py:
        print("  3. Commit: git add SQLManager/ (remove .py, adiciona .pyd/.so)")
        print("  4. git commit -m 'Ofuscação: remove .py e adiciona compilados'")


if __name__ == "__main__":
    sys.exit(main())