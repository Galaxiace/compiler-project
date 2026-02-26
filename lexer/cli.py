#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from .scanner import Scanner
from .token import TokenType


def main():
    parser = argparse.ArgumentParser(description='MiniCompiler Lexer')
    parser.add_argument('--input', '-i', required=True, help='Input source file')
    parser.add_argument('--output', '-o', help='Output tokens file (default: stdout)')

    args = parser.parse_args()

    # Читаем входной файл
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Сканируем токены
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Выводим ошибки, если есть
    if scanner.errors:
        print("Lexical errors found:", file=sys.stderr)
        for error in scanner.errors:
            print(f"  {error}", file=sys.stderr)

    # Подготавливаем вывод в формате LINE:COLUMN_TOKEN_TYPE
    output_lines = []
    for token in tokens:
        if token.type == TokenType.END_OF_FILE:
            output_lines.append(f"{token.line}:{token.column}_END_OF_FILE \"\"")
        else:
            literal_str = f" {token.literal}" if token.literal is not None else ""
            output_lines.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

    output = '\n'.join(output_lines)

    # Выводим результат
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == '__main__':
    main()