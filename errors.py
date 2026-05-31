"""
Единая система ошибок компилятора (Sprint 8)
Поддерживает:
- Категоризированные коды ошибок (E001-E999, W001-W999)
- Продолжение компиляции после ошибок
- Форматированный вывод с контекстом и подсказками
- JSON формат для интеграции с IDE
- Систему предупреждений с уровнями (-Wall, -Werror)
"""

import sys
import json
from typing import List, Optional, Tuple
from enum import Enum


class ErrorCategory(Enum):
    """Категории ошибок"""
    LEXICAL = "lexical"
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    CODEGEN = "codegen"
    LINKER = "linker"
    RUNTIME = "runtime"


class ErrorSeverity(Enum):
    """Уровни серьёзности"""
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


# Цвета для терминала
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'

    @classmethod
    def disable(cls):
        for attr in dir(cls):
            if not attr.startswith('_') and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, '')


class CompilerMessage:
    """
    Единое сообщение компилятора (ошибка, предупреждение, заметка).
    """

    def __init__(self,
                 code: str,
                 message: str,
                 category: ErrorCategory,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 line: int = 0,
                 column: int = 0,
                 source_line: str = "",
                 context: str = "",
                 suggestion: str = "",
                 file_path: str = "program.src"):
        self.code = code
        self.message = message
        self.category = category
        self.severity = severity
        self.line = line
        self.column = column
        self.source_line = source_line
        self.context = context
        self.suggestion = suggestion
        self.file_path = file_path

    def format_human(self, color: bool = True) -> str:
        """Форматирует сообщение для человека."""
        lines = []

        # Заголовок
        prefix = "error" if self.severity == ErrorSeverity.ERROR else "warning"
        if color:
            color_start = Colors.RED if self.severity == ErrorSeverity.ERROR else Colors.YELLOW
            lines.append(
                f"{color_start}{Colors.BOLD}{self.file_path}:{self.line}:{self.column}: {prefix}: {self.code}: {self.message}{Colors.NC}")
        else:
            lines.append(f"{self.file_path}:{self.line}:{self.column}: {prefix}: {self.code}: {self.message}")

        # Исходная строка с указателем
        if self.source_line and self.line > 0:
            lines.append(f" {Colors.BLUE}{self.line:>3} |{Colors.NC} {self.source_line}")
            if self.column > 0:
                caret = " " * (self.column + 4) + "^"
                lines.append(f"{Colors.GREEN}{caret}{Colors.NC}")

        # Контекст
        if self.context:
            lines.append(f"{Colors.CYAN}  = note: {self.context}{Colors.NC}" if color else f"  = note: {self.context}")

        # Подсказка
        if self.suggestion:
            lines.append(
                f"{Colors.YELLOW}  = help: {self.suggestion}{Colors.NC}" if color else f"  = help: {self.suggestion}")

        return "\n".join(lines)

    def format_json(self) -> str:
        """Форматирует сообщение в JSON для интеграции с IDE."""
        return json.dumps({
            "file": self.file_path,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "context": self.context,
            "suggestion": self.suggestion
        }, indent=2, ensure_ascii=False)


