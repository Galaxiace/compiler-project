from enum import Enum, auto
from typing import Union, Optional


class TokenType(Enum):
    # Keywords
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    VOID = auto()
    STRUCT = auto()
    FN = auto()

    # Operators
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    PERCENT = auto()  # %
    ASSIGN = auto()  # =
    PLUS_ASSIGN = auto()  # +=
    MINUS_ASSIGN = auto()  # -=
    STAR_ASSIGN = auto()  # *=
    SLASH_ASSIGN = auto()  # /=
    PERCENT_ASSIGN = auto()  # %=
    EQ_EQ = auto()  # ==
    NOT_EQ = auto()  # !=
    LESS = auto()  # <
    GREATER = auto()  # >
    LESS_EQ = auto()  # <=
    GREATER_EQ = auto()  # >=
    AND = auto()  # &
    AND_AND = auto()  # &&
    XOR = auto()  # ^
    OR = auto()  # |
    OR_OR = auto()  # ||
    NOT = auto()  # ! (логическое НЕ)
    ARROW = auto()  # ->
    DOT = auto()   # . (доступ к полям)

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    SEMICOLON = auto()  # ;
    COMMA = auto()  # ,

    # Literals
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()

    # Special
    END_OF_FILE = auto()
    INVALID = auto()


class Token:
    def __init__(self,
                 type: TokenType,
                 lexeme: str,
                 line: int,
                 column: int,
                 literal: Optional[Union[int, float, str, bool]] = None):
        self.type = type
        self.lexeme = lexeme
        self.line = line
        self.column = column
        self.literal = literal

    def __str__(self):
        literal_str = f" {self.literal}" if self.literal is not None else ""

        # Для INVALID токенов выводим как есть
        if self.type == TokenType.INVALID:
            return f"{self.line}:{self.column} {self.type.name} \"{self.lexeme}\"{literal_str}"

        return f"{self.line}:{self.column} {self.type.name} \"{self.lexeme}\"{literal_str}"

    def __repr__(self):
        return self.__str__()


# Маппинг ключевых слов
KEYWORDS = {
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'int': TokenType.INT,
    'float': TokenType.FLOAT,
    'bool': TokenType.BOOL,
    'return': TokenType.RETURN,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'void': TokenType.VOID,
    'struct': TokenType.STRUCT,
    'fn': TokenType.FN
}

# Операторы и их типы
OPERATORS = {
    '+': TokenType.PLUS,
    '-': TokenType.MINUS,
    '*': TokenType.STAR,
    '/': TokenType.SLASH,
    '%': TokenType.PERCENT,
    '=': TokenType.ASSIGN,
    '==': TokenType.EQ_EQ,
    '!=': TokenType.NOT_EQ,
    '<': TokenType.LESS,
    '>': TokenType.GREATER,
    '<=': TokenType.LESS_EQ,
    '>=': TokenType.GREATER_EQ,
    '&': TokenType.AND,
    '&&': TokenType.AND_AND,
    '^': TokenType.XOR,
    '|': TokenType.OR,
    '||': TokenType.OR_OR,
    '!': TokenType.NOT,
    '->': TokenType.ARROW,
    '+=': TokenType.PLUS_ASSIGN,
    '-=': TokenType.MINUS_ASSIGN,
    '*=': TokenType.STAR_ASSIGN,
    '/=': TokenType.SLASH_ASSIGN,
    '%=': TokenType.PERCENT_ASSIGN,
    '.': TokenType.DOT,  # оператор доступа к полям
}

# Разделители
DELIMITERS = {
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
    '{': TokenType.LBRACE,
    '}': TokenType.RBRACE,
    '[': TokenType.LBRACKET,
    ']': TokenType.RBRACKET,
    ';': TokenType.SEMICOLON,
    ',': TokenType.COMMA
}

# Константы
MAX_IDENTIFIER_LENGTH = 255
MAX_INT_VALUE = 2**31 - 1
MIN_INT_VALUE = -2**31