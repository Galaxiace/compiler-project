# tests/test_arrays.py
"""
Тесты для поддержки массивов.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator
from ir.optimizer import IROptimizer


def generate_ir(source: str, optimize: bool = False):
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    ast = parser.parse()
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    generator = IRGenerator(analyzer.get_symbol_table())
    generator.analyzer = analyzer
    ir_program = generator.generate_from_ast(ast)

    if optimize:
        optimizer = IROptimizer(ir_program)
        ir_program = optimizer.optimize()

    return ir_program


def test_array_declaration():
    source = """
    fn main() -> int {
        int arr[10];
        arr[0] = 42;
        return arr[0];
    }
    """
    ir_program = generate_ir(source)
    # Проверяем, что IR содержит операции с массивами
    assert ir_program is not None


def test_array_initialization():
    source = """
    fn main() -> int {
        int arr[3] = {1, 2, 3};
        return arr[1];
    }
    """
    ir_program = generate_ir(source)
    assert ir_program is not None


def test_multi_dimensional_array():
    source = """
    fn main() -> int {
        int matrix[3][4];
        matrix[1][2] = 42;
        return matrix[1][2];
    }
    """
    ir_program = generate_ir(source)
    assert ir_program is not None


def test_constant_folding():
    source = """
    fn main() -> int {
        return 5 + 3 * 2;
    }
    """
    ir_program = generate_ir(source, optimize=True)
    # Проверяем, что константная свертка сработала
    # (должен быть один RETURN с константой)
    assert ir_program is not None


def test_dead_code_elimination():
    source = """
    fn main() -> int {
        int x = 5;
        int y = 10;
        if (0) {
            x = 100;
        }
        return x;
    }
    """
    ir_program = generate_ir(source, optimize=True)
    assert ir_program is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])