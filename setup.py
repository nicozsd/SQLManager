from pathlib import Path

from setuptools import setup, find_packages, Extension

try:
    from Cython.Build import cythonize
except ImportError as exc:
    raise RuntimeError("Cython is required to build SQLManager") from exc

PACKAGE_NAME = "SQLManager"
BASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = BASE_DIR / PACKAGE_NAME


def discover_extensions(package_dir: Path):
    extensions = []
    for path in package_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        if "tests" in path.parts:
            continue
        module_name = ".".join(path.relative_to(BASE_DIR).with_suffix("").parts)
        extensions.append(Extension(module_name, [str(path)]))
    return extensions


ext_modules = cythonize(
    discover_extensions(PACKAGE_DIR),
    compiler_directives={
        "language_level": "3",
        "binding": True,
        "annotation_typing": False
    },
    annotate=False,
)


setup(
    name="SQLManager",
    version="4.2.2",
    description="Sistema para gerenciamento de banco de dados e validações",
    author="Avalon Tecnologia",
    author_email="nicolas.santos@avalontecnologia.com.br",
    url="https://github.com/Avalon-Tecnologia/SQLManager",
    packages=find_packages(include=[PACKAGE_NAME, f"{PACKAGE_NAME}.*"]),
    include_package_data=True,
    package_data={
        PACKAGE_NAME: [
            "_model/*.py",
            "EDTs/*.py",
            "enum/*.py",
            "tables/*.py",
            "views/*.py",
        ]
    },
    python_requires=">=3.8",
    install_requires=[
        "pyodbc>=4.0.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        'websocket': ['flask-socketio>=5.0.0'],
    },
    ext_modules=ext_modules,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    license="MIT",
)
