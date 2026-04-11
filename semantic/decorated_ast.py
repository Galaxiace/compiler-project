# semantic/decorated_ast.py
"""
Модуль для декорированного AST с аннотациями типов.
"""

from typing import List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum, auto

from parser.ast import (
    ASTNode, ProgramNode, FunctionDeclNode, StructDeclNode, VarDeclNode,
    ParamNode, BlockStmtNode, IfStmtNode, WhileStmtNode, ForStmtNode,
    ReturnStmtNode, ExprStmtNode, EmptyStmtNode,
    ExpressionNode, LiteralExprNode, IdentifierExprNode, BinaryExprNode,
    UnaryExprNode, CallExprNode, AssignmentExprNode, GroupingExprNode,
    CastExprNode
)
from .symbol_table import SymbolInfo, Type


class DecoratedNodeType(Enum):
    """Типы декорированных узлов."""
    PROGRAM = auto()
    FUNCTION = auto()
    STRUCT = auto()
    VAR = auto()
    PARAM = auto()
    BLOCK = auto()
    IF = auto()
    WHILE = auto()
    FOR = auto()
    RETURN = auto()
    EXPR_STMT = auto()
    EMPTY_STMT = auto()
    EXPR = auto()


@dataclass
class DecoratedNode:
    """Базовый класс для всех декорированных узлов."""
    original: ASTNode
    node_type: DecoratedNodeType
    line: int
    column: int

    def __post_init__(self):
        if self.original:
            self.line = self.original.line
            self.column = self.original.column


# ============= Декорированные объявления =============

@dataclass
class DecoratedProgram(DecoratedNode):
    """Декорированная программа."""
    declarations: List[Union['DecoratedFunction', 'DecoratedStruct', 'DecoratedVar']]
    symbol_table: Any

    def __init__(self, original: ProgramNode, symbol_table):
        super().__init__(original, DecoratedNodeType.PROGRAM, original.line, original.column)
        self.declarations = []
        self.symbol_table = symbol_table


@dataclass
class DecoratedFunction(DecoratedNode):
    """Декорированное объявление функции."""
    name: str
    return_type: Type
    parameters: List['DecoratedParam']
    body: 'DecoratedBlock'
    symbol: SymbolInfo

    def __init__(self, original: FunctionDeclNode, return_type: Type,
                 parameters: List['DecoratedParam'], body: 'DecoratedBlock',
                 symbol: SymbolInfo):
        super().__init__(original, DecoratedNodeType.FUNCTION, original.line, original.column)
        self.name = original.name
        self.return_type = return_type
        self.parameters = parameters
        self.body = body
        self.symbol = symbol


@dataclass
class DecoratedStruct(DecoratedNode):
    """Декорированное объявление структуры."""
    name: str
    fields: List['DecoratedVar']
    symbol: SymbolInfo

    def __init__(self, original: StructDeclNode, fields: List['DecoratedVar'], symbol: SymbolInfo):
        super().__init__(original, DecoratedNodeType.STRUCT, original.line, original.column)
        self.name = original.name
        self.fields = fields
        self.symbol = symbol


@dataclass
class DecoratedParam(DecoratedNode):
    """Декорированный параметр функции."""
    name: str
    type: Type
    symbol: SymbolInfo

    def __init__(self, original: ParamNode, type: Type, symbol: SymbolInfo):
        super().__init__(original, DecoratedNodeType.PARAM, original.line, original.column)
        self.name = original.name
        self.type = type
        self.symbol = symbol


@dataclass
class DecoratedVar(DecoratedNode):
    """Декорированное объявление переменной."""
    name: str
    type: Type
    initializer: Optional['DecoratedExpr']
    symbol: SymbolInfo

    def __init__(self, original: VarDeclNode, type: Type,
                 initializer: Optional['DecoratedExpr'], symbol: SymbolInfo):
        super().__init__(original, DecoratedNodeType.VAR, original.line, original.column)
        self.name = original.name
        self.type = type
        self.initializer = initializer
        self.symbol = symbol


