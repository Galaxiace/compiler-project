#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Optional, List

# Импорты лексера
from .scanner import Scanner
from .token import Token, TokenType
from .errors import LexicalError

# Импорты парсера
from parser.parser import Parser, ParseError
from parser.pretty_printer import PrettyPrinter
from parser.dot_generator import DotGenerator
from parser.json_generator import JsonGenerator
from parser.ast import ProgramNode


def read_source_file(file_path: str) -> str:
    """
    Читает исходный файл.

    Args:
        file_path: Путь к файлу

    Returns:
        str: Содержимое файла
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def run_lexer(source: str, output_file: Optional[str] = None) -> List[Token]:
    """
    Запускает лексер на исходном коде.

    Args:
        source: Исходный код
        output_file: Файл для вывода токенов (опционально)

    Returns:
        List[Token]: Список токенов
    """
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Выводим ошибки лексера
    if scanner.errors:
        print("Найдены лексические ошибки:", file=sys.stderr)
        for error in scanner.errors:
            print(f"  {error}", file=sys.stderr)

    # Форматируем токены для вывода
    output_lines = []
    for token in tokens:
        if token.type == TokenType.END_OF_FILE:
            output_lines.append(f"{token.line}:{token.column} END_OF_FILE \"\"")
        else:
            literal_str = f" {token.literal}" if token.literal is not None else ""
            output_lines.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

    output = '\n'.join(output_lines)

    # Выводим результат
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Ошибка записи в файл {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    return tokens


def run_parser(tokens: List[Token], format_type: str, output_file: Optional[str] = None, verbose: bool = False):
    """
    Запускает парсер на списке токенов.

    Args:
        tokens: Список токенов
        format_type: Формат вывода (text, dot, json)
        output_file: Файл для вывода (опционально)
        verbose: Подробный вывод
    """
    parser = Parser(tokens)

    try:
        ast = parser.parse()
    except ParseError as e:
        print(f"Ошибка парсинга: {e}", file=sys.stderr)
        sys.exit(1)

    # Выводим ошибки парсера
    if parser.errors:
        print("Найдены синтаксические ошибки:", file=sys.stderr)
        for error in parser.errors:
            print(f"  {error}", file=sys.stderr)

    # Генерируем вывод в нужном формате
    output = None

    if format_type == "text":
        printer = PrettyPrinter()
        printer.visit(ast)
        output = printer.get_output()

        if verbose:
            # Добавляем статистику
            stats = [
                "",
                "=" * 50,
                "СТАТИСТИКА AST:",
                f"Всего узлов: {count_nodes(ast)}",
                f"Объявлений функций: {count_declarations(ast)}",
                "=" * 50
            ]
            output += "\n" + "\n".join(stats)

    elif format_type == "dot":
        generator = DotGenerator()
        output = generator.generate(ast)

    elif format_type == "json":
        generator = JsonGenerator()
        output = generator.generate(ast)

    # Выводим результат
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Ошибка записи в файл {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


def count_nodes(node) -> int:
    """
    Подсчитывает количество узлов в AST.

    Args:
        node: Узел AST

    Returns:
        int: Количество узлов
    """
    count = 1

    # Рекурсивно обходим дочерние узлы
    if hasattr(node, 'declarations'):
        for decl in node.declarations:
            count += count_nodes(decl)

    if hasattr(node, 'parameters'):
        for param in node.parameters:
            count += count_nodes(param)

    if hasattr(node, 'fields'):
        for field in node.fields:
            count += count_nodes(field)

    if hasattr(node, 'statements'):
        for stmt in node.statements:
            count += count_nodes(stmt)

    if hasattr(node, 'body'):
        count += count_nodes(node.body)

    if hasattr(node, 'then_branch'):
        count += count_nodes(node.then_branch)

    if hasattr(node, 'else_branch') and node.else_branch:
        count += count_nodes(node.else_branch)

    if hasattr(node, 'condition'):
        count += count_nodes(node.condition)

    if hasattr(node, 'init') and node.init:
        count += count_nodes(node.init)

    if hasattr(node, 'update') and node.update:
        count += count_nodes(node.update)

    if hasattr(node, 'value') and node.value:
        count += count_nodes(node.value)

    if hasattr(node, 'expression'):
        count += count_nodes(node.expression)

    if hasattr(node, 'initializer') and node.initializer:
        count += count_nodes(node.initializer)

    if hasattr(node, 'left'):
        count += count_nodes(node.left)

    if hasattr(node, 'right'):
        count += count_nodes(node.right)

    if hasattr(node, 'operand'):
        count += count_nodes(node.operand)

    if hasattr(node, 'callee'):
        count += count_nodes(node.callee)

    if hasattr(node, 'arguments'):
        for arg in node.arguments:
            count += count_nodes(arg)

    if hasattr(node, 'target'):
        count += count_nodes(node.target)

    return count


def count_declarations(node) -> int:
    """
    Подсчитывает количество объявлений в AST.

    Args:
        node: Узел AST

    Returns:
        int: Количество объявлений
    """
    if not hasattr(node, 'node_type'):
        return 0

    count = 0

    if node.node_type.name in ['FUNCTION_DECL', 'STRUCT_DECL', 'VAR_DECL']:
        count += 1

    # Рекурсивно обходим дочерние узлы
    if hasattr(node, 'declarations'):
        for decl in node.declarations:
            count += count_declarations(decl)

    if hasattr(node, 'statements'):
        for stmt in node.statements:
            count += count_declarations(stmt)

    if hasattr(node, 'body'):
        count += count_declarations(node.body)

    if hasattr(node, 'then_branch'):
        count += count_declarations(node.then_branch)

    if hasattr(node, 'else_branch') and node.else_branch:
        count += count_declarations(node.else_branch)

    return count


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description='MiniCompiler - Лексический анализатор и парсер',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Только лексический анализ
  compiler --input program.src --mode lex

  # Парсинг с выводом AST в текстовом формате
  compiler --input program.src --mode parse --ast-format text

  # Парсинг с генерацией DOT графа
  compiler --input program.src --mode parse --ast-format dot --output ast.dot

  # Преобразование DOT в PNG
  dot -Tpng ast.dot -o ast.png

  # Парсинг с JSON выводом для автоматического тестирования
  compiler --input program.src --mode parse --ast-format json --output ast.json

  # Подробный вывод с информацией об AST
  compiler --input program.src --mode parse --verbose
        """
    )

    parser.add_argument('--input', '-i', required=True, help='Входной файл с исходным кодом')
    parser.add_argument('--output', '-o', help='Выходной файл (по умолчанию stdout)')
    parser.add_argument('--mode', '-m', choices=['lex', 'parse'], default='lex',
                        help='Режим работы: lex - только лексер, parse - лексер + парсер (по умолчанию lex)')
    parser.add_argument('--ast-format', choices=['text', 'dot', 'json'], default='text',
                        help='Формат вывода AST для режима parse (по умолчанию text)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Подробный вывод (статистика AST и т.д.)')

    args = parser.parse_args()

    # Читаем входной файл
    source = read_source_file(args.input)

    if args.mode == 'lex':
        # Только лексический анализ
        run_lexer(source, args.output)
    else:
        # Лексический анализ + парсинг
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        # Выводим ошибки лексера
        if scanner.errors:
            print("Найдены лексические ошибки:", file=sys.stderr)
            for error in scanner.errors:
                print(f"  {error}", file=sys.stderr)

            # Если есть лексические ошибки, не запускаем парсер
            if args.verbose:
                print("\nОстановка из-за лексических ошибок", file=sys.stderr)
            sys.exit(1)

        # Запускаем парсер
        run_parser(tokens, args.ast_format, args.output, args.verbose)


if __name__ == '__main__':
    main()