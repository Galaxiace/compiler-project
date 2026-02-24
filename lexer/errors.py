class LexicalError(Exception):
    """Базовый класс для лексических ошибок"""
    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        self.message = message
        super().__init__(f"[{line}:{column}] {message}")


class InvalidCharacterError(LexicalError):
    """Ошибка: недопустимый символ"""
    def __init__(self, char: str, line: int, column: int):
        super().__init__(f"Invalid character '{char}'", line, column)


class UnterminatedStringError(LexicalError):
    """Ошибка: незакрытая строка"""
    def __init__(self, line: int, column: int):
        super().__init__("Unterminated string literal", line, column)


class UnterminatedCommentError(LexicalError):
    """Ошибка: незакрытый комментарий"""
    def __init__(self, line: int, column: int):
        super().__init__("Unterminated multi-line comment", line, column)


class InvalidNumberError(LexicalError):
    """Ошибка: недопустимое число"""
    def __init__(self, value: str, line: int, column: int):
        super().__init__(f"Invalid number format: '{value}'", line, column)


class IdentifierTooLongError(LexicalError):
    """Ошибка: слишком длинный идентификатор"""
    def __init__(self, length: int, max_length: int, line: int, column: int):
        super().__init__(f"Identifier too long ({length} > {max_length})", line, column)


class IntegerOutOfRangeError(LexicalError):
    """Ошибка: целое число вне допустимого диапазона"""
    def __init__(self, value: str, line: int, column: int):
        super().__init__(f"Integer out of range (must be between -2^31 and 2^31-1): '{value}'", line, column)