# ============= Декорированные операторы =============

@dataclass
class DecoratedBlock(DecoratedNode):
    """Декорированный блок операторов."""
    statements: List[Union['DecoratedStmt']]

    def __init__(self, original: BlockStmtNode, statements: List[Union['DecoratedStmt']]):
        super().__init__(original, DecoratedNodeType.BLOCK, original.line, original.column)
        self.statements = statements


@dataclass
class DecoratedIf(DecoratedNode):
    """Декорированный условный оператор."""
    condition: 'DecoratedExpr'
    then_branch: 'DecoratedStmt'
    else_branch: Optional['DecoratedStmt']

    def __init__(self, original: IfStmtNode, condition: 'DecoratedExpr',
                 then_branch: 'DecoratedStmt', else_branch: Optional['DecoratedStmt'] = None):
        super().__init__(original, DecoratedNodeType.IF, original.line, original.column)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


@dataclass
class DecoratedWhile(DecoratedNode):
    """Декорированный цикл while."""
    condition: 'DecoratedExpr'
    body: 'DecoratedStmt'

    def __init__(self, original: WhileStmtNode, condition: 'DecoratedExpr', body: 'DecoratedStmt'):
        super().__init__(original, DecoratedNodeType.WHILE, original.line, original.column)
        self.condition = condition
        self.body = body


