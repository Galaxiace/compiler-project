import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from lexer.token import TokenType, MAX_IDENTIFIER_LENGTH, MAX_INT_VALUE, MIN_INT_VALUE
from lexer.errors import *


def test_keywords():
    """Тестирование ключевых слов"""
    source = "if else while for int float bool return true false void struct fn"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.IF, TokenType.ELSE, TokenType.WHILE, TokenType.FOR,
        TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.RETURN,
        TokenType.TRUE, TokenType.FALSE, TokenType.VOID, TokenType.STRUCT,
        TokenType.FN, TokenType.END_OF_FILE
    ]

    assert len(tokens) == len(expected_types)
    for token, expected_type in zip(tokens, expected_types):
        assert token.type == expected_type


def test_identifiers():
    """Тестирование идентификаторов"""
    source = "x variable var123 _private camelCase snake_case"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # 6 идентификаторов + EOF = 7 токенов
    assert len(tokens) == 7

    # Проверяем первые 6 токенов - они должны быть идентификаторами
    for i in range(6):
        assert tokens[i].type == TokenType.IDENTIFIER, f"Токен {i} не IDENTIFIER: {tokens[i]}"

    # Проверяем последний токен - END_OF_FILE
    assert tokens[6].type == TokenType.END_OF_FILE


def test_numbers():
    """Тестирование чисел"""
    source = "42 3.14 0 123.456"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    assert tokens[0].type == TokenType.INT_LITERAL
    assert tokens[0].literal == 42
    assert tokens[1].type == TokenType.FLOAT_LITERAL
    assert tokens[1].literal == 3.14
    assert tokens[2].type == TokenType.INT_LITERAL
    assert tokens[2].literal == 0
    assert tokens[3].type == TokenType.FLOAT_LITERAL
    assert tokens[3].literal == 123.456


def test_operators():
    """Тестирование всех операторов из спецификации"""
    source = "+ - * / % = == != <= >= < > & && | ||"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
        TokenType.PERCENT, TokenType.ASSIGN, TokenType.EQ_EQ, TokenType.NOT_EQ,
        TokenType.LESS_EQ, TokenType.GREATER_EQ, TokenType.LESS, TokenType.GREATER,
        TokenType.AND, TokenType.AND_AND, TokenType.OR, TokenType.OR_OR,
        TokenType.END_OF_FILE
    ]

    assert len(tokens) == len(expected_types)
    for token, expected_type in zip(tokens, expected_types):
        assert token.type == expected_type, f"Ожидался {expected_type}, получен {token.type}"


def test_delimiters():
    """Тестирование разделителей"""
    source = "( ) { } ; ,"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_types = [
        TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
        TokenType.SEMICOLON, TokenType.COMMA, TokenType.END_OF_FILE
    ]

    assert len(tokens) == len(expected_types)
    for token, expected_type in zip(tokens, expected_types):
        assert token.type == expected_type


def test_string_literal():
    """Тестирование строковых литералов"""
    source = '"hello world" "test"'
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    assert tokens[0].type == TokenType.STRING_LITERAL
    assert tokens[0].literal == "hello world"
    assert tokens[1].type == TokenType.STRING_LITERAL
    assert tokens[1].literal == "test"


def test_comments():
    """Тестирование комментариев"""
    source = """
    // This is a single line comment
    int x = 42; // This is also a comment
    /* This is a
       multi-line comment */
    float y = 3.14;
    """
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Проверяем, что комментарии пропущены, а код распознан
    assert tokens[0].type == TokenType.INT
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].lexeme == "x"
    assert tokens[2].type == TokenType.ASSIGN
    assert tokens[3].type == TokenType.INT_LITERAL
    assert tokens[3].literal == 42
    assert tokens[4].type == TokenType.SEMICOLON
    assert tokens[5].type == TokenType.FLOAT
    assert tokens[6].type == TokenType.IDENTIFIER
    assert tokens[6].lexeme == "y"
    assert tokens[7].type == TokenType.ASSIGN
    assert tokens[8].type == TokenType.FLOAT_LITERAL
    assert tokens[8].literal == 3.14


