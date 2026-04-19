# semantic/type_system.py
"""
Модуль системы типов для семантического анализа.
"""

from typing import Optional
from .symbol_table import Type


class TypeCompatibility:
    """Класс для проверки совместимости типов."""

    # Правила неявного приведения типов
    IMPLICIT_CASTS = {
        ('int', 'float'): True,  # int -> float (расширение)
        ('bool', 'int'): True,  # bool -> int
        ('int', 'bool'): False,  # int -> bool (нет неявного)
        ('float', 'int'): False,  # float -> int (сужающее)
    }

    @classmethod
    def is_compatible(cls, lhs: Type, rhs: Type) -> bool:
        """Проверяет, совместим ли тип rhs с lhs при присваивании."""
        if lhs == rhs:
            return True

        key = (rhs.name, lhs.name)
        return cls.IMPLICIT_CASTS.get(key, False)

    @classmethod
    def can_compare(cls, left: Type, right: Type, operator: str) -> bool:
        """Проверяет, можно ли сравнить два типа с заданным оператором."""
        numeric_types = {'int', 'float', 'bool'}

        if left.name not in numeric_types or right.name not in numeric_types:
            return False

        if operator in ('==', '!='):
            return True

        return True

    @classmethod
    def get_binary_result_type(cls, left: Type, right: Type, operator: str) -> Optional[Type]:
        """Определяет результирующий тип бинарной операции."""
        # Арифметические операторы
        if operator in ('+', '-', '*', '/', '%'):
            numeric_types = {'int', 'float'}
            if left.name not in numeric_types or right.name not in numeric_types:
                return None

            if left.name == 'float' or right.name == 'float':
                return Type('float')
            return Type('int')

        # Логические операторы
        if operator in ('&&', '||'):
            if left.name == 'bool' and right.name == 'bool':
                return Type('bool')
            return None

        # Оператор XOR (^) - побитовый, работает с int
        if operator == '^':
            if left.name == 'int' and right.name == 'int':
                return Type('int')
            return None

        # Операторы сравнения
        if operator in ('==', '!=', '<', '<=', '>', '>='):
            if cls.can_compare(left, right, operator):
                return Type('bool')
            return None

        return None

    @classmethod
    def get_unary_result_type(cls, operand: Type, operator: str) -> Optional[Type]:
        """Определяет результирующий тип унарной операции."""
        if operator == '-':
            if operand.name in ('int', 'float'):
                return Type(operand.name)
            return None

        if operator == '!':
            if operand.name == 'bool':
                return Type('bool')
            return None

        if operator == '+':
            if operand.name in ('int', 'float'):
                return Type(operand.name)
            return None

        return None