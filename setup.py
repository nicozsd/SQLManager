import os
import shutil
import subprocess
from pathlib import Path

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py

PACKAGE_NAME = "SQLManager"
PYARMOR_ENV = "SQLMANAGER_PYARMOR"
BASE_DIR = Path(__file__).resolve().parent


def should_obfuscate() -> bool:
    return os.getenv(PYARMOR_ENV, "1") != "0"


def run_pyarmor(build_lib_path: Path) -> None:
    obf_dir = BASE_DIR / "build" / "obf"
    if obf_dir.exists():
        shutil.rmtree(obf_dir)

    print("[pyarmor] Gerando código ofuscado...")
    subprocess.run([
        "pyarmor",
        "gen",
        "-O",
        str(obf_dir),
        str(BASE_DIR / PACKAGE_NAME),
    ], check=True)

    obf_package = obf_dir / PACKAGE_NAME
    target_package = build_lib_path / PACKAGE_NAME

    if target_package.exists():
        shutil.rmtree(target_package)
    shutil.copytree(obf_package, target_package)
    print(f"[pyarmor] Pacote ofuscado copiado para: {target_package}")


class build_py(_build_py):
    def run(self):
        super().run()

        if not should_obfuscate():
            print(f"[pyarmor] Ofuscação desativada ({PYARMOR_ENV}=0)")
            return

        try:
            run_pyarmor(Path(self.build_lib))
        except FileNotFoundError:
            print("[pyarmor] PyArmor não foi encontrado. Instale 'pyarmor' no ambiente para gerar o pacote ofuscado.")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Falha ao gerar ofuscação com PyArmor") from exc


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
        'websocket': ['flask-socketio>=5.0.0'],  # WebSocket opcional
    },
    cmdclass={
        'build_py': build_py,
    },
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
