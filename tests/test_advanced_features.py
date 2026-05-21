# tests/test_advanced_features.py
"""
Тесты для расширенных возможностей языка:
- Массивы
- Структуры
- Сравнение чисел с плавающей точкой
"""

import pytest
import sys
import subprocess
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir import IRGenerator, IRWriter


def generate_ir(source: str):
    """Генерация IR из исходного кода."""
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    assert len(scanner.errors) == 0, f"Lexical errors: {scanner.errors}"

    parser = Parser(tokens)
    ast = parser.parse()
    assert len(parser.errors) == 0, f"Syntax errors: {parser.errors}"

    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    errors = analyzer.get_errors()
    assert len(errors) == 0, f"Semantic errors: {errors}"

    generator = IRGenerator(analyzer.get_symbol_table())
    generator.analyzer = analyzer
    ir_program = generator.generate_from_ast(ast)

    writer = IRWriter()
    return writer.write_program(ir_program), ir_program


def compile_and_run(source: str) -> int:
    """Компилирует и запускает программу, возвращает код выхода."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.src', delete=False) as f:
        f.write(source)
        src_file = f.name

    asm_file = src_file.replace('.src', '.asm')
    obj_file = src_file.replace('.src', '.o')
    exe_file = src_file.replace('.src', '')

    runtime_asm = Path(__file__).parent.parent / 'runtime' / 'runtime.asm'
    runtime_obj = '/tmp/runtime_test.o'

    try:
        # 1. Компиляция в ассемблер
        result = subprocess.run(
            ['python', '-m', 'lexer.cli', '--input', src_file, '--mode', 'compile', '--output', asm_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return -1

        # 2. Ассемблирование программы
        result = subprocess.run(['nasm', '-f', 'elf64', '-o', obj_file, asm_file], capture_output=True)
        if result.returncode != 0:
            return -2

        # 3. Ассемблирование runtime
        result = subprocess.run(['nasm', '-f', 'elf64', '-o', runtime_obj, str(runtime_asm)], capture_output=True)
        if result.returncode != 0:
            return -3

        # 4. Линковка
        result = subprocess.run(['ld', '-o', exe_file, runtime_obj, obj_file], capture_output=True)
        if result.returncode != 0:
            return -4

        # 5. Запуск
        result = subprocess.run([exe_file], capture_output=True)
        exit_code = result.returncode

    finally:
        # Очистка
        for f in [src_file, asm_file, obj_file, exe_file, runtime_obj]:
            try:
                os.unlink(f)
            except:
                pass

    return exit_code


# ============= ТЕСТЫ МАССИВОВ =============

def test_array_declaration():
    """Объявление и инициализация массива."""
    source = """
    fn main() -> int {
        int arr[5];
        arr[0] = 42;
        return arr[0];
    }
    """
    ir, _ = generate_ir(source)
    # Проверяем наличие операций с массивами
    assert "ARRAY_ACCESS" in ir or "GEP" in ir or "LOAD" in ir


def test_array_sequential_access():
    """Последовательный доступ к элементам массива."""
    source = """
    fn main() -> int {
        int arr[3];
        arr[0] = 10;
        arr[1] = 20;
        arr[2] = 30;
        return arr[0] + arr[1] + arr[2];
    }
    """
    ir, _ = generate_ir(source)
    assert "ADD" in ir


def test_array_with_loop():
    """Массив в цикле."""
    source = """
    fn main() -> int {
        int arr[10];
        int i = 0;
        while (i < 10) {
            arr[i] = i;
            i = i + 1;
        }
        return arr[5];
    }
    """
    ir, _ = generate_ir(source)
    assert "while_header" in ir
    assert "while_body" in ir


# ============= ТЕСТЫ СТРУКТУР =============

def test_struct_declaration():
    """Объявление и использование структуры."""
    source = """
    struct Point {
        int x;
        int y;
    }
    fn main() -> int {
        Point p;
        p.x = 10;
        p.y = 20;
        return p.x + p.y;
    }
    """
    ir, _ = generate_ir(source)
    assert "STRUCT" in ir or "FIELD" in ir or "LOAD" in ir


def test_struct_nested():
    """Вложенные структуры."""
    source = """
    struct Point {
        int x;
        int y;
    }
    struct Rect {
        Point top_left;
        Point bottom_right;
    }
    fn main() -> int {
        Rect r;
        r.top_left.x = 0;
        r.top_left.y = 0;
        r.bottom_right.x = 10;
        r.bottom_right.y = 10;
        return r.bottom_right.x;
    }
    """
    ir, _ = generate_ir(source)
    # Проверяем, что парсинг прошел без ошибок
    assert True


def test_struct_return():
    """Структура как возвращаемое значение."""
    source = """
    struct Point {
        int x;
        int y;
    }
    fn make_point(int x, int y) -> Point {
        Point p;
        p.x = x;
        p.y = y;
        return p;
    }
    fn main() -> int {
        Point p = make_point(5, 7);
        return p.x + p.y;
    }
    """
    ir, _ = generate_ir(source)
    assert "CALL" in ir


# ============= ТЕСТЫ СРАВНЕНИЯ FLOAT =============

def test_float_less_than():
    """Сравнение float: меньше."""
    source = """
    fn main() -> int {
        float a = 3.14;
        float b = 2.71;
        if (a > b) {
            return 1;
        }
        return 0;
    }
    """
    ir, _ = generate_ir(source)
    assert "CMP_GT" in ir or "CMP" in ir


def test_float_equal():
    """Сравнение float: равно."""
    source = """
    fn main() -> int {
        float a = 3.14;
        float b = 3.14;
        if (a == b) {
            return 1;
        }
        return 0;
    }
    """
    ir, _ = generate_ir(source)
    assert "CMP_EQ" in ir or "CMP" in ir


def test_float_in_condition():
    """Float в условии цикла."""
    source = """
    fn main() -> int {
        float x = 0.0;
        int count = 0;
        while (x < 5.0) {
            x = x + 1.0;
            count = count + 1;
        }
        return count;
    }
    """
    ir, _ = generate_ir(source)
    assert "while_header" in ir
    assert "CMP_LT" in ir


# ============= КОМБИНИРОВАННЫЕ ТЕСТЫ =============

def test_array_of_structs():
    """Массив структур."""
    source = """
    struct Point {
        int x;
        int y;
    }
    fn main() -> int {
        Point points[3];
        points[0].x = 1;
        points[0].y = 2;
        points[1].x = 3;
        points[1].y = 4;
        points[2].x = 5;
        points[2].y = 6;
        return points[1].x + points[2].y;
    }
    """
    ir, _ = generate_ir(source)
    assert "ARRAY_ACCESS" in ir or "LOAD" in ir


def test_float_array():
    """Массив float чисел."""
    source = """
    fn main() -> int {
        float arr[3];
        arr[0] = 1.5;
        arr[1] = 2.5;
        arr[2] = 3.5;
        if (arr[1] > arr[0]) {
            return 1;
        }
        return 0;
    }
    """
    ir, _ = generate_ir(source)
    assert "CMP_GT" in ir or "CMP" in ir


def test_struct_with_float():
    """Структура с float полями."""
    source = """
    struct Point3D {
        float x;
        float y;
        float z;
    }
    fn main() -> int {
        Point3D p;
        p.x = 1.0;
        p.y = 2.0;
        p.z = 3.0;
        if (p.z > p.x) {
            return 1;
        }
        return 0;
    }
    """
    ir, _ = generate_ir(source)
    assert "CMP_GT" in ir or "CMP" in ir


# ============= ТЕСТЫ ВЫПОЛНЕНИЯ (интеграционные) =============

def test_execute_array():
    """Реальное выполнение программы с массивом."""
    source = """
    fn main() -> int {
        int arr[5];
        arr[0] = 42;
        return arr[0];
    }
    """
    exit_code = compile_and_run(source)
    assert exit_code == 42


def test_execute_struct():
    """Реальное выполнение программы со структурой."""
    source = """
    struct Point {
        int x;
        int y;
    }
    fn main() -> int {
        Point p;
        p.x = 10;
        p.y = 20;
        return p.x + p.y;
    }
    """
    exit_code = compile_and_run(source)
    assert exit_code == 30


def test_execute_float_compare():
    """Реальное выполнение программы с float сравнением."""
    source = """
    fn main() -> int {
        float a = 3.14;
        float b = 2.71;
        if (a > b) {
            return 1;
        }
        return 0;
    }
    """
    exit_code = compile_and_run(source)
    assert exit_code == 1


def test_execute_array_loop():
    """Реальное выполнение: массив в цикле."""
    source = """
    fn main() -> int {
        int arr[5];
        int i = 0;
        while (i < 5) {
            arr[i] = i * 2;
            i = i + 1;
        }
        return arr[3];
    }
    """
    exit_code = compile_and_run(source)
    assert exit_code == 6  # 3 * 2 = 6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])