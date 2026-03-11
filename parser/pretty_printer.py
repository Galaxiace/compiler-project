"""
Модуль для красивого вывода AST в текстовом формате.
Используется для отладки и визуального анализа дерева.
"""

from typing import Any
from .ast import *
from .visitor import Visitor


class PrettyPrinter(Visitor):
    """
    Visitor для красивого вывода AST в текстовом формате.

    Форматирует AST с отступами, показывая структуру программы.

    Пример вывода:
        Program [line 1]:
          FunctionDecl: main -> void [line 1]:
            Body:
              Block [line 2-5]:
                VarDecl: int x = [line 3]:
                  Literal: 42 [line 3]
    """

    def __init__(self, indent_size: int = 2):
        """
        Инициализация pretty printer.

        Args:
            indent_size: Размер отступа в пробелах
        """
        self.indent_level = 0
        self.indent_size = indent_size
        self.output = []

    def _indent(self) -> str:
        """Возвращает строку отступа для текущего уровня"""
        return " " * (self.indent_level * self.indent_size)

    def _write(self, text: str = ""):
        """Добавляет текст с текущим отступом"""
        self.output.append(self._indent() + text)

    def _write_line(self, text: str = ""):
        """Добавляет строку с текущим отступом и переводом строки"""
        self.output.append(self._indent() + text)

    def get_output(self) -> str:
        """
        Возвращает сформированный вывод.

        Returns:
            str: Текстовое представление AST
        """
        return "\n".join(self.output)

    # ============= Program =============

    def visit_program(self, node: ProgramNode) -> str:
        """Форматирует узел Program"""
        self._write_line(f"Program [line {node.line}]:")
        self.indent_level += 1
        for decl in node.declarations:
            self.visit(decl)
        self.indent_level -= 1
        return self.get_output()

    # ============= Declarations =============

    def visit_function_decl(self, node: FunctionDeclNode) -> Any:
        """Форматирует объявление функции"""
        params = ", ".join([f"{p.type_name} {p.name}" for p in node.parameters])
        self._write_line(f"FunctionDecl: {node.name} -> {node.return_type} [line {node.line}]:")
        self.indent_level += 1
        self._write_line(f"Parameters: [{params}]")
        self._write_line(f"Body [line {node.line}]:")
        self.indent_level += 1
        self.visit(node.body)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_struct_decl(self, node: StructDeclNode) -> Any:
        """Форматирует объявление структуры"""
        self._write_line(f"StructDecl: {node.name} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Fields:")
        self.indent_level += 1
        for field in node.fields:
            self.visit(field)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_var_decl(self, node: VarDeclNode) -> Any:
        """Форматирует объявление переменной"""
        if node.initializer:
            self._write_line(f"VarDecl: {node.type_name} {node.name} = [line {node.line}]:")
            self.indent_level += 1
            self.visit(node.initializer)
            self.indent_level -= 1
        else:
            self._write_line(f"VarDecl: {node.type_name} {node.name} [line {node.line}]")

    def visit_param(self, node: ParamNode) -> Any:
        """Параметры форматируются в функции, этот метод не вызывается напрямую"""
        pass

    # ============= Statements =============

    def visit_block(self, node: BlockStmtNode) -> Any:
        """
        Форматирует блок операторов с диапазоном строк.
        """
        # Находим последнюю строку в блоке
        last_line = node.line
        if node.statements:
            # Ищем максимальную строку среди операторов
            for stmt in node.statements:
                if hasattr(stmt, 'line') and stmt.line > last_line:
                    last_line = stmt.line
                # Также проверяем вложенные элементы
                if hasattr(stmt, 'condition') and hasattr(stmt.condition, 'line') and stmt.condition.line > last_line:
                    last_line = stmt.condition.line
                if hasattr(stmt, 'then_branch') and hasattr(stmt.then_branch,
                                                            'line') and stmt.then_branch.line > last_line:
                    last_line = stmt.then_branch.line

        # Если блок пустой или не нашли большую строку, используем ту же строку
        if last_line == node.line:
            self._write_line(f"Block [line {node.line}]:")
        else:
            self._write_line(f"Block [line {node.line}-{last_line}]:")

        self.indent_level += 1
        for stmt in node.statements:
            self.visit(stmt)
        self.indent_level -= 1

    def visit_if(self, node: IfStmtNode) -> Any:
        """Форматирует условный оператор"""
        self._write_line(f"IfStmt [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Condition:")
        self.indent_level += 1
        self.visit(node.condition)
        self.indent_level -= 1
        self._write_line("Then:")
        self.indent_level += 1
        self.visit(node.then_branch)
        self.indent_level -= 1
        if node.else_branch:
            self._write_line("Else:")
            self.indent_level += 1
            self.visit(node.else_branch)
            self.indent_level -= 1
        self.indent_level -= 1

    def visit_while(self, node: WhileStmtNode) -> Any:
        """Форматирует цикл while"""
        self._write_line(f"WhileStmt [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Condition:")
        self.indent_level += 1
        self.visit(node.condition)
        self.indent_level -= 1
        self._write_line("Body:")
        self.indent_level += 1
        self.visit(node.body)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_for(self, node: ForStmtNode) -> Any:
        """Форматирует цикл for"""
        self._write_line(f"ForStmt [line {node.line}]:")
        self.indent_level += 1
        if node.init:
            self._write_line("Init:")
            self.indent_level += 1
            self.visit(node.init)
            self.indent_level -= 1
        if node.condition:
            self._write_line("Condition:")
            self.indent_level += 1
            self.visit(node.condition)
            self.indent_level -= 1
        if node.update:
            self._write_line("Update:")
            self.indent_level += 1
            self.visit(node.update)
            self.indent_level -= 1
        self._write_line("Body:")
        self.indent_level += 1
        self.visit(node.body)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_return(self, node: ReturnStmtNode) -> Any:
        """Форматирует оператор return"""
        if node.value:
            self._write_line(f"Return [line {node.line}]:")
            self.indent_level += 1
            self.visit(node.value)
            self.indent_level -= 1
        else:
            self._write_line(f"Return [line {node.line}]: void")

    def visit_expr_stmt(self, node: ExprStmtNode) -> Any:
        """Форматирует оператор-выражение"""
        self._write_line(f"ExprStmt [line {node.line}]:")
        self.indent_level += 1
        self.visit(node.expression)
        self.indent_level -= 1

    def visit_empty_stmt(self, node: EmptyStmtNode) -> Any:
        """Форматирует пустой оператор"""
        self._write_line(f"EmptyStmt [line {node.line}]")

    # ============= Expressions =============

    def visit_literal(self, node: LiteralExprNode) -> Any:
        """Форматирует литерал"""
        value_str = str(node.value)
        if node.value is None:
            value_str = "null"
        elif isinstance(node.value, str):
            value_str = f'"{node.value}"'
        elif isinstance(node.value, bool):
            value_str = "true" if node.value else "false"
        self._write_line(f"Literal: {value_str} [line {node.line}]")

    def visit_identifier(self, node: IdentifierExprNode) -> Any:
        """Форматирует идентификатор"""
        self._write_line(f"Identifier: {node.name} [line {node.line}]")

    def visit_binary(self, node: BinaryExprNode) -> Any:
        """Форматирует бинарную операцию"""
        self._write_line(f"Binary: {node.operator} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Left:")
        self.indent_level += 1
        self.visit(node.left)
        self.indent_level -= 1
        self._write_line("Right:")
        self.indent_level += 1
        self.visit(node.right)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_unary(self, node: UnaryExprNode) -> Any:
        """Форматирует унарную операцию"""
        self._write_line(f"Unary: {node.operator} [line {node.line}]:")
        self.indent_level += 1
        self.visit(node.operand)
        self.indent_level -= 1

    def visit_call(self, node: CallExprNode) -> Any:
        """Форматирует вызов функции"""
        self._write_line(f"Call [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Callee:")
        self.indent_level += 1
        self.visit(node.callee)
        self.indent_level -= 1
        if node.arguments:
            self._write_line("Arguments:")
            self.indent_level += 1
            for arg in node.arguments:
                self.visit(arg)
            self.indent_level -= 1
        self.indent_level -= 1

    def visit_assignment(self, node: AssignmentExprNode) -> Any:
        """Форматирует присваивание"""
        self._write_line(f"Assignment: {node.operator} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Target:")
        self.indent_level += 1
        self.visit(node.target)
        self.indent_level -= 1
        self._write_line("Value:")
        self.indent_level += 1
        self.visit(node.value)
        self.indent_level -= 1
        self.indent_level -= 1

    def visit_grouping(self, node: GroupingExprNode) -> Any:
        """Форматирует группировку в скобках"""
        self._write_line(f"Grouping [line {node.line}]:")
        self.indent_level += 1
        self.visit(node.expression)
        self.indent_level -= 1

    def visit_cast(self, node: CastExprNode) -> Any:
        """Форматирует приведение типа"""
        self._write_line(f"Cast: {node.type_name} [line {node.line}]:")
        self.indent_level += 1
        self.visit(node.expression)
        self.indent_level -= 1