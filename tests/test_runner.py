#!/usr/bin/env python3
import os
import sys
import difflib
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from lexer.token import TokenType

TEST_DIR = Path(__file__).parent / "lexer"
VALID_DIR = TEST_DIR / "valid"
INVALID_DIR = TEST_DIR / "invalid"


def format_token(token):
    """Форматирует токен для вывода и сравнения"""
    if token.type == TokenType.END_OF_FILE:
        return f"{token.line}:{token.column} END_OF_FILE \"\""
    else:
        literal = f" {token.literal}" if token.literal is not None else ""
        return f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal}"


def run_test(src_file, expected_file):
    """Запускает лексер на src_file и сравнивает с expected_file"""
    print(f"  Testing {src_file.name}...", end=" ")

    # Читаем исходный код
    with open(src_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # Сканируем токены
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Форматируем вывод используя ту же функцию, что и при генерации
    actual_lines = [format_token(token) for token in tokens]

    # Читаем ожидаемый вывод
    with open(expected_file, 'r', encoding='utf-8') as f:
        expected_lines = [line.rstrip() for line in f]

    # Сравниваем
    if actual_lines == expected_lines:
        print(" PASSED")
        return True, None
    else:
        print(" FAILED")
        diff = difflib.unified_diff(
            expected_lines, actual_lines,
            fromfile=str(expected_file),
            tofile="<actual>",
            lineterm=""
        )
        return False, '\n'.join(diff)


def main():
    print("\n" + "=" * 60)
    print("ЗАПУСК ТЕСТОВ ЛЕКСЕРА")
    print("=" * 60)

    passed = 0
    failed = 0
    failed_tests = []

    # Тестируем валидные файлы
    print("\n ВАЛИДНЫЕ ТЕСТЫ:")
    for src_file in sorted(VALID_DIR.glob("*.src")):
        expected_file = src_file.with_suffix('.expected')
        if not expected_file.exists():
            print(f"  {src_file.name}...   НЕТ .expected ФАЙЛА")
            failed += 1
            failed_tests.append(f"{src_file.name} (нет .expected)")
            continue

        ok, diff = run_test(src_file, expected_file)
        if ok:
            passed += 1
        else:
            failed += 1
            failed_tests.append(f"{src_file.name}")
            if diff:
                print(f"\n{diff}\n")

    # Тестируем невалидные файлы
    print("\n НЕВАЛИДНЫЕ ТЕСТЫ:")
    for src_file in sorted(INVALID_DIR.glob("*.src")):
        expected_file = src_file.with_suffix('.expected')
        if not expected_file.exists():
            print(f"  {src_file.name}...   НЕТ .expected ФАЙЛА")
            failed += 1
            failed_tests.append(f"{src_file.name} (нет .expected)")
            continue

        ok, diff = run_test(src_file, expected_file)
        if ok:
            passed += 1
        else:
            failed += 1
            failed_tests.append(f"{src_file.name}")
            if diff:
                print(f"\n{diff}\n")

    # Итоги
    print("\n" + "=" * 60)
    print(f"ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"  PASSED: {passed}")
    print(f"  FAILED: {failed}")
    if failed_tests:
        print(f"\nПроваленные тесты:")
        for test in failed_tests:
            print(f"  - {test}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())