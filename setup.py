# Setup para o Core como pacote instalável

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.build_py import build_py
import os
import py_compile
import shutil
from pathlib import Path

class ObfuscatedBuildCommand(build_py):
    """
    Comando customizado que ofusca o código durante o build.
    Compila arquivos .py para .pyc e mantém apenas bytecode.
    """
    def run(self):
        # Rodar build padrão primeiro
        build_py.run(self)
        
        # Ofuscar código no diretório de build
        build_lib = Path(self.build_lib) / 'SQLManager'
        
        if build_lib.exists() and os.getenv('OBFUSCATE_BUILD', '1') == '1':
            print("\nOfuscando código SQLManager...")
            self.obfuscate_directory(build_lib)
            print("Ofuscação concluída!\n")
    
    def obfuscate_directory(self, target_dir):
        """Compila .py para .pyc e remove código fonte legível."""
        for root, dirs, files in os.walk(target_dir):
            # Ignorar __pycache__
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    source_path = os.path.join(root, file)
                    
                    try:
                        # Compilar para bytecode
                        py_compile.compile(source_path, doraise=True)
                        
                        # Substituir .py por versão minificada
                        with open(source_path, 'w', encoding='utf-8') as f:
                            f.write("# SQLManager - Código Ofuscado\n")
                            f.write("# Avalon Tecnologia © 2026\n")
                            f.write(f"exec(__import__('importlib.util').util.spec_from_file_location('{file[:-3]}',__file__.replace('.py','.pyc')).loader.load_module().__dict__.get('__code__',compile('','','exec')))\n")
                        
                        print(f"{file}")
                        
                    except Exception as e:
                        print(f"Erro ao ofuscar {file}: {e}")

class CustomInstallCommand(install):
    '''Atua como um start no pip install'''
    def run(self):                        
        install.run(self)                           


setup(
    name="SQLManager",
    version="4.2.2",
    description="Sistema para gerenciamento de banco de dados e validações",
    author="Avalon Tecnologia",
    author_email="nicolas.santos@avalontecnologia.com.br",
    url="https://github.com/Avalon-Tecnologia/SQLManager",
    packages=find_packages(include=["SQLManager", "SQLManager.*"]),
    include_package_data=True,
    #''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
    package_data={
        "SQLManager": [
            "_model/*.py",
            "EDTs/*.py",
            "enum/*.py",
            "tables/*.py",
            "views/*.py",
        ]
    },
    #''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
    python_requires=">=3.8",
    install_requires=[
        "pyodbc>=4.0.0",
        "python-dotenv>=0.19.0",
        
        #''' [BEGIN CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
        "flask-socketio>=5.0.0",  # Para WebSocketManager
        #''' [END CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    cmdclass={
        'build_py': ObfuscatedBuildCommand,  # Ofusca durante build
        'install': CustomInstallCommand,        
    },
    license="MIT",
    license_file="LICENSE",
)