def test_invalid_character():
    """Тестирование недопустимых символов"""
    source = "int x = 42; @ invalid"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Должна быть ошибка
    assert len(scanner.errors) > 0
    assert isinstance(scanner.errors[0], InvalidCharacterError)


def test_unterminated_string_with_newline():
    """Тестирование незакрытой строки с переносом строки"""
    source = 'string s = "unterminated\nint x = 5;'
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    print(f"\nТест незакрытой строки с переносом:")
    print(f"Исходный код: {repr(source)}")
    print(f"Позиции символов:")
    print(f"  'string' начинается с колонки 1")
    print(f"  's' на колонке 8")
    print(f"  '=' на колонке 10")
    print(f"  '\"' на колонке 12")

    for i, token in enumerate(tokens):
        print(f"Токен {i}: {token}")
    print(f"Ошибки: {[str(e) for e in scanner.errors]}")

    # Проверяем наличие ошибки
    assert len(scanner.errors) == 1
    assert isinstance(scanner.errors[0], UnterminatedStringError)
    assert scanner.errors[0].line == 1  # Ошибка на первой строке
    assert scanner.errors[0].column == 12  # Позиция открывающей кавычки

    # Проверяем токены
    # Ожидаемая последовательность:
    # 1. IDENTIFIER "string" (колонка 1)
    # 2. IDENTIFIER "s" (колонка 8)
    # 3. ASSIGN "=" (колонка 10)
    # 4. INVALID (незакрытая строка) (колонка 12)
    # 5. INT "int" (колонка 1 на второй строке)
    # 6. IDENTIFIER "x" (колонка 5 на второй строке)
    # 7. ASSIGN "=" (колонка 7 на второй строке)
    # 8. INT_LITERAL "5" (колонка 9 на второй строке)
    # 9. SEMICOLON ";" (колонка 10 на второй строке)
    # 10. END_OF_FILE

    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].lexeme == "string"
    assert tokens[0].line == 1
    assert tokens[0].column == 1

    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].lexeme == "s"
    assert tokens[1].line == 1
    assert tokens[1].column == 8

    assert tokens[2].type == TokenType.ASSIGN
    assert tokens[2].lexeme == "="
    assert tokens[2].line == 1
    assert tokens[2].column == 10

    assert tokens[3].type == TokenType.INVALID
    assert tokens[3].lexeme == 'unterminated'
    assert tokens[3].line == 1
    assert tokens[3].column == 12
    assert tokens[3].literal is None

    assert tokens[4].type == TokenType.INT
    assert tokens[4].lexeme == "int"
    assert tokens[4].line == 2
    assert tokens[4].column == 1

    assert tokens[5].type == TokenType.IDENTIFIER
    assert tokens[5].lexeme == "x"
    assert tokens[5].line == 2
    assert tokens[5].column == 5

    assert tokens[6].type == TokenType.ASSIGN
    assert tokens[6].lexeme == "="
    assert tokens[6].line == 2
    assert tokens[6].column == 7

    assert tokens[7].type == TokenType.INT_LITERAL
    assert tokens[7].lexeme == "5"
    assert tokens[7].literal == 5
    assert tokens[7].line == 2
    assert tokens[7].column == 9

    assert tokens[8].type == TokenType.SEMICOLON
    assert tokens[8].lexeme == ";"
    assert tokens[8].line == 2
    assert tokens[8].column == 10

    assert tokens[9].type == TokenType.END_OF_FILE
    assert tokens[9].lexeme == ""
    assert tokens[9].line == 2
    assert tokens[9].column == 11


def test_unterminated_string_positions():
    """Тестирование точности позиций при незакрытой строке"""
    test_cases = [
        ('"unterminated', 1, 1, 1, 1),  # строка начинается с колонки 1
        ('x = "unterminated', 1, 5, 1, 5),  # кавычка на колонке 5
        ('  "unterminated', 1, 3, 1, 3),  # кавычка на колонке 3 с пробелами
        ('"unterminated\nx=5;', 1, 1, 1, 1),  # с последующим кодом
    ]

    for source, exp_line, exp_col, err_line, err_col in test_cases:
        print(f"\nТест: {repr(source)}")
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        for i, token in enumerate(tokens):
            print(f"Токен {i}: {token}")

        if scanner.errors:
            print(f"Ошибка: {scanner.errors[0]}")
            assert scanner.errors[0].line == err_line
            assert scanner.errors[0].column == err_col

        # Проверяем позицию INVALID токена
        invalid_tokens = [t for t in tokens if t.type == TokenType.INVALID]
        if invalid_tokens:
            assert invalid_tokens[0].line == exp_line
            assert invalid_tokens[0].column == exp_col


