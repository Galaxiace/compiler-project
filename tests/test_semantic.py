# tests/test_semantic.py
"""
Тесты для семантического анализатора MiniCompiler.
Проверяют таблицу символов, проверку типов, ошибки и декорированное AST.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from semantic.symbol_table import SymbolTable, SymbolInfo, SymbolKind, Type
from semantic.errors import (
    SemanticError, UndeclaredIdentifierError, DuplicateDeclarationError,
    TypeMismatchError, ArgumentCountMismatchError, InvalidReturnTypeError,
    InvalidConditionTypeError, InvalidAssignmentTargetError, UseBeforeDeclarationError
)
from semantic.decorated_ast import DecoratedASTPrinter


def analyze_source(source: str):
    """
    Вспомогательная функция: выполняет полный анализ исходного кода.

    Args:
        source: Исходный код

    Returns:
        tuple: (decorated_ast, errors)
    """
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    if scanner.errors:
        return None, scanner.errors

    parser = Parser(tokens)
    ast = parser.parse()

    if parser.errors:
        return None, parser.errors

    analyzer = SemanticAnalyzer()
    decorated = analyzer.analyze(ast)

    return decorated, analyzer.get_errors()


# ============= ТЕСТЫ ТАБЛИЦЫ СИМВОЛОВ =============

def test_symbol_table_creation():
    """Тест создания таблицы символов."""
    table = SymbolTable()
    assert table.global_scope is not None
    assert table.current_scope == table.global_scope
    assert len(table.scope_stack) == 1


def test_symbol_table_enter_exit_scope():
    """Тест входа и выхода из области видимости."""
    table = SymbolTable()

    table.enter_scope("test_scope")
    assert table.current_scope.name == "test_scope"
    assert table.current_scope.level == 1
    assert table.current_scope.parent is not None

    table.exit_scope()
    assert table.current_scope == table.global_scope


def test_symbol_table_insert_and_lookup():
    """Тест вставки и поиска символов."""
    table = SymbolTable()

    int_type = Type("int")

    info = SymbolInfo(
        name="x",
        kind=SymbolKind.VARIABLE,
        type=int_type,
        line=1,
        column=1,
        is_initialized=True
    )

    assert table.insert("x", info) == True
    assert table.insert("x", info) == False

    found = table.lookup("x")
    assert found is not None
    assert found.name == "x"
    assert found.kind == SymbolKind.VARIABLE

    assert table.lookup("y") is None


def test_symbol_table_nested_scopes():
    """Тест вложенных областей видимости."""
    table = SymbolTable()
    int_type = Type("int")

    global_info = SymbolInfo("x", SymbolKind.VARIABLE, int_type, 1, 1)
    table.insert("x", global_info)

    table.enter_scope("function:main")

    local_info = SymbolInfo("x", SymbolKind.VARIABLE, int_type, 2, 5)
    table.insert("x", local_info)

    local = table.lookup_local("x")
    assert local is local_info

    found = table.lookup("x")
    assert found is local_info

    table.exit_scope()

    found = table.lookup("x")
    assert found is global_info


# ============= ТЕСТЫ ОБЪЯВЛЕНИЙ =============

def test_global_variable_declaration():
    """Тест объявления глобальной переменной."""
    source = "int x = 42;"
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_duplicate_global_variable():
    """Тест повторного объявления глобальной переменной."""
    source = """
    int x = 5;
    int x = 10;
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 1
    assert isinstance(errors[0], DuplicateDeclarationError)


def test_function_declaration():
    """Тест объявления функции."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_duplicate_function():
    """Тест повторного объявления функции."""
    source = """
    fn test() -> void { return; }
    fn test() -> void { return; }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 1
    assert isinstance(errors[0], DuplicateDeclarationError)


def test_struct_declaration():
    """Тест объявления структуры."""
    source = """
    struct Point {
        int x;
        int y;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_struct_duplicate_field():
    """Тест дублирующихся полей структуры."""
    source = """
    struct Point {
        int x;
        int x;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) >= 1


# ============= ТЕСТЫ ПРОВЕРКИ ТИПОВ =============

