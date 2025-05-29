#!/usr/bin/env python3

import os

from setuptools import find_packages, setup

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))

setup(
    name="ocode",
    version="0.1.0",
    description="Terminal-native AI coding assistant powered by Ollama models",
    long_description="OCode delivers terminal-native workflow with deep codebase intelligence and autonomous task execution.",
    long_description_content_type="text/markdown",
    author="OCode Team",
    author_email="team@ocode.dev",
    url="https://github.com/ocode/ocode",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9",
        "click>=8.1",
        "rich>=13",
        "gitpython>=3.1",
        "tree-sitter>=0.20",
        "pydantic>=2",
        "pyyaml>=6",
        "prompt-toolkit>=3",
        "aiofiles>=23",
        "watchdog>=3",
        "requests>=2.31.0",
        "pexpect>=4.9.0",
        "psutil>=5.9.0",
        "jsonpath-ng>=1.5.3",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ]
    },
    entry_points={"console_scripts": ["ocode=ocode_python.core.cli:main"]},
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Tools",
        "Topic :: Software Development :: Code Generators",
    ],
    keywords="ai coding assistant terminal ollama llm development",
    project_urls={
        "Bug Reports": "https://github.com/ocode/ocode/issues",
        "Source": "https://github.com/ocode/ocode",
        "Documentation": "https://ocode.dev/docs",
    },
)
