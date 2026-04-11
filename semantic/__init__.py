# semantic/__init__.py
"""Пакет семантического анализатора для MiniCompiler"""

from .symbol_table import SymbolTable, SymbolInfo, SymbolKind, Type
from .analyzer import SemanticAnalyzer
from .type_system import TypeCompatibility
from .errors import SemanticError

__all__ = [
    'SymbolTable',
    'SymbolInfo',
    'SymbolKind',
    'Type',
    'SemanticAnalyzer',
    'TypeCompatibility',
    'SemanticError'
]