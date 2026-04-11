# semantic/symbol_table.py
"""
Модуль таблицы символов для семантического анализа.
Поддерживает вложенные области видимости и различные типы символов.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum, auto
from dataclasses import dataclass, field


class SymbolKind(Enum):
    """Типы символов, которые могут храниться в таблице"""
    VARIABLE = auto()
    FUNCTION = auto()
    PARAMETER = auto()
    STRUCT = auto()
    FIELD = auto()


@dataclass
class Type:
    """
    Представление типа в семантическом анализаторе.
    ВНИМАНИЕ: Это отдельный класс, не связанный с parser.ast.Type!
    """
    name: str  # 'int', 'float', 'bool', 'void', 'string' или имя структуры
    is_struct: bool = False
    fields: Dict[str, 'Type'] = field(default_factory=dict)  # Для структур
    param_types: List['Type'] = field(default_factory=list)  # Для функций
    return_type: Optional['Type'] = None  # Для функций
    is_array: bool = False
    array_size: Optional[int] = None
    element_type: Optional['Type'] = None

    # Для отслеживания размера в памяти (stretch goal)
    size_bytes: int = 0
    alignment: int = 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Type):
            return False

        # Базовые типы
        if not self.is_struct and not other.is_struct:
            return self.name == other.name

        # Структуры
        if self.is_struct and other.is_struct:
            if self.name != other.name:
                return False
            # Сравниваем поля
            if set(self.fields.keys()) != set(other.fields.keys()):
                return False
            for name, field_type in self.fields.items():
                if name not in other.fields or field_type != other.fields[name]:
                    return False
            return True

        # Функциональные типы
        if self.return_type is not None and other.return_type is not None:
            if self.return_type != other.return_type:
                return False
            if len(self.param_types) != len(other.param_types):
                return False
            for pt1, pt2 in zip(self.param_types, other.param_types):
                if pt1 != pt2:
                    return False
            return True

        # Массивы
        if self.is_array and other.is_array:
            return (self.element_type == other.element_type and
                    self.array_size == other.array_size)

        return False

    def __hash__(self):
        return hash((self.name, self.is_struct, tuple(self.fields.keys())))

    def __repr__(self):
        if self.is_array:
            return f"{self.element_type}[{self.array_size}]" if self.array_size else f"{self.element_type}[]"
        if self.is_struct:
            return f"struct {self.name}"
        if self.return_type is not None:
            params = ", ".join(str(t) for t in self.param_types)
            return f"({params}) -> {self.return_type}"
        return self.name


@dataclass
class SymbolInfo:
    """Информация о символе в таблице"""
    name: str
    kind: SymbolKind
    type: Type
    line: int
    column: int

    # Дополнительная информация для функций
    parameters: List[Any] = field(default_factory=list)  # List[ParamNode]
    return_type_node: Optional[Type] = None

    # Для структур
    fields: Dict[str, Type] = field(default_factory=dict)

    # Для отслеживания инициализации (базовая проверка)
    is_initialized: bool = False

    # Для layout (stretch goal)
    stack_offset: int = -1
    size_bytes: int = 0

    def __repr__(self):
        return f"SymbolInfo({self.name}, {self.kind.name}, {self.type})"


class Scope:
    """Представляет одну область видимости"""

    def __init__(self, name: str, level: int, parent: Optional['Scope'] = None):
        self.name = name  # 'global', 'function:main', 'block:5'
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, SymbolInfo] = {}
        self.children: List['Scope'] = []

    def insert(self, name: str, info: SymbolInfo) -> bool:
        """Вставляет символ в текущую область. Возвращает True если успешно."""
        if name in self.symbols:
            return False
        self.symbols[name] = info
        return True

    def lookup_local(self, name: str) -> Optional[SymbolInfo]:
        """Ищет символ только в текущей области."""
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[SymbolInfo]:
        """Ищет символ в текущей и родительских областях."""
        scope = self
        while scope:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def get_all_symbols(self) -> Dict[str, SymbolInfo]:
        """Возвращает все символы в текущей области."""
        return self.symbols.copy()

    def __repr__(self):
        return f"Scope({self.name}, level={self.level}, symbols={list(self.symbols.keys())})"


class SymbolTable:
    """
    Иерархическая таблица символов.

    Пример использования:
        table = SymbolTable()
        table.enter_scope("global")
        table.insert("x", SymbolInfo(...))
        table.enter_scope("function:main")
        table.insert("y", SymbolInfo(...))
        table.lookup("x")  # Найдет в глобальной области
        table.lookup_local("y")  # Найдет только в текущей
        table.exit_scope()
    """

    def __init__(self):
        self.global_scope = Scope("global", 0, None)
        self.current_scope = self.global_scope
        self.scope_stack: List[Scope] = [self.global_scope]
        self.scope_counter = 1  # Для уникальных имен областей

    def enter_scope(self, name: str = None) -> Scope:
        """
        Входит в новую вложенную область видимости.

        Args:
            name: Имя области (опционально)

        Returns:
            Scope: Созданная область
        """
        if name is None:
            name = f"block_{self.scope_counter}"
            self.scope_counter += 1

        new_scope = Scope(name, len(self.scope_stack), self.current_scope)
        self.current_scope.children.append(new_scope)
        self.current_scope = new_scope
        self.scope_stack.append(new_scope)
        return new_scope

    def exit_scope(self) -> Optional[Scope]:
        """
        Выходит из текущей области видимости.

        Returns:
            Scope: Предыдущая область или None
        """
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]
            return self.current_scope
        return None

    def insert(self, name: str, info: SymbolInfo) -> bool:
        """
        Вставляет символ в текущую область.

        Args:
            name: Имя символа
            info: Информация о символе

        Returns:
            bool: True если вставка успешна, False если символ уже существует
        """
        return self.current_scope.insert(name, info)

    def lookup(self, name: str) -> Optional[SymbolInfo]:
        """
        Ищет символ от текущей области к глобальной.

        Args:
            name: Имя символа

        Returns:
            SymbolInfo или None
        """
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[SymbolInfo]:
        """
        Ищет символ только в текущей области.

        Args:
            name: Имя символа

        Returns:
            SymbolInfo или None
        """
        return self.current_scope.lookup_local(name)

    def get_current_scope(self) -> Scope:
        """Возвращает текущую область видимости."""
        return self.current_scope

    def get_global_scope(self) -> Scope:
        """Возвращает глобальную область видимости."""
        return self.global_scope

    def dump(self) -> str:
        """
        Возвращает строковое представление таблицы символов.

        Returns:
            str: Dump таблицы символов
        """
        lines = []
        self._dump_scope(self.global_scope, 0, lines)
        return "\n".join(lines)

    def _dump_scope(self, scope: Scope, indent: int, lines: List[str]):
        """Рекурсивно выводит область видимости."""
        prefix = "  " * indent
        lines.append(f"{prefix}Scope: {scope.name} (level {scope.level})")

        if scope.symbols:
            lines.append(f"{prefix}  Symbols:")
            for name, info in scope.symbols.items():
                init_mark = " (initialized)" if info.is_initialized else ""
                lines.append(
                    f"{prefix}    - {name}: {info.kind.name} -> {info.type}{init_mark} [{info.line}:{info.column}]")

                if info.kind == SymbolKind.FUNCTION and info.parameters:
                    params_str = ", ".join(
                        f"{getattr(p, 'type_name', 'unknown')} {getattr(p, 'name', '?')}" for p in info.parameters)
                    lines.append(f"{prefix}      params: ({params_str})")
                elif info.kind == SymbolKind.STRUCT and info.fields:
                    fields_str = ", ".join(f"{fname}: {ftype}" for fname, ftype in info.fields.items())
                    lines.append(f"{prefix}      fields: {{{fields_str}}}")

        for child in scope.children:
            self._dump_scope(child, indent + 1, lines)


def create_builtin_types() -> Dict[str, Type]:
    """Создает встроенные типы языка."""
    return {
        'int': Type('int', size_bytes=4, alignment=4),
        'float': Type('float', size_bytes=8, alignment=8),
        'bool': Type('bool', size_bytes=1, alignment=1),
        'void': Type('void', size_bytes=0, alignment=0),
        'string': Type('string', size_bytes=8, alignment=8),  # указатель на строку
    }