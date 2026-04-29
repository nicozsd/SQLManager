from pathlib import Path
import os

from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
except ImportError as exc:
    raise RuntimeError("Cython is required to build SQLManager") from exc

PACKAGE_NAME = "SQLManager"
BASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = BASE_DIR / PACKAGE_NAME


def discover_extensions(package_dir: Path):
    """Descobre todos os arquivos .py para compilar com Cython (exclui testes e __init__.py)"""
    extensions = []

    for path in package_dir.rglob("*.py"):
        relative_path = path.relative_to(BASE_DIR)

        # Pula __init__.py e arquivos de teste
        if path.name == "__init__.py":
            continue

        if "tests" in relative_path.parts:
            continue

        module_name = ".".join(relative_path.with_suffix("").parts)
        source_path = relative_path.as_posix()

        extensions.append(
            Extension(
                module_name,
                [source_path],
            )
        )

    return extensions


def get_compiled_package_data(package_dir: Path):
    """
    Retorna dicionário de package_data para arquivos compilados (.pyd/.so).
    Inclui também .pyi stub files se existirem.
    """
    package_data = {}

    for path in package_dir.rglob("*"):
        if path.is_file() and path.suffix in (".pyd", ".so", ".pyi"):
            rel_path = path.relative_to(package_dir)
            package_name = ".".join(rel_path.parts[:-1]) if rel_path.parent != Path(".") else PACKAGE_NAME
            if package_name not in package_data:
                package_data[package_name] = []
            package_data[package_name].append(str(rel_path.name))

    return package_data


def get_package_modules(package_dir: Path, base_dir: Path):
    """
    Retorna lista de módulos do pacote baseados nos arquivos compilados (.pyd/.so).
    Isso substitui find_packages() para evitar incluir .py não compilados.
    """
    modules = set()
    modules.add(PACKAGE_NAME)  # Sempre inclui o pacote principal

    for path in package_dir.rglob("*.pyd"):
        rel_path = path.relative_to(package_dir)
        # Converte caminho do arquivo compilado para nome do módulo
        module_parts = list(rel_path.parts[:-1])  # Remove .pyd
        if module_parts:
            modules.add(f"{PACKAGE_NAME}.{'.'.join(module_parts)}")

    for path in package_dir.rglob("*.so"):
        rel_path = path.relative_to(package_dir)
        module_parts = list(rel_path.parts[:-1])  # Remove .so
        if module_parts:
            modules.add(f"{PACKAGE_NAME}.{'.'.join(module_parts)}")

    # Também descobre subpacotes por diretórios com __init__.py
    for init_py in package_dir.rglob("__init__.py"):
        rel_path = init_py.relative_to(package_dir).parent
        if rel_path != Path("."):
            module_parts = list(rel_path.parts)
            modules.add(f"{PACKAGE_NAME}.{'.'.join(module_parts)}")

    return sorted(modules)


ext_modules = cythonize(
    discover_extensions(PACKAGE_DIR),
    compiler_directives={
        "language_level": "3",
        "binding": True,
        "annotation_typing": False,
    },
    annotate=False,
)


setup(
    name="SQLManager",
    version="4.2.3",
    description="Sistema para gerenciamento de banco de dados e validações",
    author="Avalon Tecnologia",
    author_email="nicolas.santos@avalontecnologia.com.br",
    url="https://github.com/Avalon-Tecnologia/SQLManager",
    packages=get_package_modules(PACKAGE_DIR, BASE_DIR),
    include_package_data=True,
    package_data=get_compiled_package_data(PACKAGE_DIR),
    python_requires=">=3.10",
    install_requires=[
        "pyodbc>=4.0.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "websocket": ["flask-socketio>=5.0.0"],
    },
    ext_modules=ext_modules,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    license="MIT",
)