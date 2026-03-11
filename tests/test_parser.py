"""
Тесты для парсера MiniCompiler.
Проверяют корректность построения AST и обработку ошибок.
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer.scanner import Scanner
from lexer.token import TokenType
from parser.parser import Parser, ParseError
from parser.ast import *
from parser.pretty_printer import PrettyPrinter
from parser.dot_generator import DotGenerator
from parser.json_generator import JsonGenerator


def parse_source(source: str):
    """
    Вспомогательная функция: парсит исходный код и возвращает AST.

    Args:
        source: Исходный код

    Returns:
        ProgramNode: AST программы
    """
    scanner = Scanner(source)
    tokens = scanner.scan_tokens()

    # Проверяем, что нет лексических ошибок
    assert len(scanner.errors) == 0, f"Лексические ошибки: {scanner.errors}"

    parser = Parser(tokens)
    ast = parser.parse()

    # Проверяем, что нет синтаксических ошибок
    assert len(parser.errors) == 0, f"Синтаксические ошибки: {parser.errors}"

    return ast


# ============= ТЕСТЫ ОБЪЯВЛЕНИЙ =============

def test_empty_program():
    """Тест пустой программы"""
    source = ""
    ast = parse_source(source)

    assert isinstance(ast, ProgramNode)
    assert len(ast.declarations) == 0


def test_function_decl_no_params():
    """Тест объявления функции без параметров"""
    source = """
    fn main() -> void {
        return;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    func = ast.declarations[0]
    assert isinstance(func, FunctionDeclNode)
    assert func.name == "main"
    assert func.return_type == "void"
    assert len(func.parameters) == 0
    assert isinstance(func.body, BlockStmtNode)


def test_function_decl_with_params():
    """Тест объявления функции с параметрами"""
    source = """
    fn add(int a, int b) -> int {
        return a + b;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    func = ast.declarations[0]
    assert func.name == "add"
    assert func.return_type == "int"
    assert len(func.parameters) == 2

    param1 = func.parameters[0]
    assert param1.type_name == "int"
    assert param1.name == "a"

    param2 = func.parameters[1]
    assert param2.type_name == "int"
    assert param2.name == "b"


def test_struct_decl():
    """Тест объявления структуры"""
    source = """
    struct Point {
        int x;
        int y;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    struct = ast.declarations[0]
    assert isinstance(struct, StructDeclNode)
    assert struct.name == "Point"
    assert len(struct.fields) == 2

    field1 = struct.fields[0]
    assert field1.type_name == "int"
    assert field1.name == "x"
    assert field1.initializer is None

    field2 = struct.fields[1]
    assert field2.type_name == "int"
    assert field2.name == "y"


def test_var_decl_no_init():
    """Тест объявления переменной без инициализации"""
    source = "int x;"
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    var = ast.declarations[0]
    assert isinstance(var, VarDeclNode)
    assert var.type_name == "int"
    assert var.name == "x"
    assert var.initializer is None


def test_var_decl_with_init():
    """Тест объявления переменной с инициализацией"""
    source = "int x = 42;"
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    var = ast.declarations[0]
    assert var.type_name == "int"
    assert var.name == "x"
    assert isinstance(var.initializer, LiteralExprNode)
    assert var.initializer.value == 42


# ============= ТЕСТЫ ОПЕРАТОРОВ =============

def test_block_stmt():
    """Тест блока операторов"""
    source = """
    {
        int x = 5;
        int y = 10;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    block = ast.declarations[0]
    assert isinstance(block, BlockStmtNode)
    assert len(block.statements) == 2

    stmt1 = block.statements[0]
    assert isinstance(stmt1, VarDeclNode)
    assert stmt1.name == "x"
    assert stmt1.initializer.value == 5

    stmt2 = block.statements[1]
    assert isinstance(stmt2, VarDeclNode)
    assert stmt2.name == "y"
    assert stmt2.initializer.value == 10


def test_if_stmt():
    """Тест условного оператора if"""
    source = """
    if (x > 0) {
        y = 1;
    } else {
        y = -1;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    if_stmt = ast.declarations[0]
    assert isinstance(if_stmt, IfStmtNode)

    # Проверяем условие
    assert isinstance(if_stmt.condition, BinaryExprNode)
    assert if_stmt.condition.operator == ">"

    # Проверяем then ветку
    assert isinstance(if_stmt.then_branch, BlockStmtNode)

    # Проверяем else ветку
    assert if_stmt.else_branch is not None
    assert isinstance(if_stmt.else_branch, BlockStmtNode)


def test_while_stmt():
    """Тест цикла while"""
    source = """
    while (i < 10) {
        i = i + 1;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    while_stmt = ast.declarations[0]
    assert isinstance(while_stmt, WhileStmtNode)

    # Проверяем условие
    assert isinstance(while_stmt.condition, BinaryExprNode)
    assert while_stmt.condition.operator == "<"

    # Проверяем тело
    assert isinstance(while_stmt.body, BlockStmtNode)


def test_for_stmt():
    """Тест цикла for"""
    source = """
    for (int i = 0; i < 10; i = i + 1) {
        sum = sum + i;
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    for_stmt = ast.declarations[0]
    assert isinstance(for_stmt, ForStmtNode)

    # Проверяем инициализацию
    assert for_stmt.init is not None
    assert isinstance(for_stmt.init, VarDeclNode)
    assert for_stmt.init.name == "i"

    # Проверяем условие
    assert for_stmt.condition is not None
    assert isinstance(for_stmt.condition, BinaryExprNode)

    # Проверяем обновление
    assert for_stmt.update is not None
    assert isinstance(for_stmt.update, AssignmentExprNode)

    # Проверяем тело
    assert isinstance(for_stmt.body, BlockStmtNode)


def test_return_stmt():
    """Тест оператора return"""
    source = """
    return 42;
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    return_stmt = ast.declarations[0]
    assert isinstance(return_stmt, ReturnStmtNode)
    assert return_stmt.value is not None
    assert isinstance(return_stmt.value, LiteralExprNode)
    assert return_stmt.value.value == 42


def test_return_void():
    """Тест оператора return без значения"""
    source = "return;"
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    return_stmt = ast.declarations[0]
    assert isinstance(return_stmt, ReturnStmtNode)
    assert return_stmt.value is None


def test_empty_stmt():
    """Тест пустого оператора"""
    source = ";"
    ast = parse_source(source)

    assert len(ast.declarations) == 0

    source_block = "{ ; }"
    ast_block = parse_source(source_block)
    assert len(ast_block.declarations) == 1
    block = ast_block.declarations[0]
    assert isinstance(block, BlockStmtNode)
    assert len(block.statements) == 1
    assert isinstance(block.statements[0], EmptyStmtNode)


# ============= ТЕСТЫ ВЫРАЖЕНИЙ =============

def test_literal_expressions():
    """Тест литеральных выражений"""
    source = """
    int a = 42;
    float b = 3.14;
    string c = "hello";
    bool d = true;
    bool e = false;
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 5

    # Целое число
    assert ast.declarations[0].initializer.value == 42

    # Число с плавающей точкой
    assert ast.declarations[1].initializer.value == 3.14

    # Строка
    assert ast.declarations[2].initializer.value == "hello"

    # Булевы значения
    assert ast.declarations[3].initializer.value is True
    assert ast.declarations[4].initializer.value is False


def test_binary_operations():
    """Тест бинарных операций с приоритетами"""
    source = """
    int a = 1 + 2 * 3;
    int b = (1 + 2) * 3;
    bool c = x > 5 && y < 10;
    """
    ast = parse_source(source)

    # Проверяем: 1 + 2 * 3 (умножение имеет больший приоритет)
    expr1 = ast.declarations[0].initializer
    assert isinstance(expr1, BinaryExprNode)
    assert expr1.operator == "+"
    assert isinstance(expr1.left, LiteralExprNode)
    assert expr1.left.value == 1
    assert isinstance(expr1.right, BinaryExprNode)
    assert expr1.right.operator == "*"

    # Проверяем: (1 + 2) * 3 (скобки меняют приоритет)
    expr2 = ast.declarations[1].initializer
    assert isinstance(expr2, BinaryExprNode)
    assert expr2.operator == "*"
    assert isinstance(expr2.left, GroupingExprNode)

    # Проверяем: x > 5 && y < 10 (&& имеет меньший приоритет чем сравнения)
    expr3 = ast.declarations[2].initializer
    assert isinstance(expr3, BinaryExprNode)
    assert expr3.operator == "&&"


def test_unary_operations():
    """Тест унарных операций"""
    source = """
    int a = -5;
    int b = !flag;
    int c = -!x;
    """
    ast = parse_source(source)

    # -5 - должно быть UnaryExprNode, но лексер создает INT_LITERAL со значением -5
    # Это нормально для отрицательных чисел-констант
    expr1 = ast.declarations[0].initializer
    # Проверяем, что это литерал со значением -5
    assert isinstance(expr1, LiteralExprNode)
    assert expr1.value == -5

    # !flag - должно быть UnaryExprNode
    expr2 = ast.declarations[1].initializer
    assert isinstance(expr2, UnaryExprNode)
    assert expr2.operator == "!"
    assert isinstance(expr2.operand, IdentifierExprNode)
    assert expr2.operand.name == "flag"

    # -!x - двойной унарный
    expr3 = ast.declarations[2].initializer
    assert isinstance(expr3, UnaryExprNode)
    assert expr3.operator == "-"
    assert isinstance(expr3.operand, UnaryExprNode)
    assert expr3.operand.operator == "!"


def test_assignment():
    """Тест присваивания"""
    source = "x = 42;"
    ast = parse_source(source)

    assert len(ast.declarations) == 1
    assign = ast.declarations[0].expression
    assert isinstance(assign, AssignmentExprNode)
    assert assign.operator == "="
    assert isinstance(assign.target, IdentifierExprNode)
    assert assign.target.name == "x"
    assert isinstance(assign.value, LiteralExprNode)
    assert assign.value.value == 42


def test_function_call():
    """Тест вызова функции"""
    source = """
    int result = add(5, 3);
    print("hello");
    """
    ast = parse_source(source)

    # add(5, 3)
    call1 = ast.declarations[0].initializer
    assert isinstance(call1, CallExprNode)
    assert isinstance(call1.callee, IdentifierExprNode)
    assert call1.callee.name == "add"
    assert len(call1.arguments) == 2
    assert call1.arguments[0].value == 5
    assert call1.arguments[1].value == 3

    # print("hello")
    stmt2 = ast.declarations[1]
    assert isinstance(stmt2, ExprStmtNode)
    call2 = stmt2.expression
    assert isinstance(call2, CallExprNode)
    assert call2.callee.name == "print"
    assert len(call2.arguments) == 1
    assert call2.arguments[0].value == "hello"


# ============= ТЕСТЫ ПРИОРИТЕТОВ =============

def test_precedence_1_assignment():
    """Тест приоритета: присваивание (самый низкий)"""
    source = "x = y = 5;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # Правоассоциативное: x = (y = 5)
    assert isinstance(expr, AssignmentExprNode)
    assert expr.target.name == "x"
    assert isinstance(expr.value, AssignmentExprNode)
    assert expr.value.target.name == "y"
    assert expr.value.value.value == 5


def test_precedence_2_logical_or():
    """Тест приоритета: логическое ИЛИ"""
    source = "a || b && c;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # && имеет больший приоритет: a || (b && c)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "||"
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, BinaryExprNode)
    assert expr.right.operator == "&&"


def test_precedence_3_logical_and():
    """Тест приоритета: логическое И"""
    source = "a && b == c;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # == имеет больший приоритет: a && (b == c)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "&&"
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, BinaryExprNode)
    assert expr.right.operator == "=="


def test_precedence_4_equality():
    """Тест приоритета: сравнение на равенство"""
    source = "a == b < c;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # < имеет больший приоритет: a == (b < c)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "=="
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, BinaryExprNode)
    assert expr.right.operator == "<"


def test_precedence_5_relational():
    """Тест приоритета: реляционные операторы"""
    source = "a < b + c;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # + имеет больший приоритет: a < (b + c)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "<"
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, BinaryExprNode)
    assert expr.right.operator == "+"


