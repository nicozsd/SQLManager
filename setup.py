# Setup para o Core como pacote instalável

from setuptools import setup, find_packages

setup(
    name="SQLManager",
    version="4.2.2",
    description="Sistema para gerenciamento de banco de dados e validações",
    author="Avalon Tecnologia",
    author_email="nicolas.santos@avalontecnologia.com.br",
    url="https://github.com/Avalon-Tecnologia/SQLManager",
    packages=find_packages(include=["SQLManager", "SQLManager.*"]),
    include_package_data=True,
    package_data={
        "SQLManager": [
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
        "pymysql>=1.0.0",
        "cryptography>=3.4.0",
    ],
    extras_require={
        'websocket': ['flask-socketio>=5.0.0'],  # WebSocket opcional
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