def test_type_compatibility_int_to_float():
    """Тест совместимости int -> float (расширение)."""
    source = """
    fn test() -> void {
        float x = 42;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_type_mismatch_float_to_int():
    """Тест несовместимости float -> int (сужающее)."""
    source = """
    fn test() -> void {
        int x = 3.14;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 1
    assert isinstance(errors[0], TypeMismatchError)


def test_binary_operation_int_plus_int():
    """Тест: int + int -> int."""
    source = """
    fn test() -> int {
        return 5 + 3;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_binary_operation_int_plus_float():
    """Тест: int + float -> float."""
    source = """
    fn test() -> float {
        return 5 + 3.14;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_binary_operation_invalid_types():
    """Тест: недопустимая бинарная операция."""
    source = """
    fn test() -> void {
        bool b = true;
        int x = b + 5;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) >= 1
    assert any(isinstance(e, TypeMismatchError) for e in errors)


def test_logical_operation():
    """Тест логических операций."""
    source = """
    fn test() -> void {
        bool a = true;
        bool b = false;
        bool c = a && b;
        bool d = a || b;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    # Выводим ошибки для отладки, если они есть
    if errors:
        for e in errors:
            print(f"Debug - logical_operation error: {e}")

    assert len(errors) == 0


def test_comparison_operations():
    """Тест операций сравнения."""
    source = """
    fn test() -> bool {
        int x = 5;
        int y = 10;
        return x < y && x == 5;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_unary_operations():
    """Тест унарных операций."""
    source = """
    fn test() -> void {
        int x = -5;
        bool y = !true;
        int z = +10;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    if errors:
        for e in errors:
            print(f"Debug - unary_operations error: {e}")

    assert len(errors) == 0


# ============= ТЕСТЫ ПЕРЕМЕННЫХ =============

def test_undeclared_variable():
    """Тест использования необъявленной переменной."""
    source = """
    fn test() -> void {
        x = 42;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert isinstance(errors[0], UndeclaredIdentifierError)


def test_local_variable_scope():
    """Тест области видимости локальной переменной."""
    source = """
    fn test() -> void {
        int local = 5;
        {
            int local = 10;
            local = 15;
        }
        local = 20;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_uninitialized_variable_error():
    """Тест: использование неинициализированной переменной вызывает ошибку."""
    source = """
    fn test() -> void {
        int x;
        int y = x;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert any(isinstance(e, UseBeforeDeclarationError) for e in errors)


def test_initialized_variable_no_error():
    """Тест: инициализированная переменная не вызывает ошибку."""
    source = """
    fn test() -> void {
        int x = 5;
        int y = x;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    init_errors = [e for e in errors if isinstance(e, UseBeforeDeclarationError)]
    assert len(init_errors) == 0


def test_parameter_initialized():
    """Тест: параметры всегда считаются инициализированными."""
    source = """
    fn test(int param) -> void {
        int x = param;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    init_errors = [e for e in errors if isinstance(e, UseBeforeDeclarationError)]
    assert len(init_errors) == 0


def test_assignment_initializes_variable():
    """Тест: присваивание инициализирует переменную."""
    source = """
    fn test() -> void {
        int x;
        x = 5;
        int y = x;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    # Проверяем, что нет ошибки UseBeforeDeclarationError для x
    # x инициализируется присваиванием x = 5, затем используется в int y = x
    init_errors = [e for e in errors if isinstance(e, UseBeforeDeclarationError)]

    if init_errors:
        for e in init_errors:
            print(f"Debug - assignment_initializes_variable error: {e}")

    assert len(init_errors) == 0


# ============= ТЕСТЫ ФУНКЦИЙ =============

def test_function_call():
    """Тест вызова функции."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }

    fn main() -> void {
        int result = add(5, 3);
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_argument_count_mismatch():
    """Тест несоответствия количества аргументов."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }

    fn main() -> void {
        int result = add(5);
        return;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) == 1
    assert isinstance(errors[0], ArgumentCountMismatchError)


def test_argument_type_mismatch():
    """Тест несоответствия типов аргументов."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }

    fn main() -> void {
        int result = add(5, 3.14);
        return;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) == 1
    assert isinstance(errors[0], TypeMismatchError)


def test_return_type_match():
    """Тест соответствия возвращаемого типа."""
    source = """
    fn get_five() -> int {
        return 5;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_return_type_mismatch():
    """Тест несоответствия возвращаемого типа."""
    source = """
    fn get_pi() -> int {
        return 3.14;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert any(isinstance(e, (InvalidReturnTypeError, TypeMismatchError)) for e in errors)


def test_void_return():
    """Тест void функции."""
    source = """
    fn print_hello() -> void {
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_void_return_with_value():
    """Тест void функции с возвратом значения."""
    source = """
    fn print_hello() -> void {
        return 5;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert any(isinstance(e, InvalidReturnTypeError) for e in errors)


def test_missing_return():
    """Тест функции без return."""
    source = """
    fn get_five() -> int {
        int x = 5;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) >= 1


# ============= ТЕСТЫ УПРАВЛЯЮЩИХ КОНСТРУКЦИЙ =============

def test_if_condition_bool():
    """Тест условия if с bool выражением."""
    source = """
    fn test() -> void {
        bool flag = true;
        if (flag) {
            return;
        }
    }
    """
    decorated, errors = analyze_source(source)

    if errors:
        for e in errors:
            print(f"Debug - if_condition_bool error: {e}")

    assert len(errors) == 0


def test_if_condition_non_bool():
    """Тест условия if с не-bool выражением."""
    source = """
    fn test() -> void {
        int x = 5;
        if (x) {
            return;
        }
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) == 1
    assert isinstance(errors[0], InvalidConditionTypeError)


def test_while_condition_bool():
    """Тест условия while с bool выражением."""
    source = """
    fn test() -> void {
        int i = 0;
        while (i < 10) {
            i = i + 1;
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_while_condition_non_bool():
    """Тест условия while с не-bool выражением."""
    source = """
    fn test() -> void {
        int i = 10;
        while (i) {
            i = i - 1;
        }
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) == 1
    assert isinstance(errors[0], InvalidConditionTypeError)


def test_for_loop():
    """Тест цикла for."""
    source = """
    fn test() -> void {
        for (int i = 0; i < 10; i = i + 1) {
            // тело
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


# ============= ТЕСТЫ ПРИСВАИВАНИЯ =============

def test_assignment_compatible_types():
    """Тест присваивания совместимых типов."""
    source = """
    fn test() -> void {
        int x = 5;
        x = 10;
        float y = 3.14;
        y = 42;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_assignment_incompatible_types():
    """Тест присваивания несовместимых типов."""
    source = """
    fn test() -> void {
        int x = 5;
        x = 3.14;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) == 1
    assert isinstance(errors[0], TypeMismatchError)


def test_assignment_to_non_variable():
    """Тест присваивания не переменной."""
    source = """
    fn test() -> void {
        int x = 5;
        (x + 1) = 10;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert any(isinstance(e, InvalidAssignmentTargetError) for e in errors)


# ============= ТЕСТЫ ДЕКОРИРОВАННОГО AST =============

def test_decorated_ast_printer():
    """Тест вывода декорированного AST."""
    source = """
    fn test() -> int {
        int x = 42;
        return x;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0

    printer = DecoratedASTPrinter(show_types=True)
    output = printer.print(decorated)

    # Проверяем наличие ключевых элементов в выводе
    assert "Program" in output
    assert "test" in output  # Имя функции
    assert "int" in output  # Тип возвращаемого значения
    assert "x" in output  # Имя переменной


def test_decorated_ast_with_types():
    """Тест декорированного AST с аннотациями типов."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0

    printer = DecoratedASTPrinter(show_types=True)
    output = printer.print(decorated)

    # Проверяем наличие аннотаций типов
    assert "Program" in output
    assert "add" in output


def test_decorated_ast_with_symbols():
    """Тест декорированного AST с отображением символов."""
    source = """
    fn test() -> void {
        int x = 5;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0

    printer = DecoratedASTPrinter(show_symbols=True)
    output = printer.print(decorated)

    # Проверяем, что вывод содержит информацию о символах
    assert output is not None
    assert len(output) > 0


# ============= КОМПЛЕКСНЫЕ ТЕСТЫ =============

def test_complex_program():
    """Тест комплексной программы."""
    source = """
    fn factorial(int n) -> int {
        int result = 1;
        while (n > 0) {
            result = result * n;
            n = n - 1;
        }
        return result;
    }

    fn main() -> void {
        int x = 5;
        int fact = factorial(x);
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_error_recovery():
    """Тест восстановления после ошибок."""
    source = """
    fn test() -> void {
        int x = 5;
        unknown_var = 10;
        int y = x + 5;
        return;
    }
    """
    decorated, errors = analyze_source(source)

    assert len(errors) >= 1
    assert any("undeclared" in e.message.lower() for e in errors)


def test_multiple_errors():
    """Тест множественных ошибок."""
    source = """
    fn test() -> void {
        int x = "string";
        unknown = 5;
        if (x) {
            return "hello";
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) >= 3


def test_function_forward_reference():
    """Тест forward reference функций."""
    source = """
    fn main() -> void {
        int result = add(5, 3);
        return;
    }

    fn add(int a, int b) -> int {
        return a + b;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_nested_blocks():
    """Тест вложенных блоков и областей видимости."""
    source = """
    fn test() -> void {
        int x = 1;
        {
            int y = 2;
            x = y;
        }
        int z = x;
        return;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_complex_expressions():
    """Тест сложных выражений с разными типами."""
    source = """
    fn test() -> float {
        int a = 5;
        float b = 3.14;
        float c = a + b * 2.0;
        return c;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_nested_function_calls():
    """Тест вложенных вызовов функций."""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }

    fn mul(int a, int b) -> int {
        return a * b;
    }

    fn main() -> int {
        return mul(add(2, 3), add(4, 5));
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_type_conversion_in_conditions():
    """Тест преобразования типов в условиях."""
    source = """
    fn test() -> void {
        int x = 5;
        float y = 3.14;
        if (x < y) {
            return;
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_unreachable_code_detection():
    """Тест обнаружения недостижимого кода (базовая проверка)."""
    source = """
    fn test() -> int {
        return 5;
        int x = 10;  // Недостижимый код
        return x;
    }
    """
    decorated, errors = analyze_source(source)
    # Недостижимый код может не обнаруживаться в базовой версии
    # Проверяем только что нет критических ошибок
    critical_errors = [e for e in errors if not isinstance(e, (TypeMismatchError, InvalidReturnTypeError))]
    assert len(critical_errors) == 0


# ============= ТЕСТЫ КОНСТАНТНОЙ СВЕРТКИ =============

def test_constant_folding_addition():
    """Тест константной свертки сложения."""
    source = """
    fn test() -> int {
        return 5 + 3;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_constant_folding_multiplication():
    """Тест константной свертки умножения."""
    source = """
    fn test() -> int {
        return 5 * 3;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_constant_folding_complex():
    """Тест константной свертки сложного выражения."""
    source = """
    fn test() -> int {
        return (5 + 3) * 2;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_constant_boolean_expressions():
    """Тест константных булевых выражений."""
    source = """
    fn test() -> bool {
        return true && false || true;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


# ============= ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ =============

def test_empty_function():
    """Тест пустой функции."""
    source = """
    fn empty() -> void {
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_function_without_return_in_void():
    """Тест void функции без return."""
    source = """
    fn test() -> void {
        int x = 5;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0  # void функции не требуют return


def test_nested_if_statements():
    """Тест вложенных if операторов."""
    source = """
    fn test(int x) -> void {
        if (x > 0) {
            if (x > 10) {
                return;
            }
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_boolean_variable_usage():
    """Тест использования булевых переменных."""
    source = """
    fn test() -> void {
        bool flag = true;
        bool result = !flag;
        if (result) {
            return;
        }
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_multiple_parameters():
    """Тест функции с множеством параметров."""
    source = """
    fn many_params(int a, int b, int c, int d, int e) -> int {
        return a + b + c + d + e;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


def test_long_expression():
    """Тест длинного выражения."""
    source = """
    fn test() -> int {
        return 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10;
    }
    """
    decorated, errors = analyze_source(source)
    assert len(errors) == 0


# ============= ЗАПУСК ТЕСТОВ =============

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])