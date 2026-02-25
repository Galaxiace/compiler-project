from typing import List, Optional
from .token import Token, TokenType, KEYWORDS, OPERATORS, DELIMITERS, MAX_IDENTIFIER_LENGTH, MAX_INT_VALUE, \
    MIN_INT_VALUE
from .errors import *


class Scanner:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.errors: List[LexicalError] = []

    def scan_tokens(self) -> List[Token]:
        """Сканирует все токены из исходного кода"""
        while not self.is_at_end():
            self.start = self.current
            self._scan_token()

        # Добавляем EOF токен
        self.tokens.append(Token(TokenType.END_OF_FILE, "", self.line, self.column))
        return self.tokens

    def _scan_token(self):
        """Сканирует один токен"""
        char = self._advance()

        if char == '\n':
            self.line += 1
            self.column = 1
        elif char in ' \t\r':
            # Пропускаем пробелы
            pass
        elif char == '/':
            if self._match('/'):
                # Однострочный комментарий
                self._skip_single_line_comment()
            elif self._match('*'):
                # Многострочный комментарий
                self._skip_multi_line_comment()
            else:
                self._add_operator_token(char)
        elif char == '"':
            self._read_string()
        elif char.isdigit():
            self._read_number()
        elif char == '-':
            # Проверяем, является ли это отрицательным числом
            if self._is_negative_number():
                self._read_number()
            else:
                self._add_operator_token(char)
        elif char.isalpha() or char == '_':
            self._read_identifier()
        elif char in '+-*/%=<>!&|':  # Все операторы (кроме '-', который обработан выше)
            self._read_operator(char)
        elif char in '(){};,':
            self._add_delimiter_token(char)
        else:
            # Недопустимый символ
            error = InvalidCharacterError(char, self.line, self.column - 1)
            self.errors.append(error)
            self._add_token(TokenType.INVALID, char)

    def _is_negative_number(self) -> bool:
        """
        Определяет, является ли текущий минус началом отрицательного числа.
        Минус считается частью числа, если:
        1. После него идет цифра
        2. Перед ним нет числа/идентификатора (или это начало строки)
        3. Предыдущий символ - не цифра и не идентификатор
        """
        if self.is_at_end() or not self._peek().isdigit():
            return False

        # Если это первый символ в строке - может быть отрицательным числом
        if self.start == 0:
            return True

        # Проверяем предыдущий символ
        prev_char = self.source[self.start - 1]

        # Если перед минусом был пробел, табуляция, перевод строки или открывающая скобка - это отрицательное число
        if prev_char in ' \t\n\r({[':
            return True

        # Если перед минусом был оператор - это отрицательное число
        if prev_char in '+-*/%=<>!&|':
            return True

        # В остальных случаях (цифра, буква, подчеркивание) - это оператор вычитания
        return False

    def _advance(self) -> str:
        """Продвигает указатель на один символ и возвращает его"""
        self.current += 1
        self.column += 1
        return self.source[self.current - 1]

    def _peek(self) -> str:
        """Возвращает текущий символ без продвижения"""
        if self.is_at_end():
            return '\0'
        return self.source[self.current]

    def _peek_next(self) -> str:
        """Возвращает следующий символ без продвижения"""
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]

    def _match(self, expected: str) -> bool:
        """Проверяет, совпадает ли текущий символ с ожидаемым"""
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False

        self.current += 1
        self.column += 1
        return True

    def _is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец файла"""
        return self.current >= len(self.source)

    def is_at_end(self) -> bool:
        """Публичный метод для проверки конца файла"""
        return self._is_at_end()

    def _add_token(self, token_type: TokenType, lexeme: str = None, literal=None):
        """Добавляет токен в список"""
        if lexeme is None:
            lexeme = self.source[self.start:self.current]
        token = Token(token_type, lexeme, self.line, self.column - len(lexeme), literal)
        self.tokens.append(token)

    def _add_operator_token(self, char: str):
        """Добавляет токен оператора"""
        if char in OPERATORS:
            self._add_token(OPERATORS[char])
        else:
            error = InvalidCharacterError(char, self.line, self.column - 1)
            self.errors.append(error)
            self._add_token(TokenType.INVALID, char)

    def _add_delimiter_token(self, char: str):
        """Добавляет токен разделителя"""
        self._add_token(DELIMITERS[char])

    def _skip_single_line_comment(self):
        """Пропускает однострочный комментарий"""
        while not self.is_at_end() and self._peek() != '\n':
            self._advance()

    def _skip_multi_line_comment(self):
        """Пропускает многострочный комментарий"""
        while not self.is_at_end():
            if self._peek() == '*' and self._peek_next() == '/':
                self._advance()  # Пропускаем *
                self._advance()  # Пропускаем /
                return
            elif self._peek() == '\n':
                self.line += 1
                self.column = 1
            self._advance()

        # Если дошли до конца файла без закрытия комментария
        self.errors.append(UnterminatedCommentError(self.line, self.column))

    def _read_string(self):
        """Читает строковый литерал"""
        string_start_line = self.line
        string_start_column = self.column - 1  # Начальная позиция кавычки

        # Запоминаем начальную позицию для токена INVALID
        token_start_line = self.line
        token_start_column = self.column - 1

        # Флаг для отслеживания, была ли ошибка
        has_error = False

        while not self.is_at_end() and self._peek() != '"':
            if self._peek() == '\n':
                # Встретили перевод строки внутри незакрытой строки - это ошибка
                has_error = True
                break
            self._advance()

        if self.is_at_end() or has_error:
            # Ошибка: строка не закрыта
            self.errors.append(UnterminatedStringError(string_start_line, string_start_column))

            # Создаем INVALID токен для незакрытой строки
            string_value = self.source[self.start + 1:self.current]
            token = Token(
                TokenType.INVALID,
                string_value,
                token_start_line,
                token_start_column,
                literal=None
            )
            self.tokens.append(token)

            # Если мы остановились из-за перевода строки, не продвигаем указатель дальше
            # чтобы следующий токен обрабатывался с начала новой строки
            return

        # Закрывающая кавычка
        self._advance()

        # Извлекаем значение строки без кавычек
        string_value = self.source[self.start + 1:self.current - 1]
        self._add_token(TokenType.STRING_LITERAL, literal=string_value)

    def _read_number(self):
        """Читает числовой литерал (int или float)"""
        is_float = False
        start_line = self.line
        start_column = self.column - len(self.source[self.start:self.current])

        # Проверяем, начинается ли число с минуса
        is_negative = self.source[self.start] == '-'
        if is_negative:
            # Пропускаем минус (он уже считан в _advance)
            pass

        # Читаем целую часть
        while not self.is_at_end() and self._peek().isdigit():
            self._advance()

        # Проверяем, есть ли дробная часть
        if not self.is_at_end() and self._peek() == '.':
            is_float = True
            self._advance()  # Пропускаем точку

            # Должна быть хотя бы одна цифра после точки
            if not self.is_at_end() and self._peek().isdigit():
                while not self.is_at_end() and self._peek().isdigit():
                    self._advance()
            else:
                self.errors.append(InvalidNumberError(
                    self.source[self.start:self.current],
                    self.line,
                    self.column
                ))
                self._add_token(TokenType.INVALID, self.source[self.start:self.current])
                return

        number_str = self.source[self.start:self.current]

        # Проверяем, не начинается ли число с нуля (для целых, исключая отрицательные)
        if not is_float and len(number_str) > 1 and number_str[0] == '0':
            # Разрешено только число 0 само по себе
            if number_str != '0' and not (is_negative and number_str == '-0'):
                self.errors.append(InvalidNumberError(number_str, start_line, start_column))

        if is_float:
            try:
                value = float(number_str)
                self._add_token(TokenType.FLOAT_LITERAL, literal=value)
            except ValueError:
                self.errors.append(InvalidNumberError(number_str, self.line, self.column))
                self._add_token(TokenType.INVALID, number_str)
        else:
            try:
                value = int(number_str)
                # Проверяем диапазон для целых чисел
                if value > MAX_INT_VALUE or value < MIN_INT_VALUE:
                    self.errors.append(IntegerOutOfRangeError(number_str, start_line, start_column))
                self._add_token(TokenType.INT_LITERAL, literal=value)
            except ValueError:
                self.errors.append(InvalidNumberError(number_str, self.line, self.column))
                self._add_token(TokenType.INVALID, number_str)

    def _read_identifier(self):
        """Читает идентификатор или ключевое слово"""
        start_line = self.line
        start_column = self.column - 1

        while not self.is_at_end() and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()

        identifier = self.source[self.start:self.current]

        # Проверяем максимальную длину идентификатора
        if len(identifier) > MAX_IDENTIFIER_LENGTH:
            self.errors.append(IdentifierTooLongError(
                len(identifier), MAX_IDENTIFIER_LENGTH, start_line, start_column
            ))

        # Проверяем, не является ли идентификатор ключевым словом
        if identifier in KEYWORDS:
            token_type = KEYWORDS[identifier]
            # Для true/false также добавляем литеральное значение
            if identifier in ('true', 'false'):
                literal = identifier == 'true'
                self._add_token(token_type, literal=literal)
            else:
                self._add_token(token_type)
        else:
            self._add_token(TokenType.IDENTIFIER)

    def _read_operator(self, first_char: str):
        """Читает оператор (включая двухсимвольные)"""
        # Сначала проверяем двухсимвольные операторы
        if first_char == '=' and self._match('='):
            self._add_token(TokenType.EQ_EQ, '==')
        elif first_char == '!' and self._match('='):
            self._add_token(TokenType.NOT_EQ, '!=')
        elif first_char == '<' and self._match('='):
            self._add_token(TokenType.LESS_EQ, '<=')
        elif first_char == '>' and self._match('='):
            self._add_token(TokenType.GREATER_EQ, '>=')
        elif first_char == '&' and self._match('&'):
            self._add_token(TokenType.AND_AND, '&&')
        elif first_char == '|' and self._match('|'):
            self._add_token(TokenType.OR_OR, '||')
        else:
            # Односимвольный оператор
            if first_char in OPERATORS:
                self._add_token(OPERATORS[first_char], first_char)
            else:
                # Если символ не найден в операторах, добавляем как INVALID
                error = InvalidCharacterError(first_char, self.line, self.column - 1)
                self.errors.append(error)
                self._add_token(TokenType.INVALID, first_char)

    def next_token(self) -> Token:
        """Возвращает следующий токен и продвигает указатель"""
        if not self.tokens:
            self.scan_tokens()

        if self.tokens:
            return self.tokens.pop(0)
        return Token(TokenType.END_OF_FILE, "", self.line, self.column)

    def peek_token(self) -> Token:
        """Возвращает следующий токен без продвижения"""
        if not self.tokens:
            self.scan_tokens()

        if self.tokens:
            return self.tokens[0]
        return Token(TokenType.END_OF_FILE, "", self.line, self.column)

    def get_line(self) -> int:
        return self.line

    def get_column(self) -> int:
        return self.column

    def get_errors(self) -> List[LexicalError]:
        return self.errors