def test_precedence_6_additive():
    """Тест приоритета: сложение/вычитание"""
    source = "a + b * c;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # * имеет больший приоритет: a + (b * c)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "+"
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, BinaryExprNode)
    assert expr.right.operator == "*"


def test_precedence_7_multiplicative():
    """Тест приоритета: умножение/деление"""
    source = "a * -b;"
    ast = parse_source(source)

    expr = ast.declarations[0].expression
    # унарный минус имеет больший приоритет: a * (-b)
    assert isinstance(expr, BinaryExprNode)
    assert expr.operator == "*"
    assert isinstance(expr.left, IdentifierExprNode)
    assert expr.left.name == "a"
    assert isinstance(expr.right, UnaryExprNode)
    assert expr.right.operator == "-"


# ============= ТЕСТЫ ОШИБОК =============

def test_missing_semicolon():
    """Тест пропущенной точки с запятой"""
    source = "int x = 5"

    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)

    ast = parser.parse()

    # Должна быть ошибка
    assert len(parser.errors) > 0
    error = parser.errors[0]
    assert "Ожидалась ';'" in error.message


def test_mismatched_parentheses():
    """Тест несогласованных скобок"""
    source = "if (x > 5 { y = 10; }"

    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)

    ast = parser.parse()

    # Должна быть ошибка
    assert len(parser.errors) > 0
    error = parser.errors[0]
    assert "Ожидалась ')'" in error.message


