#!/usr/bin/env python3
"""
Обновленный CLI с поддержкой семантического анализа и IR генерации.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

from ir import IROpcode
# Импорты лексера
from lexer.scanner import Scanner
from lexer.token import Token, TokenType
from lexer.errors import LexicalError

# Импорты парсера
from parser.parser import Parser, ParseError
from parser.pretty_printer import PrettyPrinter
from parser.dot_generator import DotGenerator
from parser.json_generator import JsonGenerator
from parser.ast import ProgramNode

# Импорты семантического анализатора
from semantic.analyzer import SemanticAnalyzer
from semantic.symbol_table import SymbolTable
from semantic.errors import SemanticError
from semantic.decorated_ast import DecoratedASTPrinter

# Импорты IR генератора
from ir.ir_generator import IRGenerator
from ir.ir_writer import IRWriter
from ir.dot_generator import IRDotGenerator
from ir.control_flow import IRProgram


def read_source_file(file_path: str) -> str:
    """Читает исходный файл."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def run_lexer(source: str, output_file: Optional[str] = None) -> List[Token]:
    """Запускает лексер на исходном коде."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    if scanner.errors:
        print("Найдены лексические ошибки:", file=sys.stderr)
        for error in scanner.errors:
            print(f"  {error}", file=sys.stderr)

    output_lines = []
    for token in tokens:
        if token.type == TokenType.END_OF_FILE:
            output_lines.append(f"{token.line}:{token.column} END_OF_FILE \"\"")
        else:
            literal_str = f" {token.literal}" if token.literal is not None else ""
            output_lines.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

    output = '\n'.join(output_lines)

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
    """Запускает парсер на списке токенов."""
    parser = Parser(tokens)

    try:
        ast = parser.parse()
    except ParseError as e:
        print(f"Ошибка парсинга: {e}", file=sys.stderr)
        sys.exit(1)

    if parser.errors:
        print("Найдены синтаксические ошибки:", file=sys.stderr)
        for error in parser.errors:
            print(f"  {error}", file=sys.stderr)

    if format_type == "text":
        printer = PrettyPrinter()
        printer.visit(ast)
        output = printer.get_output()

        if verbose:
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

    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Ошибка записи в файл {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    return ast


def run_semantic(ast: ProgramNode, output_file: Optional[str] = None,
                 verbose: bool = False, show_types: bool = False):
    """
    Запускает семантический анализ на AST.

    Args:
        ast: Корневой узел AST
        output_file: Файл для вывода
        verbose: Подробный вывод
        show_types: Показывать аннотации типов

    Returns:
        tuple: (success: bool, analyzer: SemanticAnalyzer, decorated_ast)
    """
    analyzer = SemanticAnalyzer()
    decorated_ast = analyzer.analyze(ast)

    errors = analyzer.get_errors()

    # Выводим ошибки
    if errors:
        print("Найдены семантические ошибки:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)

    # Формируем вывод
    output_lines = []

    # Таблица символов
    output_lines.append("=" * 60)
    output_lines.append("SYMBOL TABLE")
    output_lines.append("=" * 60)
    output_lines.append(analyzer.get_symbol_table().dump())
    output_lines.append("")

    # Декорированный AST с типами
    if show_types:
        output_lines.append("=" * 60)
        output_lines.append("DECORATED AST (with type annotations)")
        output_lines.append("=" * 60)

        printer = DecoratedASTPrinter()
        output_lines.append(printer.print(decorated_ast))
        output_lines.append("")

    # Отчет об ошибках
    output_lines.append("=" * 60)
    output_lines.append("VALIDATION REPORT")
    output_lines.append("=" * 60)
    output_lines.append(f"Total errors: {len(errors)}")

    if errors:
        output_lines.append("\nError list:")
        for i, error in enumerate(errors, 1):
            output_lines.append(f"  {i}. {error.message} [{error.line}:{error.column}]")

    output = "\n".join(output_lines)

    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Ошибка записи в файл {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    return len(errors) == 0, analyzer, decorated_ast


def run_ir(ast: ProgramNode, output_file: Optional[str] = None,
           format_type: str = "text", verbose: bool = False,
           optimize: bool = False, show_stats: bool = False,
           validate: bool = False):
    """
    Запускает IR генерацию на AST.
    """
    # Сначала выполняем семантический анализ
    analyzer = SemanticAnalyzer()
    decorated_ast = analyzer.analyze(ast)

    errors = analyzer.get_errors()
    if errors:
        print("Найдены семантические ошибки:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return False

    # Генерируем IR
    generator = IRGenerator(analyzer.get_symbol_table())
    generator.analyzer = analyzer
    ir_program = generator.generate_from_ast(ast)

    # Валидация IR
    if validate:
        from ir.validator import IRValidator
        validator = IRValidator()
        ir_errors, ir_warnings = validator.validate(ir_program)

        if ir_errors:
            print("Найдены ошибки в IR:", file=sys.stderr)
            for error in ir_errors:
                print(f"  ERROR: {error}", file=sys.stderr)

        if ir_warnings:
            print("Предупреждения IR:", file=sys.stderr)
            for warning in ir_warnings:
                print(f"  WARNING: {warning}", file=sys.stderr)

    # Применяем оптимизации если нужно
    if optimize:
        try:
            from ir.peephole_optimizer import PeepholeOptimizer
            optimizer = PeepholeOptimizer(ir_program)
            ir_program = optimizer.optimize()
            if verbose:
                print("Оптимизация IR выполнена", file=sys.stderr)
        except ImportError:
            if verbose:
                print("Оптимизатор не реализован (stretch goal)", file=sys.stderr)

    # Форматируем вывод
    if format_type == "dot":
        dot_gen = IRDotGenerator()
        output_parts = []
        for func in ir_program.functions:
            output_parts.append(f"// CFG for function: {func.name}")
            output_parts.append(dot_gen.generate_function(func))
            output_parts.append("")
        output = "\n".join(output_parts)
    elif format_type == "json":
        from ir.json_generator import IRJsonGenerator
        json_gen = IRJsonGenerator()
        output = json_gen.generate(ir_program)
    else:  # text
        writer = IRWriter()
        output = writer.write_program(ir_program)

    # Добавляем статистику если нужно
    if show_stats:
        stats = generate_ir_stats(ir_program)
        output = stats + "\n" + output

    # Добавляем verbose информацию
    if verbose:
        header = [
            "#" + "=" * 60,
            f"# IR GENERATION REPORT",
            f"# Generated functions: {len(ir_program.functions)}",
            f"# Global variables: {len(ir_program.global_vars)}",
            "#" + "=" * 60,
            ""
        ]
        output = "\n".join(header) + "\n" + output

    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Ошибка записи в файл {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    return True


# В функции generate_ir_stats добавить:

def generate_ir_stats(ir_program: IRProgram) -> str:
    """Генерирует статистику по IR программе."""
    lines = []
    lines.append("=" * 60)
    lines.append("IR STATISTICS")
    lines.append("=" * 60)

    total_instructions = 0
    instruction_counts = {}
    total_blocks = 0
    total_temporaries = 0
    max_stack_depth = 0

    for func in ir_program.functions:
        total_blocks += len(func.blocks)
        total_temporaries += func.temp_counter

        # Считаем максимальную глубину стека (количество ALLOCA)
        func_stack_depth = 0
        for block in func.blocks:
            for instr in block.instructions:
                total_instructions += 1
                opcode = instr.opcode.name
                instruction_counts[opcode] = instruction_counts.get(opcode, 0) + 1
                if instr.opcode == IROpcode.ALLOCA:
                    func_stack_depth += 1

        max_stack_depth = max(max_stack_depth, func_stack_depth)

    lines.append(f"Total functions:      {len(ir_program.functions)}")
    lines.append(f"Total basic blocks:   {total_blocks}")
    lines.append(f"Total instructions:   {total_instructions}")
    lines.append(f"Total temporaries:    {total_temporaries}")
    lines.append(f"Max stack depth:      {max_stack_depth}")
    lines.append("")
    lines.append("Instructions by type:")

    for opcode, count in sorted(instruction_counts.items(), key=lambda x: -x[1]):
        percentage = (count / total_instructions * 100) if total_instructions > 0 else 0
        lines.append(f"  {opcode:20} {count:5} ({percentage:5.1f}%)")

    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)


def count_nodes(node) -> int:
    """Подсчитывает количество узлов в AST."""
    count = 1

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
    """Подсчитывает количество объявлений в AST."""
    if not hasattr(node, 'node_type'):
        return 0

    count = 0
    if node.node_type.name in ['FUNCTION_DECL', 'STRUCT_DECL', 'VAR_DECL']:
        count += 1

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
        description='MiniCompiler - Лексический анализатор, парсер, семантический анализатор и IR генератор',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Только лексический анализ
  compiler --input program.src --mode lex

  # Парсинг с выводом AST в текстовом формате
  compiler --input program.src --mode parse --ast-format text

  # Семантический анализ
  compiler --input program.src --mode semantic

  # Семантический анализ с показом типов
  compiler --input program.src --mode semantic --show-types

  # Генерация IR
  compiler --input program.src --mode ir

  # Генерация IR с выводом в файл
  compiler --input program.src --mode ir --output program.ir

  # Генерация CFG в формате DOT
  compiler --input program.src --mode ir --ir-format dot --output cfg.dot

  # Генерация IR со статистикой
  compiler --input program.src --mode ir --stats

  # Генерация IR с оптимизацией
  compiler --input program.src --mode ir --optimize --stats

  # Полный pipeline с подробным выводом
  compiler --input program.src --mode ir --verbose
        """
    )

    parser.add_argument('--input', '-i', required=True, help='Входной файл с исходным кодом')
    parser.add_argument('--output', '-o', help='Выходной файл (по умолчанию stdout)')
    parser.add_argument('--mode', '-m', choices=['lex', 'parse', 'semantic', 'ir'], default='lex',
                        help='Режим работы: lex - лексер, parse - парсер, semantic - семантика, ir - IR генерация')
    parser.add_argument('--ast-format', choices=['text', 'dot', 'json'], default='text',
                        help='Формат вывода AST для режима parse (по умолчанию text)')
    parser.add_argument('--ir-format', choices=['text', 'dot', 'json'], default='text',
                        help='Формат вывода IR (по умолчанию text)')
    parser.add_argument('--validate', action='store_true',
                        help='Проверять валидность IR')
    parser.add_argument('--show-types', action='store_true',
                        help='Показывать аннотации типов в декорированном AST')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Подробный вывод (статистика AST, IR и т.д.)')
    parser.add_argument('--optimize', action='store_true',
                        help='Применять оптимизации к IR (stretch goal)')
    parser.add_argument('--stats', action='store_true',
                        help='Выводить статистику IR')

    args = parser.parse_args()

    source = read_source_file(args.input)

    if args.mode == 'lex':
        run_lexer(source, args.output)

    elif args.mode == 'parse':
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        if scanner.errors:
            print("Найдены лексические ошибки:", file=sys.stderr)
            for error in scanner.errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

        run_parser(tokens, args.ast_format, args.output, args.verbose)

    elif args.mode == 'semantic':
        # Лексический анализ
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        if scanner.errors:
            print("Найдены лексические ошибки:", file=sys.stderr)
            for error in scanner.errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

        # Синтаксический анализ
        parser_obj = Parser(tokens)
        ast = parser_obj.parse()

        if parser_obj.errors:
            print("Найдены синтаксические ошибки:", file=sys.stderr)
            for error in parser_obj.errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

        # Семантический анализ
        success, _, _ = run_semantic(ast, args.output, args.verbose, args.show_types)
        sys.exit(0 if success else 1)

    elif args.mode == 'ir':
        # Лексический анализ
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        if scanner.errors:
            print("Найдены лексические ошибки:", file=sys.stderr)
            for error in scanner.errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

        # Синтаксический анализ
        parser_obj = Parser(tokens)
        ast = parser_obj.parse()

        if parser_obj.errors:
            print("Найдены синтаксические ошибки:", file=sys.stderr)
            for error in parser_obj.errors:
                print(f"  {error}", file=sys.stderr)
            sys.exit(1)

        # IR генерация
        success = run_ir(
            ast,
            args.output,
            args.ir_format,
            args.verbose,
            args.optimize,
            args.stats
        )
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()