class ErrorHandler:
    """
    Обработчик ошибок компилятора.
    Собирает все сообщения и выводит их в нужном формате.
    """

    def __init__(self,
                 max_errors: int = 20,
                 warning_level: str = "default",
                 warnings_as_errors: bool = False,
                 output_format: str = "human",
                 color: bool = True,
                 source_file: str = "program.src"):
        self.messages: List[CompilerMessage] = []
        self.max_errors = max_errors
        self.warning_level = warning_level
        self.warnings_as_errors = warnings_as_errors
        self.output_format = output_format
        self.color = color
        self.source_file = source_file
        self.error_count = 0
        self.warning_count = 0

        # Хранилище строк исходного файла для контекста
        self.source_lines: List[str] = []

    def load_source(self, source: str):
        """Загружает исходный код для отображения контекста ошибок."""
        self.source_lines = source.split('\n')

    def get_source_line(self, line: int) -> str:
        """Возвращает строку исходного кода по номеру (1-indexed)."""
        if 0 < line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def add_error(self, code: str, message: str, category: ErrorCategory,
                  line: int = 0, column: int = 0,
                  context: str = "", suggestion: str = ""):
        """Добавляет ошибку."""
        source_line = self.get_source_line(line) if line > 0 else ""

        msg = CompilerMessage(
            code=code,
            message=message,
            category=category,
            severity=ErrorSeverity.ERROR,
            line=line,
            column=column,
            source_line=source_line,
            context=context,
            suggestion=suggestion,
            file_path=self.source_file
        )

        self.messages.append(msg)
        self.error_count += 1

        # Выводим сразу
        if self.output_format == "json":
            print(msg.format_json(), file=sys.stderr)
        else:
            print(msg.format_human(self.color), file=sys.stderr)

    def add_warning(self, code: str, message: str, category: ErrorCategory,
                    line: int = 0, column: int = 0,
                    context: str = "", suggestion: str = ""):
        """Добавляет предупреждение (с учётом уровня)."""
        # Проверяем уровень предупреждений
        if self.warning_level == "none":
            return
        if self.warning_level == "default" and not code.startswith('W2'):
            return

        source_line = self.get_source_line(line) if line > 0 else ""

        msg = CompilerMessage(
            code=code,
            message=message,
            category=category,
            severity=ErrorSeverity.WARNING if not self.warnings_as_errors else ErrorSeverity.ERROR,
            line=line,
            column=column,
            source_line=source_line,
            context=context,
            suggestion=suggestion,
            file_path=self.source_file
        )

        self.messages.append(msg)

        if self.warnings_as_errors:
            self.error_count += 1
        else:
            self.warning_count += 1

        # Выводим сразу
        if self.output_format == "json":
            print(msg.format_json(), file=sys.stderr)
        else:
            print(msg.format_human(self.color), file=sys.stderr)

    def has_errors(self) -> bool:
        """Проверяет наличие ошибок."""
        return self.error_count > 0

    def too_many_errors(self) -> bool:
        """Проверяет, не превышен ли лимит ошибок."""
        if self.error_count > self.max_errors:
            print(f"\n{Colors.RED}Fatal: Too many errors ({self.max_errors} maximum). Aborting compilation.{Colors.NC}",
                  file=sys.stderr)
            return True
        return False

    def print_summary(self):
        """Выводит сводку по ошибкам и предупреждениям."""
        total = self.error_count + self.warning_count
        if total == 0:
            return

        parts = []
        if self.error_count > 0:
            parts.append(f"{self.error_count} error{'s' if self.error_count != 1 else ''}")
        if self.warning_count > 0:
            parts.append(f"{self.warning_count} warning{'s' if self.warning_count != 1 else ''}")

        summary = ", ".join(parts) + " generated."

        if self.error_count > 0:
            print(f"\n{Colors.RED}{summary} Compilation failed.{Colors.NC}", file=sys.stderr)
        else:
            print(f"\n{Colors.YELLOW}{summary}{Colors.NC}", file=sys.stderr)


# ============================================================
# Коды ошибок
# ============================================================

