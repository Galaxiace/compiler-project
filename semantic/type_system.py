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

        # Для массивов
        if lhs.is_array and rhs.is_array:
            return cls.is_compatible(lhs.element_type, rhs.element_type)

        # Передача массива в параметр-массив (указатель)
        # lhs - параметр функции (array), rhs - аргумент (array)
        if lhs.is_array and rhs.is_array:
            return True

        # Для структур
        if lhs.is_struct and rhs.is_struct:
            return lhs.name == rhs.name

        # Для extern-функций разрешаем string → int (передача указателей)
        if lhs.name == 'int' and rhs.name == 'string':
            return True

        key = (rhs.name, lhs.name)
        return cls.IMPLICIT_CASTS.get(key, False)

    @classmethod
    def can_compare(cls, left: Type, right: Type, operator: str) -> bool:
        """Проверяет, можно ли сравнить два типа с заданным оператором."""
        numeric_types = {'int', 'float', 'bool'}

        # Для массивов - можно сравнивать указатели
        if left.is_array and right.is_array:
            return operator in ('==', '!=')

        # Для структур - можно сравнивать по значению?
        if left.is_struct and right.is_struct:
            return operator in ('==', '!=') and left.name == right.name

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
            # Массивы: операции не поддерживаются
            if left.is_array or right.is_array:
                return None

            numeric_types = {'int', 'float'}
            if left.name not in numeric_types or right.name not in numeric_types:
                return None

            if left.name == 'float' or right.name == 'float':
                return Type('float')
            return Type('int')

        # Логические операторы
        if operator in ('&&', '||'):
            if left.is_array or right.is_array:
                return None
            if left.name == 'bool' and right.name == 'bool':
                return Type('bool')
            return None

        # Оператор XOR (^) - побитовый, работает с int
        if operator == '^':
            if left.is_array or right.is_array:
                return None
            if left.name == 'int' and right.name == 'int':
                return Type('int')
            return None

        # Операторы сравнения
        if operator in ('==', '!=', '<', '<=', '>', '>='):
            # Поддержка сравнения массивов (указатели)
            if left.is_array and right.is_array:
                return Type('bool')
            # Поддержка сравнения структур
            if left.is_struct and right.is_struct and left.name == right.name:
                return Type('bool')
            if cls.can_compare(left, right, operator):
                return Type('bool')
            return None

        return None

    @classmethod
    def get_unary_result_type(cls, operand: Type, operator: str) -> Optional[Type]:
        """Определяет результирующий тип унарной операции."""
        if operator == '-':
            if operand.is_array:
                return None
            if operand.name in ('int', 'float'):
                return Type(operand.name)
            return None

        if operator == '!':
            if operand.is_array:
                return None
            if operand.name == 'bool':
                return Type('bool')
            return None

        if operator == '+':
            if operand.is_array:
                return None
            if operand.name in ('int', 'float'):
                return Type(operand.name)
            return None

        return None

    @classmethod
    def is_float_type(cls, type_obj: Type) -> bool:
        """Проверяет, является ли тип float."""
        return type_obj.name == 'float'

    @classmethod
    def get_comparison_instruction(cls, left: Type, right: Type, operator: str) -> str:
        """
        Возвращает тип сравнения (int или float).
        """
        if cls.is_float_type(left) or cls.is_float_type(right):
            return 'float'
        return 'int'