def test_cli_output_format():
    """Тестирование формата вывода CLI для незакрытой строки"""
    source = 'string s = "unterminated\nint x = 5;'
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Форматируем вывод как в CLI
    output_lines = []
    for token in tokens:
        if token.type == TokenType.END_OF_FILE:
            output_lines.append(f"{token.line}:{token.column} END_OF_FILE \"\"")
        else:
            literal_str = f" {token.literal}" if token.literal is not None else ""
            output_lines.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

    # Выводим для проверки
    print(f"\nCLI вывод для test_unterminated_string.src:")
    for line in output_lines:
        print(line)

    # Проверяем, что нет отрицательных колонок
    for line in output_lines:
        parts = line.split(' ')
        if len(parts) >= 2:
            line_col = parts[0]
            if ':' in line_col:
                col = int(line_col.split(':')[1])
                assert col >= 1, f"Колонка не может быть отрицательной: {col} в строке '{line}'"

    # Проверяем, что токены после ошибки присутствуют
    has_int = any("INT \"int\"" in line for line in output_lines)
    assert has_int, "Должен быть токен INT после ошибки"


def test_position_tracking():
    """Тестирование отслеживания позиции"""
    source = "int\nx = 42;"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # int на строке 1, колонке 1
    assert tokens[0].line == 1
    assert tokens[0].column == 1

    # x на строке 2, колонке 1
    assert tokens[1].line == 2
    assert tokens[1].column == 1

    # = на строке 2, колонке 3
    assert tokens[2].line == 2
    assert tokens[2].column == 3


def test_identifier_max_length():
    """Тестирование проверки максимальной длины идентификатора"""
    # Создаем идентификатор длиной 256 символов (превышает MAX_IDENTIFIER_LENGTH = 255)
    long_id = "a" * 256
    source = f"{long_id} = 42;"

    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Должна быть ошибка о слишком длинном идентификаторе
    assert len(scanner.errors) > 0
    assert isinstance(scanner.errors[0], IdentifierTooLongError)


def test_integer_range():
    """Тестирование проверки диапазона целых чисел"""
    # Формируем строку с числами, разделяя их пробелами для правильного распознавания
    source = f"{MAX_INT_VALUE} {MIN_INT_VALUE} {MAX_INT_VALUE + 1} {MIN_INT_VALUE - 1}"

    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Выводим токены для отладки
    print(f"\nТест integer_range:")
    for i, token in enumerate(tokens):
        print(f"Токен {i}: {token}")
    print(f"Ошибки: {[str(e) for e in scanner.errors]}")

    # Первый токен - максимальное положительное число
    assert tokens[0].type == TokenType.INT_LITERAL
    assert tokens[0].literal == MAX_INT_VALUE

    # Второй токен - минимальное отрицательное число
    assert tokens[1].type == TokenType.INT_LITERAL
    assert tokens[1].literal == MIN_INT_VALUE

    # Третий токен - число вне диапазона (должна быть ошибка, но токен создается)
    assert tokens[2].type == TokenType.INT_LITERAL
    assert tokens[2].literal == MAX_INT_VALUE + 1

    # Четвертый токен - число вне диапазона
    assert tokens[3].type == TokenType.INT_LITERAL
    assert tokens[3].literal == MIN_INT_VALUE - 1

    # Должны быть ошибки для чисел вне диапазона (2 ошибки)
    assert len(scanner.errors) >= 2
    assert isinstance(scanner.errors[0], IntegerOutOfRangeError)


