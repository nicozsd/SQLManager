from pathlib import Path
import os

from setuptools import setup, find_packages, Extension

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
    packages=find_packages(
        include=[PACKAGE_NAME, f"{PACKAGE_NAME}.*"],
        exclude=[f"{PACKAGE_NAME}.tests", f"{PACKAGE_NAME}.tests.*"],
    ),
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