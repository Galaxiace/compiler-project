"""Дополнительные тесты для парсера (граничные случаи)"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lexer.scanner import Scanner
from parser.parser import Parser

def parse_source(source):
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    return parser.parse()

class TestParserExtra:
    def test_empty_program(self):
        ast = parse_source("")
        assert len(ast.declarations) == 0

    def test_multiple_functions(self):
        source = """
        fn foo() -> int { return 1; }
        fn bar() -> int { return 2; }
        """
        ast = parse_source(source)
        funcs = [d for d in ast.declarations if hasattr(d, 'name')]
        assert len(funcs) == 2

    def test_nested_blocks(self):
        source = """
        fn main() -> int {
            if (true) {
                while (true) {
                    return 0;
                }
            }
            return 1;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_for_loop_empty(self):
        source = """
        fn main() -> int {
            for (;;) {
                return 0;
            }
            return 1;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_logical_operators(self):
        source = """
        fn main() -> int {
            bool a = true;
            bool b = false;
            bool c = a && b;
            bool d = a || b;
            return 0;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_bitwise_operators(self):
        source = """
        fn main() -> int {
            int a = 5 & 3;
            int b = 5 | 3;
            int c = 5 ^ 3;
            return a + b + c;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_complex_expression(self):
        source = """
        fn main() -> int {
            int x = (1 + 2) * (3 - 4) / 5;
            return x;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_cast_expression(self):
        source = """
        fn main() -> int {
            int x = (int) 3.14;
            return x;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_array_access(self):
        source = """
        fn main() -> int {
            int arr[10];
            arr[0] = 42;
            return arr[0];
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_struct_field_access(self):
        source = """
        struct Point { int x; int y; }
        fn main() -> int {
            struct Point p;
            p.x = 10;
            p.y = 20;
            return p.x + p.y;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 2

    def test_extern_variadic(self):
        source = 'extern int printf(int fmt, ...);'
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_compound_assignment(self):
        source = """
        fn main() -> int {
            int x = 10;
            x += 5;
            x -= 3;
            x *= 2;
            x /= 4;
            x %= 3;
            return x;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1

    def test_unary_operators(self):
        source = """
        fn main() -> int {
            int x = 5;
            int y = -x;
            bool flag = !true;
            return y;
        }
        """
        ast = parse_source(source)
        assert len(ast.declarations) == 1