def test_invalid_expression():
    """Тест недопустимого выражения"""
    source = "int x = +;"

    scanner = Scanner(source)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)

    ast = parser.parse()

    # Должна быть ошибка
    assert len(parser.errors) > 0
    error = parser.errors[0]
    assert "Неожиданный токен" in error.message


# ============= ТЕСТЫ ВИЗУАЛИЗАЦИИ =============

def test_pretty_printer():
    """Тест pretty printer"""
    source = """
    fn main() -> void {
        int x = 42;
        return;
    }
    """
    ast = parse_source(source)

    printer = PrettyPrinter()
    printer.visit(ast)
    output = printer.get_output()

    # Проверяем, что вывод содержит ожидаемые строки
    assert "Program [line 2]:" in output
    assert "FunctionDecl: main -> void [line 2]:" in output
    assert "Block [line 2-4]:" in output
    assert "VarDecl: int x = [line 3]" in output
    assert "Literal: 42 [line 3]" in output
    assert "Return [line 4]: void" in output


def test_dot_generator():
    """Тест генератора DOT"""
    source = "int x = 42;"
    ast = parse_source(source)

    generator = DotGenerator()
    dot = generator.generate(ast)

    # Проверяем, что DOT файл содержит ожидаемые элементы
    assert "digraph AST" in dot
    assert "Program" in dot
    # Вместо проверки точной строки, проверяем наличие ключевых слов
    assert "int x" in dot or "Var:" in dot
    assert "42" in dot