class ErrorCodes:
    """
    Реестр кодов ошибок.

    Категории:
    E001-E099: Лексические ошибки
    E100-E199: Синтаксические ошибки
    E200-E299: Семантические ошибки (типы)
    E300-E399: Семантические ошибки (символы)
    E400-E499: Ошибки кодогенерации
    E500-E599: Ошибки линковки

    W001-W099: Предупреждения (общие)
    W100-W199: Предупреждения (стиль)
    W200-W299: Предупреждения (производительность)
    """

    # Лексические ошибки
    LEX_INVALID_CHAR = "E001"
    LEX_UNTERMINATED_STRING = "E002"
    LEX_UNTERMINATED_COMMENT = "E003"
    LEX_INVALID_NUMBER = "E004"
    LEX_IDENTIFIER_TOO_LONG = "E005"
    LEX_INTEGER_OUT_OF_RANGE = "E006"

    # Синтаксические ошибки
    SYNTAX_UNEXPECTED_TOKEN = "E100"
    SYNTAX_MISSING_SEMICOLON = "E101"
    SYNTAX_MISMATCHED_PAREN = "E102"
    SYNTAX_MISSING_TOKEN = "E103"

    # Семантические ошибки (типы)
    SEMANTIC_TYPE_MISMATCH = "E200"
    SEMANTIC_INVALID_OPERATION = "E201"
    SEMANTIC_INVALID_CONDITION = "E202"
    SEMANTIC_INVALID_RETURN = "E203"

    # Семантические ошибки (символы)
    SEMANTIC_UNDECLARED = "E300"
    SEMANTIC_DUPLICATE = "E301"
    SEMANTIC_UNINITIALIZED = "E302"
    SEMANTIC_WRONG_ARG_COUNT = "E303"
    SEMANTIC_INVALID_ASSIGNMENT = "E304"

    # Предупреждения
    WARN_UNUSED_VARIABLE = "W001"
    WARN_IMPLICIT_CAST = "W002"
    WARN_UNREACHABLE_CODE = "W003"


# ============================================================
# Фабрика сообщений для быстрого создания
# ============================================================

class ErrorFactory:
    """Фабрика для создания типовых сообщений об ошибках."""

    @staticmethod
    def invalid_character(char: str, line: int, column: int) -> CompilerMessage:
        return CompilerMessage(
            code=ErrorCodes.LEX_INVALID_CHAR,
            message=f"Invalid character '{char}'",
            category=ErrorCategory.LEXICAL,
            line=line,
            column=column,
            suggestion="Remove or replace this character"
        )

    @staticmethod
    def unterminated_string(line: int, column: int) -> CompilerMessage:
        return CompilerMessage(
            code=ErrorCodes.LEX_UNTERMINATED_STRING,
            message="Unterminated string literal",
            category=ErrorCategory.LEXICAL,
            line=line,
            column=column,
            suggestion="Add closing double-quote (\")"
        )

    @staticmethod
    def unexpected_token(expected: str, found: str, line: int, column: int) -> CompilerMessage:
        return CompilerMessage(
            code=ErrorCodes.SYNTAX_UNEXPECTED_TOKEN,
            message=f"Expected {expected}, but found {found}",
            category=ErrorCategory.SYNTAX,
            line=line,
            column=column
        )

    @staticmethod
    def undefined_variable(name: str, line: int, column: int,
                           similar: Optional[str] = None) -> CompilerMessage:
        suggestion = ""
        if similar:
            suggestion = f"Did you mean '{similar}'?"
        return CompilerMessage(
            code=ErrorCodes.SEMANTIC_UNDECLARED,
            message=f"Undefined variable '{name}'",
            category=ErrorCategory.SEMANTIC,
            line=line,
            column=column,
            suggestion=suggestion
        )

    @staticmethod
    def type_mismatch(expected: str, found: str, line: int, column: int,
                      context: str = "") -> CompilerMessage:
        return CompilerMessage(
            code=ErrorCodes.SEMANTIC_TYPE_MISMATCH,
            message=f"Type mismatch: expected '{expected}', found '{found}'",
            category=ErrorCategory.SEMANTIC,
            line=line,
            column=column,
            context=context
        )

    @staticmethod
    def unused_variable(name: str, line: int, column: int) -> CompilerMessage:
        return CompilerMessage(
            code=ErrorCodes.WARN_UNUSED_VARIABLE,
            message=f"Unused variable '{name}'",
            category=ErrorCategory.SEMANTIC,
            severity=ErrorSeverity.WARNING,
            line=line,
            column=column,
            suggestion=f"Remove or use the variable '{name}'"
        )