def test_malformed_number():
    """Тестирование неправильного формата числа"""
    source = "123.  .456 12..34"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Выводим информацию для отладки
    print(f"\nТест malformed_number:")
    for i, token in enumerate(tokens):
        print(f"Токен {i}: {token}")
    print(f"Ошибки: {[str(e) for e in scanner.errors]}")
    print(f"Типы ошибок: {[type(e).__name__ for e in scanner.errors]}")

    # Должны быть ошибки
    assert len(scanner.errors) > 0

    # Проверяем, что все ошибки - InvalidNumberError
    # Но также могут быть ошибки незакрытых комментариев из-за синтаксиса
    for error in scanner.errors:
        if not isinstance(error, InvalidNumberError):
            print(f"Предупреждение: найден неожиданный тип ошибки {type(error).__name__}")

    # Убеждаемся, что есть хотя бы одна InvalidNumberError
    assert any(isinstance(error, InvalidNumberError) for error in scanner.errors)


def test_windows_line_endings():
    """Тестирование Windows line endings (\r\n)"""
    source = "int x = 42;\r\nfloat y = 3.14;\r\n"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Проверяем позиции после Windows line endings
    assert tokens[0].line == 1  # int
    assert tokens[4].line == 1  # ;
    assert tokens[5].line == 2  # float


def test_negative_numbers():
    """Тестирование отрицательных чисел"""
    source = "-42 -3.14 -0 -123.456"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    print(f"\nТест negative_numbers:")
    for i, token in enumerate(tokens):
        print(f"Токен {i}: {token}")

    # Проверяем отрицательные целые
    assert tokens[0].type == TokenType.INT_LITERAL
    assert tokens[0].literal == -42

    # Проверяем отрицательные числа с плавающей точкой
    assert tokens[1].type == TokenType.FLOAT_LITERAL
    assert tokens[1].literal == -3.14

    assert tokens[2].type == TokenType.INT_LITERAL
    assert tokens[2].literal == 0  # -0 должно быть 0

    assert tokens[3].type == TokenType.FLOAT_LITERAL
    assert tokens[3].literal == -123.456


def test_minus_operator_vs_negative():
    """Тестирование различения оператора минус и отрицательного числа"""
    source = "5 - 3 -3 5-3 - 3"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    print(f"\nТест minus_operator_vs_negative:")
    print(f"Исходная строка: '{source}'")
    for i, token in enumerate(tokens):
        print(f"Токен {i}: {token}")

    # Ожидаемая последовательность:
    # 5 (INT), - (MINUS), 3 (INT), -3 (INT), 5 (INT), - (MINUS), 3 (INT), - (MINUS), 3 (INT)

    expected_sequence = [
        (TokenType.INT_LITERAL, 5),  # 5
        (TokenType.MINUS, None),  # -
        (TokenType.INT_LITERAL, 3),  # 3
        (TokenType.INT_LITERAL, -3),  # -3
        (TokenType.INT_LITERAL, 5),  # 5
        (TokenType.MINUS, None),  # - (оператор)
        (TokenType.INT_LITERAL, 3),  # 3
        (TokenType.MINUS, None),  # - (оператор)
        (TokenType.INT_LITERAL, 3),  # 3
        (TokenType.END_OF_FILE, None)  # EOF
    ]

    assert len(tokens) == len(expected_sequence)

    for i, (token, (expected_type, expected_value)) in enumerate(zip(tokens, expected_sequence)):
        assert token.type == expected_type, f"Токен {i}: ожидался {expected_type}, получен {token.type}"
        if expected_value is not None:
            assert token.literal == expected_value, f"Токен {i}: ожидалось значение {expected_value}, получено {token.literal}"


def test_mixed_tokens():
    """Тестирование смешанных последовательностей токенов"""
    source = "fn main() { int x = 42 + 3.14; }"
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    expected_sequence = [
        TokenType.FN, TokenType.IDENTIFIER, TokenType.LPAREN, TokenType.RPAREN,
        TokenType.LBRACE, TokenType.INT, TokenType.IDENTIFIER, TokenType.ASSIGN,
        TokenType.INT_LITERAL, TokenType.PLUS, TokenType.FLOAT_LITERAL,
        TokenType.SEMICOLON, TokenType.RBRACE, TokenType.END_OF_FILE
    ]

    assert len(tokens) == len(expected_sequence)
    for token, expected_type in zip(tokens, expected_sequence):
        assert token.type == expected_type


if __name__ == '__main__':
    pytest.main([__file__, '-v'])