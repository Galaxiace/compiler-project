"""
Setup configuration for MiniCompiler project.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="compiler",
    version="0.1.0",
    author="Galaxiace",
    author_email="zevs2885@gmail.com",
    description="A mini compiler for a C-like language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Galaxiace/compiler-project",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "compiler=lexer.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)