@dataclass
class DecoratedFor(DecoratedNode):
    """Декорированный цикл for."""
    init: Optional['DecoratedStmt']
    condition: Optional['DecoratedExpr']
    update: Optional['DecoratedExpr']
    body: 'DecoratedStmt'

    def __init__(self, original: ForStmtNode, init: Optional['DecoratedStmt'] = None,
                 condition: Optional['DecoratedExpr'] = None, update: Optional['DecoratedExpr'] = None,
                 body: Optional['DecoratedStmt'] = None):
        super().__init__(original, DecoratedNodeType.FOR, original.line, original.column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body


@dataclass
class DecoratedReturn(DecoratedNode):
    """Декорированный оператор return."""
    value: Optional['DecoratedExpr']

    def __init__(self, original: ReturnStmtNode, value: Optional['DecoratedExpr'] = None):
        super().__init__(original, DecoratedNodeType.RETURN, original.line, original.column)
        self.value = value


@dataclass
class DecoratedExprStmt(DecoratedNode):
    """Декорированный оператор-выражение."""
    expression: 'DecoratedExpr'

    def __init__(self, original: ExprStmtNode, expression: 'DecoratedExpr'):
        super().__init__(original, DecoratedNodeType.EXPR_STMT, original.line, original.column)
        self.expression = expression


@dataclass
class DecoratedEmptyStmt(DecoratedNode):
    """Декорированный пустой оператор."""

    def __init__(self, original: EmptyStmtNode):
        super().__init__(original, DecoratedNodeType.EMPTY_STMT, original.line, original.column)


DecoratedStmt = Union[
    DecoratedVar, DecoratedBlock, DecoratedIf, DecoratedWhile,
    DecoratedFor, DecoratedReturn, DecoratedExprStmt, DecoratedEmptyStmt
]


# ============= Декорированные выражения (без @dataclass для полного контроля) =============

class DecoratedExpr(DecoratedNode):
    """Базовый класс для всех декорированных выражений."""

    def __init__(self, original: ExpressionNode, type: Type,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, DecoratedNodeType.EXPR, original.line, original.column)
        self.type = type
        self.symbol = symbol
        self.is_constant = is_constant
        self.constant_value = constant_value


class DecoratedLiteralExpr(DecoratedExpr):
    """Декорированный литерал."""

    def __init__(self, original: LiteralExprNode, type: Type, value: Any,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = True, constant_value: Any = None):
        const_val = constant_value if constant_value is not None else value
        super().__init__(original, type, symbol, is_constant, const_val)
        self.value = value


class DecoratedIdentifierExpr(DecoratedExpr):
    """Декорированный идентификатор."""

    def __init__(self, original: IdentifierExprNode, type: Type, symbol: SymbolInfo,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.name = original.name


class DecoratedBinaryExpr(DecoratedExpr):
    """Декорированное бинарное выражение."""

    def __init__(self, original: BinaryExprNode, type: Type,
                 left: DecoratedExpr, operator: str, right: DecoratedExpr,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.left = left
        self.operator = operator
        self.right = right


class DecoratedUnaryExpr(DecoratedExpr):
    """Декорированное унарное выражение."""

    def __init__(self, original: UnaryExprNode, type: Type,
                 operator: str, operand: DecoratedExpr,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.operator = operator
        self.operand = operand


class DecoratedCallExpr(DecoratedExpr):
    """Декорированный вызов функции."""

    def __init__(self, original: CallExprNode, type: Type,
                 callee: DecoratedExpr, arguments: List[DecoratedExpr],
                 symbol: Optional[SymbolInfo] = None,
                 function_symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.callee = callee
        self.arguments = arguments
        self.function_symbol = function_symbol


class DecoratedAssignmentExpr(DecoratedExpr):
    """Декорированное присваивание."""

    def __init__(self, original: AssignmentExprNode, type: Type,
                 target: DecoratedExpr, operator: str, value: DecoratedExpr,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.target = target
        self.operator = operator
        self.value = value


class DecoratedGroupingExpr(DecoratedExpr):
    """Декорированное группирующее выражение."""

    def __init__(self, original: GroupingExprNode, type: Type,
                 expression: DecoratedExpr,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.expression = expression


class DecoratedCastExpr(DecoratedExpr):
    """Декорированное приведение типа."""

    def __init__(self, original: CastExprNode, type: Type,
                 target_type: Type, expression: DecoratedExpr,
                 symbol: Optional[SymbolInfo] = None,
                 is_constant: bool = False, constant_value: Any = None):
        super().__init__(original, type, symbol, is_constant, constant_value)
        self.target_type = target_type
        self.expression = expression


# ============= DecoratedASTPrinter =============

class DecoratedASTPrinter:
    """Класс для красивого вывода декорированного AST."""

    def __init__(self, show_types: bool = True, show_symbols: bool = False,
                 show_constants: bool = False):
        self.indent_level = 0
        self.indent_size = 2
        self.output = []
        self.show_types = show_types
        self.show_symbols = show_symbols
        self.show_constants = show_constants

    def _indent(self) -> str:
        return " " * (self.indent_level * self.indent_size)

    def _write(self, text: str = ""):
        self.output.append(self._indent() + text)

    def _write_line(self, text: str = ""):
        self.output.append(self._indent() + text)

    def _type_annotation(self, type: Type) -> str:
        if not self.show_types:
            return ""
        return f" [type: {type.name}]"

    def _constant_annotation(self, expr: DecoratedExpr) -> str:
        if not self.show_constants or not expr.is_constant:
            return ""
        value_str = self._format_constant_value(expr.constant_value)
        return f" [constant: {value_str}]"

    def _symbol_annotation(self, symbol: Optional[SymbolInfo]) -> str:
        if not self.show_symbols or not symbol:
            return ""
        return f" [ref: {symbol.kind.name} {symbol.name}@{symbol.line}]"

    def _format_constant_value(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def get_output(self) -> str:
        return "\n".join(self.output)

    def clear(self):
        self.output = []
        self.indent_level = 0

    def print_program(self, node: DecoratedProgram):
        self._write_line(f"Program [line {node.line}]:")
        self.indent_level += 1

        self._write_line("Symbol Table:")
        self.indent_level += 1
        self._write_line(node.symbol_table.dump())
        self.indent_level -= 1

        for decl in node.declarations:
            self._write_line("")
            if isinstance(decl, DecoratedFunction):
                self.print_function(decl)
            elif isinstance(decl, DecoratedStruct):
                self.print_struct(decl)
            elif isinstance(decl, DecoratedVar):
                self.print_var(decl)

        self.indent_level -= 1

    def print_function(self, node: DecoratedFunction):
        params_str = ", ".join(f"{p.type.name} {p.name}" for p in node.parameters)
        type_str = self._type_annotation(node.return_type) if self.show_types else ""
        symbol_str = self._symbol_annotation(node.symbol) if self.show_symbols else ""

        self._write_line(
            f"FunctionDecl: {node.name} ({params_str}) -> {node.return_type.name}{type_str}{symbol_str} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Body:")
        self.indent_level += 1
        self.print_block(node.body)
        self.indent_level -= 2

    def print_struct(self, node: DecoratedStruct):
        symbol_str = self._symbol_annotation(node.symbol) if self.show_symbols else ""
        self._write_line(f"StructDecl: {node.name}{symbol_str} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Fields:")
        self.indent_level += 1
        for field in node.fields:
            self.print_var(field)
        self.indent_level -= 2

    def print_var(self, node: DecoratedVar):
        type_str = self._type_annotation(node.type) if self.show_types else ""
        symbol_str = self._symbol_annotation(node.symbol) if self.show_symbols else ""

        if node.initializer:
            self._write_line(f"VarDecl: {node.type.name} {node.name}{type_str}{symbol_str} = [line {node.line}]:")
            self.indent_level += 1
            self.print_expr(node.initializer)
            self.indent_level -= 1
        else:
            self._write_line(f"VarDecl: {node.type.name} {node.name}{type_str}{symbol_str} [line {node.line}]")

    def print_block(self, node: DecoratedBlock):
        last_line = node.line
        for stmt in node.statements:
            if hasattr(stmt, 'line') and stmt.line > last_line:
                last_line = stmt.line

        if last_line == node.line:
            self._write_line(f"Block [line {node.line}]:")
        else:
            self._write_line(f"Block [line {node.line}-{last_line}]:")

        self.indent_level += 1
        for stmt in node.statements:
            self.print_statement(stmt)
        self.indent_level -= 1

    def print_statement(self, stmt: DecoratedStmt):
        if isinstance(stmt, DecoratedVar):
            self.print_var(stmt)
        elif isinstance(stmt, DecoratedBlock):
            self.print_block(stmt)
        elif isinstance(stmt, DecoratedIf):
            self.print_if(stmt)
        elif isinstance(stmt, DecoratedWhile):
            self.print_while(stmt)
        elif isinstance(stmt, DecoratedFor):
            self.print_for(stmt)
        elif isinstance(stmt, DecoratedReturn):
            self.print_return(stmt)
        elif isinstance(stmt, DecoratedExprStmt):
            self.print_expr_stmt(stmt)
        elif isinstance(stmt, DecoratedEmptyStmt):
            self._write_line(f"EmptyStmt [line {stmt.line}]")

    def print_if(self, node: DecoratedIf):
        self._write_line(f"IfStmt [line {node.line}]:")
        self.indent_level += 1

        self._write_line("Condition:")
        self.indent_level += 1
        self.print_expr(node.condition)
        self.indent_level -= 1

        self._write_line("Then:")
        self.indent_level += 1
        self.print_statement(node.then_branch)
        self.indent_level -= 1

        if node.else_branch:
            self._write_line("Else:")
            self.indent_level += 1
            self.print_statement(node.else_branch)
            self.indent_level -= 1

        self.indent_level -= 1

    def print_while(self, node: DecoratedWhile):
        self._write_line(f"WhileStmt [line {node.line}]:")
        self.indent_level += 1

        self._write_line("Condition:")
        self.indent_level += 1
        self.print_expr(node.condition)
        self.indent_level -= 1

        self._write_line("Body:")
        self.indent_level += 1
        self.print_statement(node.body)
        self.indent_level -= 2

    def print_for(self, node: DecoratedFor):
        self._write_line(f"ForStmt [line {node.line}]:")
        self.indent_level += 1

        if node.init:
            self._write_line("Init:")
            self.indent_level += 1
            self.print_statement(node.init)
            self.indent_level -= 1

        if node.condition:
            self._write_line("Condition:")
            self.indent_level += 1
            self.print_expr(node.condition)
            self.indent_level -= 1

        if node.update:
            self._write_line("Update:")
            self.indent_level += 1
            self.print_expr(node.update)
            self.indent_level -= 1

        self._write_line("Body:")
        self.indent_level += 1
        self.print_statement(node.body)
        self.indent_level -= 2

    def print_return(self, node: DecoratedReturn):
        if node.value:
            self._write_line(f"Return [line {node.line}]:")
            self.indent_level += 1
            self.print_expr(node.value)
            self.indent_level -= 1
        else:
            self._write_line(f"Return [line {node.line}]: void")

    def print_expr_stmt(self, node: DecoratedExprStmt):
        self._write_line(f"ExprStmt [line {node.line}]:")
        self.indent_level += 1
        self.print_expr(node.expression)
        self.indent_level -= 1

    def print_expr(self, expr: DecoratedExpr):
        if isinstance(expr, DecoratedLiteralExpr):
            self._print_literal(expr)
        elif isinstance(expr, DecoratedIdentifierExpr):
            self._print_identifier(expr)
        elif isinstance(expr, DecoratedBinaryExpr):
            self._print_binary(expr)
        elif isinstance(expr, DecoratedUnaryExpr):
            self._print_unary(expr)
        elif isinstance(expr, DecoratedCallExpr):
            self._print_call(expr)
        elif isinstance(expr, DecoratedAssignmentExpr):
            self._print_assignment(expr)
        elif isinstance(expr, DecoratedGroupingExpr):
            self._print_grouping(expr)
        elif isinstance(expr, DecoratedCastExpr):
            self._print_cast(expr)

    def _print_literal(self, node: DecoratedLiteralExpr):
        value_str = self._format_constant_value(node.value)
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Literal: {value_str}{type_str}{const_str} [line {node.line}]")

    def _print_identifier(self, node: DecoratedIdentifierExpr):
        type_str = self._type_annotation(node.type)
        symbol_str = self._symbol_annotation(node.symbol)
        const_str = self._constant_annotation(node)
        self._write_line(f"Identifier: {node.name}{type_str}{symbol_str}{const_str} [line {node.line}]")

    def _print_binary(self, node: DecoratedBinaryExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Binary: {node.operator}{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Left:")
        self.indent_level += 1
        self.print_expr(node.left)
        self.indent_level -= 1
        self._write_line("Right:")
        self.indent_level += 1
        self.print_expr(node.right)
        self.indent_level -= 2

    def _print_unary(self, node: DecoratedUnaryExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Unary: {node.operator}{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self.print_expr(node.operand)
        self.indent_level -= 1

    def _print_call(self, node: DecoratedCallExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Call{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Callee:")
        self.indent_level += 1
        self.print_expr(node.callee)
        self.indent_level -= 1
        if node.arguments:
            self._write_line("Arguments:")
            self.indent_level += 1
            for arg in node.arguments:
                self.print_expr(arg)
            self.indent_level -= 1
        self.indent_level -= 1

    def _print_assignment(self, node: DecoratedAssignmentExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Assignment: {node.operator}{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self._write_line("Target:")
        self.indent_level += 1
        self.print_expr(node.target)
        self.indent_level -= 1
        self._write_line("Value:")
        self.indent_level += 1
        self.print_expr(node.value)
        self.indent_level -= 2

    def _print_grouping(self, node: DecoratedGroupingExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Grouping{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self.print_expr(node.expression)
        self.indent_level -= 1

    def _print_cast(self, node: DecoratedCastExpr):
        type_str = self._type_annotation(node.type)
        const_str = self._constant_annotation(node)
        self._write_line(f"Cast: -> {node.target_type.name}{type_str}{const_str} [line {node.line}]:")
        self.indent_level += 1
        self.print_expr(node.expression)
        self.indent_level -= 1

    def print(self,
              node: Union[DecoratedProgram, DecoratedFunction, DecoratedBlock, DecoratedStmt, DecoratedExpr]) -> str:
        self.clear()

        if isinstance(node, DecoratedProgram):
            self.print_program(node)
        elif isinstance(node, DecoratedFunction):
            self.print_function(node)
        elif isinstance(node, DecoratedBlock):
            self.print_block(node)
        elif isinstance(node, DecoratedVar):
            self.print_var(node)
        elif isinstance(node, DecoratedIf):
            self.print_if(node)
        elif isinstance(node, DecoratedWhile):
            self.print_while(node)
        elif isinstance(node, DecoratedFor):
            self.print_for(node)
        elif isinstance(node, DecoratedReturn):
            self.print_return(node)
        elif isinstance(node, DecoratedExprStmt):
            self.print_expr_stmt(node)
        elif isinstance(node, DecoratedExpr):
            self.print_expr(node)

        return self.get_output()


# ============= Вспомогательные функции =============

def create_decorated_literal(literal: LiteralExprNode, type: Type) -> DecoratedLiteralExpr:
    return DecoratedLiteralExpr(literal, type, literal.value)


def create_decorated_identifier(identifier: IdentifierExprNode, type: Type,
                                symbol: SymbolInfo) -> DecoratedIdentifierExpr:
    return DecoratedIdentifierExpr(identifier, type, symbol)


def create_decorated_binary(binary: BinaryExprNode, type: Type,
                            left: DecoratedExpr, right: DecoratedExpr) -> DecoratedBinaryExpr:
    is_constant = left.is_constant and right.is_constant
    constant_value = None

    if is_constant:
        constant_value = _fold_binary_constant(left.constant_value, binary.operator, right.constant_value)

    return DecoratedBinaryExpr(binary, type, left, binary.operator, right,
                               is_constant=is_constant, constant_value=constant_value)


def create_decorated_unary(unary: UnaryExprNode, type: Type,
                           operand: DecoratedExpr) -> DecoratedUnaryExpr:
    is_constant = operand.is_constant
    constant_value = None

    if is_constant:
        constant_value = _fold_unary_constant(unary.operator, operand.constant_value)

    return DecoratedUnaryExpr(unary, type, unary.operator, operand,
                              is_constant=is_constant, constant_value=constant_value)


def create_decorated_call(call: CallExprNode, type: Type,
                          callee: DecoratedExpr, arguments: List[DecoratedExpr],
                          function_symbol: Optional[SymbolInfo] = None) -> DecoratedCallExpr:
    return DecoratedCallExpr(call, type, callee, arguments, function_symbol=function_symbol)


def create_decorated_assignment(assignment: AssignmentExprNode, type: Type,
                                target: DecoratedExpr, value: DecoratedExpr) -> DecoratedAssignmentExpr:
    return DecoratedAssignmentExpr(assignment, type, target, assignment.operator, value)


def _fold_binary_constant(left: Any, operator: str, right: Any) -> Any:
    if operator == '+':
        return left + right
    elif operator == '-':
        return left - right
    elif operator == '*':
        return left * right
    elif operator == '/':
        if right != 0:
            return left / right
        return None
    elif operator == '%':
        if isinstance(left, int) and isinstance(right, int) and right != 0:
            return left % right
        return None
    elif operator == '==':
        return left == right
    elif operator == '!=':
        return left != right
    elif operator == '<':
        return left < right
    elif operator == '<=':
        return left <= right
    elif operator == '>':
        return left > right
    elif operator == '>=':
        return left >= right
    elif operator == '&&':
        return left and right
    elif operator == '||':
        return left or right
    return None


def _fold_unary_constant(operator: str, operand: Any) -> Any:
    if operator == '-':
        return -operand
    elif operator == '!':
        return not operand
    elif operator == '+':
        return operand
    return None