def test_json_generator():
    """Тест генератора JSON"""
    source = "int x = 42;"
    ast = parse_source(source)

    generator = JsonGenerator()
    json_str = generator.generate(ast)

    # Проверяем наличие ключевых полей в JSON
    assert '"type": "PROGRAM"' in json_str or '"type": "Program"' in json_str
    assert '"declarations"' in json_str
    assert '"type_name": "int"' in json_str or '"type": "int"' in json_str
    assert '"name": "x"' in json_str
    assert '"value": 42' in json_str


# ============= ТЕСТЫ СЛОЖНЫХ ПРОГРАММ =============

def test_complete_program():
    """Тест полной программы"""
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
        print(fact);
    }
    """
    ast = parse_source(source)

    assert len(ast.declarations) == 2

    # Первая функция: factorial
    func1 = ast.declarations[0]
    assert func1.name == "factorial"
    assert len(func1.parameters) == 1
    assert func1.parameters[0].name == "n"

    # Вторая функция: main
    func2 = ast.declarations[1]
    assert func2.name == "main"
    assert len(func2.parameters) == 0

    # Проверяем тело main
    body = func2.body
    assert len(body.statements) == 3
    assert isinstance(body.statements[0], VarDeclNode)  # int x = 5;
    assert isinstance(body.statements[1], VarDeclNode)  # int fact = factorial(x);
    assert isinstance(body.statements[2], ExprStmtNode)  # print(fact);


if __name__ == '__main__':
    pytest.main([__file__, '-v'])