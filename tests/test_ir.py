# tests/test_ir.py
"""
Тесты для IR генерации.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir import IRGenerator, IRWriter, IRValidator


def generate_ir(source: str):
    """Вспомогательная функция для генерации IR из исходного кода."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    assert len(scanner.errors) == 0, f"Лексические ошибки: {scanner.errors}"

    parser = Parser(tokens)
    ast = parser.parse()
    assert len(parser.errors) == 0, f"Синтаксические ошибки: {parser.errors}"

    analyzer = SemanticAnalyzer()
    decorated = analyzer.analyze(ast)
    errors = analyzer.get_errors()
    assert len(errors) == 0, f"Семантические ошибки: {errors}"

    generator = IRGenerator(analyzer.get_symbol_table())
    generator.analyzer = analyzer
    ir_program = generator.generate_from_ast(ast)

    writer = IRWriter()
    return writer.write_program(ir_program), ir_program


def test_simple_expression():
    source = """
    fn main() -> int {
        return 2 + 3 * 4;
    }
    """
    ir, _ = generate_ir(source)
    assert "function main() -> int {" in ir
    assert "MUL" in ir
    assert "ADD" in ir
    assert "RETURN" in ir


def test_mod_operator():
    source = """
    fn main() -> int {
        return 10 % 3;
    }
    """
    ir, _ = generate_ir(source)
    assert "MOD" in ir


def test_xor_operator():
    source = """
    fn main() -> int {
        return 5 ^ 3;
    }
    """
    ir, _ = generate_ir(source)
    # XOR может быть представлен как XOR или ^
    assert "XOR" in ir or "^" in ir


def test_variable_declaration():
    source = """
    fn main() -> void {
        int x = 5;
        int y = x + 10;
        return;
    }
    """
    ir, _ = generate_ir(source)
    assert "ALLOCA" in ir
    assert "STORE" in ir
    assert "LOAD" in ir
    assert "ADD" in ir


def test_if_statement():
    source = """
    fn main() -> void {
        int x = 5;
        if (x > 0) {
            x = 1;
        } else {
            x = -1;
        }
        return;
    }
    """
    ir, _ = generate_ir(source)
    assert "CMP_GT" in ir or "CMP" in ir
    assert "JUMP_IF" in ir
    assert "if_then" in ir
    assert "if_else" in ir
    assert "if_endif" in ir


def test_if_with_not():
    source = """
    fn main() -> void {
        bool flag = true;
        if (!flag) {
            return;
        }
        return;
    }
    """
    ir, _ = generate_ir(source)
    assert "NOT" in ir
    assert "JUMP_IF_NOT" in ir or "JUMP_IF" in ir


def test_while_loop():
    source = """
    fn main() -> void {
        int i = 0;
        while (i < 10) {
            i = i + 1;
        }
        return;
    }
    """
    ir, _ = generate_ir(source)
    assert "while_header" in ir
    assert "while_body" in ir
    assert "while_exit" in ir
    assert "JUMP" in ir


def test_function_call():
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }

    fn main() -> int {
        return add(5, 3);
    }
    """
    ir, _ = generate_ir(source)
    assert "function add" in ir
    assert "function main" in ir
    assert "PARAM" in ir
    assert "CALL" in ir


def test_factorial():
    source = """
    fn factorial(int n) -> int {
        if (n <= 1) {
            return 1;
        } else {
            return n * factorial(n - 1);
        }
    }
    """
    ir, _ = generate_ir(source)
    assert "function factorial" in ir
    assert "CMP_LE" in ir or "CMP" in ir
    assert "SUB" in ir
    assert "MUL" in ir
    assert "CALL" in ir
    assert "RETURN" in ir


def test_complex_program():
    source = """
    fn sum(int n) -> int {
        int result = 0;
        int i = 0;
        while (i < n) {
            result = result + i;
            i = i + 1;
        }
        return result;
    }

    fn main() -> int {
        return sum(10);
    }
    """
    ir, _ = generate_ir(source)
    assert "function sum" in ir
    assert "function main" in ir
    assert "while_header" in ir
    assert "ADD" in ir
    assert "CALL" in ir


def test_logical_operations():
    source = """
    fn main() -> bool {
        bool a = true;
        bool b = false;
        return a && b;
    }
    """
    ir, _ = generate_ir(source)
    assert "AND" in ir


def test_unary_operations():
    source = """
    fn main() -> int {
        int x = 5;
        return -x;
    }
    """
    ir, _ = generate_ir(source)
    assert "NEG" in ir


def test_multiple_functions():
    source = """
    fn foo() -> int {
        return 1;
    }

    fn bar() -> int {
        return 2;
    }

    fn main() -> int {
        return foo() + bar();
    }
    """
    ir, _ = generate_ir(source)
    assert "function foo" in ir
    assert "function bar" in ir
    assert "function main" in ir
    assert "CALL" in ir


def test_nested_if():
    source = """
    fn main() -> void {
        int x = 10;
        if (x > 0) {
            if (x > 5) {
                x = 1;
            }
        }
        return;
    }
    """
    ir, _ = generate_ir(source)
    assert ir.count("if_then") >= 2
    assert ir.count("if_endif") >= 2


def test_ir_validation():
    """Тест валидации IR."""
    source = """
    fn main() -> int {
        return 42;
    }
    """
    _, ir_program = generate_ir(source)

    validator = IRValidator()
    errors, warnings = validator.validate(ir_program)

    assert len(errors) == 0, f"Validation errors: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])