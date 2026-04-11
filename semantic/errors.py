# semantic/errors.py
"""
Модуль ошибок семантического анализатора.
"""

from typing import Optional


class SemanticError(Exception):
    """Базовый класс для семантических ошибок."""

    def __init__(self, message: str, line: int, column: int,
                 context: Optional[str] = None,
                 expected: Optional[str] = None,
                 found: Optional[str] = None,
                 suggestion: Optional[str] = None):
        self.line = line
        self.column = column
        self.message = message
        self.context = context
        self.expected = expected
        self.found = found
        self.suggestion = suggestion
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Форматирует сообщение об ошибке."""
        lines = [f"semantic error: {self.message}"]
        lines.append(f"---> program.src:{self.line}:{self.column}")

        if self.context:
            lines.append(f"= in: {self.context}")

        if self.expected is not None and self.found is not None:
            lines.append(f"= expected: {self.expected}")
            lines.append(f"= found: {self.found}")

        if self.suggestion:
            lines.append(f"= note: {self.suggestion}")

        return "\n".join(lines)

    def __str__(self):
        return self.format_message()


class UndeclaredIdentifierError(SemanticError):
    """Ошибка: использование необъявленного идентификатора."""

    def __init__(self, name: str, line: int, column: int, suggestion: Optional[str] = None):
        message = f"undeclared variable '{name}'"
        super().__init__(message, line, column, suggestion=suggestion)


class DuplicateDeclarationError(SemanticError):
    """Ошибка: повторное объявление символа."""

    def __init__(self, name: str, kind: str, line: int, column: int, prev_line: int):
        message = f"duplicate {kind} declaration '{name}'"
        context = f"previously declared at line {prev_line}"
        super().__init__(message, line, column, context=context)


class TypeMismatchError(SemanticError):
    """Ошибка: несоответствие типов."""

    def __init__(self, expected: str, found: str, line: int, column: int, context: str = ""):
        message = f"type mismatch in {context}" if context else "type mismatch"
        super().__init__(message, line, column, expected=expected, found=found)


class ArgumentCountMismatchError(SemanticError):
    """Ошибка: несоответствие количества аргументов."""

    def __init__(self, func_name: str, expected: int, found: int, line: int, column: int):
        message = f"argument count mismatch in call to '{func_name}'"
        super().__init__(message, line, column,
                         expected=str(expected), found=str(found))


class InvalidReturnTypeError(SemanticError):
    """Ошибка: несоответствие возвращаемого типа."""

    def __init__(self, expected: str, found: str, line: int, column: int):
        message = "invalid return type"
        super().__init__(message, line, column, expected=expected, found=found)


class InvalidConditionTypeError(SemanticError):
    """Ошибка: неверный тип условия."""

    def __init__(self, found: str, line: int, column: int):
        message = "condition must be boolean"
        super().__init__(message, line, column, expected="bool", found=found)


class InvalidAssignmentTargetError(SemanticError):
    """Ошибка: попытка присвоить значение не переменной."""

    def __init__(self, line: int, column: int):
        message = "invalid assignment target"
        super().__init__(message, line, column)


class UseBeforeDeclarationError(SemanticError):
    """Ошибка: использование переменной до инициализации."""

    def __init__(self, name: str, line: int, column: int):
        message = f"variable '{name}' may be uninitialized"
        super().__init__(message, line, column)