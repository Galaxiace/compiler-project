"""
Тесты для сравнения вывода лексера с ожидаемыми файлами.
Сравнивает .src файлы с соответствующими .expected файлами.
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from lexer.token import TokenType


def normalize_output(output):
    """
    Нормализует вывод для сравнения.
    Убирает различия в:
    - символах конца строки (\r\n vs \n)
    - пробелах в конце строк
    - пустых строках в конце файла
    """
    # Убираем \r, затем разбиваем на строки
    lines = output.replace('\r', '').split('\n')

    # Убираем пробелы в конце каждой строки
    lines = [line.rstrip() for line in lines]

    # Убираем пустые строки в конце
    while lines and not lines[-1]:
        lines.pop()

    # Собираем обратно с одним переводом строки в конце
    return '\n'.join(lines) + '\n'


def compare_with_expected(source_file, expected_file):
    """
    Сравнивает вывод лексера для source_file с содержимым expected_file.

    Args:
        source_file: Path к .src файлу с исходным кодом
        expected_file: Path к .expected файлу с ожидаемым выводом
    """
    # Читаем исходный код
    with open(source_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # Сканируем токены
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Форматируем вывод как в спецификации
    actual_output = []
    for token in tokens:
        if token.type == TokenType.END_OF_FILE:
            actual_output.append(f"{token.line}:{token.column} END_OF_FILE \"\"")
        else:
            literal_str = f" {token.literal}" if token.literal is not None else ""
            actual_output.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

    # Нормализуем фактический вывод
    actual_output = normalize_output('\n'.join(actual_output))

    # Читаем ожидаемый вывод
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_output = normalize_output(f.read())

    # Подробный вывод при ошибке
    if actual_output != expected_output:
        print(f"\n{'=' * 60}")
        print(f"❌ ОШИБКА В ФАЙЛЕ: {source_file.name}")
        print(f"{'=' * 60}")

        # Показываем первые несколько символов для диагностики
        print(f"\nПервые 50 символов ожидаемого вывода:")
        print(repr(expected_output[:50]))
        print(f"\nПервые 50 символов фактического вывода:")
        print(repr(actual_output[:50]))

        # Разбиваем на строки для построчного сравнения
        actual_lines = actual_output.split('\n')
        expected_lines = expected_output.split('\n')

        print(f"\n{'=' * 60}")
        print(f"ПОСТРОЧНОЕ СРАВНЕНИЕ:")
        print(f"{'=' * 60}")

        max_lines = max(len(actual_lines), len(expected_lines))
        for i in range(max_lines):
            actual_line = actual_lines[i] if i < len(actual_lines) else "<нет строки>"
            expected_line = expected_lines[i] if i < len(expected_lines) else "<нет строки>"

            if actual_line != expected_line:
                print(f"\nСтрока {i + 1}:")
                print(f"  Ожидалось: {repr(expected_line)}")
                print(f"  Получено:  {repr(actual_line)}")

                # Показываем позицию различия
                min_len = min(len(actual_line), len(expected_line))
                for j in range(min_len):
                    if j >= len(actual_line) or j >= len(expected_line) or actual_line[j] != expected_line[j]:
                        print(f"  Различие на позиции {j}:")
                        print(f"    Ожидалось: {repr(expected_line[j])} (код {ord(expected_line[j])})")
                        print(f"    Получено:  {repr(actual_line[j])} (код {ord(actual_line[j])})")
                        break

        print(f"\n{'=' * 60}")

        # Если есть ошибки лексера, покажем их
        if scanner.errors:
            print(f"\nОШИБКИ ЛЕКСЕРА:")
            for error in scanner.errors:
                print(f"  {error}")
            print(f"\n{'=' * 60}")

    # Сравниваем
    assert actual_output == expected_output, \
        f"\nФайл: {source_file}\n" \
        f"Ожидалось:\n{expected_output}\n" \
        f"Получено:\n{actual_output}"


# ========== ВАЛИДНЫЕ ТЕСТЫ ==========

def test_valid_basic():
    """Сравнение test_basic.src с ожидаемым выводом"""
    source = Path(__file__).parent / "lexer" / "valid" / "test_basic.src"
    expected = Path(__file__).parent / "lexer" / "valid" / "test_basic.expected"

    # Проверяем, что файлы существуют
    assert source.exists(), f"Файл не найден: {source}"
    assert expected.exists(), f"Файл не найден: {expected}"

    compare_with_expected(source, expected)


def test_valid_operators():
    """Сравнение test_operators.src с ожидаемым выводом"""
    source = Path(__file__).parent / "lexer" / "valid" / "test_operators.src"
    expected = Path(__file__).parent / "lexer" / "valid" / "test_operators.expected"

    assert source.exists(), f"Файл не найден: {source}"
    assert expected.exists(), f"Файл не найден: {expected}"

    compare_with_expected(source, expected)


# ========== НЕВАЛИДНЫЕ ТЕСТЫ ==========

def test_invalid_char():
    """Сравнение test_invalid_char.src с ожидаемым выводом"""
    source = Path(__file__).parent / "lexer" / "invalid" / "test_invalid_char.src"
    expected = Path(__file__).parent / "lexer" / "invalid" / "test_invalid_char.expected"

    assert source.exists(), f"Файл не найден: {source}"
    assert expected.exists(), f"Файл не найден: {expected}"

    compare_with_expected(source, expected)


def test_unterminated_string():
    """Сравнение test_unterminated_string.src с ожидаемым выводом"""
    source = Path(__file__).parent / "lexer" / "invalid" / "test_unterminated_string.src"
    expected = Path(__file__).parent / "lexer" / "invalid" / "test_unterminated_string.expected"

    assert source.exists(), f"Файл не найден: {source}"
    assert expected.exists(), f"Файл не найден: {expected}"

    # Для отладки покажем содержимое файлов
    print(f"\n{'=' * 60}")
    print(f"ТЕСТ: test_unterminated_string")
    print(f"{'=' * 60}")

    with open(source, 'r', encoding='utf-8') as f:
        source_content = f.read()
    print(f"Исходный код ({source}):")
    print(repr(source_content))

    with open(expected, 'r', encoding='utf-8') as f:
        expected_content = f.read()
    print(f"\nОжидаемый вывод ({expected}):")
    print(repr(expected_content))
    print(f"{'=' * 60}\n")

    compare_with_expected(source, expected)


# ========== ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ==========

def test_all_expected_files_exist():
    """Проверяет, что для всех .src файлов есть соответствующие .expected файлы"""
    tests_dir = Path(__file__).parent / "lexer"

    for category in ['valid', 'invalid']:
        category_dir = tests_dir / category
        if category_dir.exists():
            for src_file in category_dir.glob("*.src"):
                expected_file = src_file.with_suffix('.expected')
                assert expected_file.exists(), \
                    f"Для файла {src_file} нет соответствующего .expected файла"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])