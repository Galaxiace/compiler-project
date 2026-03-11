"""
Модуль содержит иерархию классов для построения абстрактного синтаксического дерева (AST).
Каждый узел AST соответствует какому-либо элементу языка: выражению, оператору, объявлению.
"""

from enum import Enum, auto
from typing import List, Optional, Union, Any
from dataclasses import dataclass, field


class NodeType(Enum):
    """
    Перечисление всех типов узлов AST.
    Используется для идентификации типа узла без использования isinstance.
    """
    # Program
    PROGRAM = auto()

    # Declarations (объявления)
    FUNCTION_DECL = auto()
    STRUCT_DECL = auto()
    VAR_DECL = auto()
    PARAM = auto()

    # Statements (операторы)
    BLOCK = auto()
    IF = auto()
    WHILE = auto()
    FOR = auto()
    RETURN = auto()
    EXPR_STMT = auto()
    EMPTY_STMT = auto()

    # Expressions (выражения)
    LITERAL = auto()
    IDENTIFIER = auto()
    BINARY = auto()
    UNARY = auto()
    CALL = auto()
    ASSIGNMENT = auto()
    GROUPING = auto()
    CAST = auto()


@dataclass
class ASTNode:
    """
    Базовый класс для всех узлов AST.
    Содержит общую информацию: тип узла, строку и колонку в исходном коде.
    """
    node_type: NodeType
    line: int
    column: int

    def accept(self, visitor: 'Visitor') -> Any:
        """
        Принимает визитера (реализация паттерна Visitor).

        Args:
            visitor: Объект-визитер

        Returns:
            Any: Результат обхода
        """
        method_name = f'visit_{self.node_type.name.lower()}'
        method = getattr(visitor, method_name, None)
        if method:
            return method(self)
        return visitor.visit_default(self)


# ============= Expression Nodes (Узлы выражений) =============

@dataclass
class ExpressionNode(ASTNode):
    """
    Базовый класс для всех выражений.
    Выражение - это конструкция, которая возвращает значение.
    """
    pass


@dataclass
class LiteralExprNode(ExpressionNode):
    """
    Литерал: число, строка, булево значение или null.

    Примеры:
        42
        3.14
        "hello"
        true
        false
        null
    """
    value: Union[int, float, str, bool, None]

    def __init__(self, value: Union[int, float, str, bool, None], line: int, column: int):
        super().__init__(NodeType.LITERAL, line, column)
        self.value = value


@dataclass
class IdentifierExprNode(ExpressionNode):
    """
    Идентификатор (имя переменной, функции, структуры).

    Пример:
        x
        counter
        myFunction
    """
    name: str

    def __init__(self, name: str, line: int, column: int):
        super().__init__(NodeType.IDENTIFIER, line, column)
        self.name = name


@dataclass
class BinaryExprNode(ExpressionNode):
    """
    Бинарная операция: левый операнд оператор правый операнд.

    Примеры:
        left + right
        a * b
        x && y
    """
    left: ExpressionNode
    operator: str
    right: ExpressionNode

    def __init__(self, left: ExpressionNode, operator: str, right: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.BINARY, line, column)
        self.left = left
        self.operator = operator
        self.right = right


@dataclass
class UnaryExprNode(ExpressionNode):
    """
    Унарная операция: оператор операнд.

    Примеры:
        -5
        !flag
        +value
    """
    operator: str
    operand: ExpressionNode

    def __init__(self, operator: str, operand: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.UNARY, line, column)
        self.operator = operator
        self.operand = operand


@dataclass
class CallExprNode(ExpressionNode):
    """
    Вызов функции: callee(аргументы).

    Пример:
        add(5, 3)
        print("hello")
    """
    callee: ExpressionNode
    arguments: List[ExpressionNode]

    def __init__(self, callee: ExpressionNode, arguments: List[ExpressionNode], line: int, column: int):
        super().__init__(NodeType.CALL, line, column)
        self.callee = callee
        self.arguments = arguments


@dataclass
class AssignmentExprNode(ExpressionNode):
    """
    Присваивание: цель оператор значение.

    Примеры:
        x = 5
        y += 10
        z *= 2
    """
    target: ExpressionNode
    operator: str
    value: ExpressionNode

    def __init__(self, target: ExpressionNode, operator: str, value: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.ASSIGNMENT, line, column)
        self.target = target
        self.operator = operator
        self.value = value


@dataclass
class GroupingExprNode(ExpressionNode):
    """
    Группировка в скобках: (выражение).
    Используется для изменения приоритета операций.

    Пример:
        (a + b) * c
    """
    expression: ExpressionNode

    def __init__(self, expression: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.GROUPING, line, column)
        self.expression = expression


@dataclass
class CastExprNode(ExpressionNode):
    """
    Приведение типа: (тип) выражение.

    Пример:
        (float) 5
    """
    type_name: str
    expression: ExpressionNode

    def __init__(self, type_name: str, expression: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.CAST, line, column)
        self.type_name = type_name
        self.expression = expression


# ============= Statement Nodes (Узлы операторов) =============

@dataclass
class StatementNode(ASTNode):
    """
    Базовый класс для всех операторов.
    Оператор - это конструкция, которая выполняет действие и не возвращает значение.
    """
    pass


@dataclass
class BlockStmtNode(StatementNode):
    """
    Блок операторов: { операторы }.

    Пример:
        {
            int x = 5;
            int y = 10;
        }
    """
    statements: List[StatementNode]

    def __init__(self, statements: List[StatementNode], line: int, column: int):
        super().__init__(NodeType.BLOCK, line, column)
        self.statements = statements


@dataclass
class ExprStmtNode(StatementNode):
    """
    Оператор-выражение: выражение;

    Пример:
        x = 42;
        add(5, 3);
    """
    expression: ExpressionNode

    def __init__(self, expression: ExpressionNode, line: int, column: int):
        super().__init__(NodeType.EXPR_STMT, line, column)
        self.expression = expression


@dataclass
class IfStmtNode(StatementNode):
    """
    Условный оператор: if (условие) then_ветка [else else_ветка]

    Пример:
        if (x > 0) {
            y = 1;
        } else {
            y = -1;
        }
    """
    condition: ExpressionNode
    then_branch: StatementNode
    else_branch: Optional[StatementNode] = None

    def __init__(self, condition: ExpressionNode, then_branch: StatementNode,
                 line: int, column: int, else_branch: Optional[StatementNode] = None):
        super().__init__(NodeType.IF, line, column)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


@dataclass
class WhileStmtNode(StatementNode):
    """
    Цикл while: while (условие) тело

    Пример:
        while (i < 10) {
            i = i + 1;
        }
    """
    condition: ExpressionNode
    body: StatementNode

    def __init__(self, condition: ExpressionNode, body: StatementNode, line: int, column: int):
        super().__init__(NodeType.WHILE, line, column)
        self.condition = condition
        self.body = body


@dataclass
class ForStmtNode(StatementNode):
    """
    Цикл for: for (инициализация; условие; обновление) тело

    Пример:
        for (int i = 0; i < 10; i = i + 1) {
            sum = sum + i;
        }
    """
    init: Optional[StatementNode]
    condition: Optional[ExpressionNode]
    update: Optional[ExpressionNode]
    body: StatementNode

    def __init__(self, init: Optional[StatementNode], condition: Optional[ExpressionNode],
                 update: Optional[ExpressionNode], body: StatementNode, line: int, column: int):
        super().__init__(NodeType.FOR, line, column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body


@dataclass
class ReturnStmtNode(StatementNode):
    """
    Оператор return: return [значение];

    Примеры:
        return 42;
        return;
    """
    value: Optional[ExpressionNode] = None

    def __init__(self, line: int, column: int, value: Optional[ExpressionNode] = None):
        super().__init__(NodeType.RETURN, line, column)
        self.value = value


@dataclass
class EmptyStmtNode(StatementNode):
    """
    Пустой оператор: ;

    Используется, когда точка с запятой стоит сама по себе.
    """

    def __init__(self, line: int, column: int):
        super().__init__(NodeType.EMPTY_STMT, line, column)


# ============= Declaration Nodes (Узлы объявлений) =============

@dataclass
class DeclarationNode(ASTNode):
    """
    Базовый класс для всех объявлений.
    Объявление вводит новое имя в программе.
    """
    pass


@dataclass
class VarDeclNode(DeclarationNode, StatementNode):
    """
    Объявление переменной: тип имя [= инициализатор];

    Примеры:
        int x;
        float y = 3.14;
        bool flag = true;
    """
    type_name: str
    name: str
    initializer: Optional[ExpressionNode] = None

    def __init__(self, type_name: str, name: str, line: int, column: int,
                 initializer: Optional[ExpressionNode] = None):
        super().__init__(NodeType.VAR_DECL, line, column)
        self.type_name = type_name
        self.name = name
        self.initializer = initializer


@dataclass
class ParamNode(ASTNode):
    """
    Параметр функции: тип имя

    Пример:
        int x
        float value
    """
    type_name: str
    name: str

    def __init__(self, type_name: str, name: str, line: int, column: int):
        super().__init__(NodeType.PARAM, line, column)
        self.type_name = type_name
        self.name = name


@dataclass
class FunctionDeclNode(DeclarationNode):
    """
    Объявление функции: fn имя(параметры) -> возвращаемый_тип { тело }

    Пример:
        fn add(int a, int b) -> int {
            return a + b;
        }
    """
    return_type: str
    name: str
    parameters: List[ParamNode]
    body: BlockStmtNode

    def __init__(self, return_type: str, name: str, parameters: List[ParamNode],
                 body: BlockStmtNode, line: int, column: int):
        super().__init__(NodeType.FUNCTION_DECL, line, column)
        self.return_type = return_type
        self.name = name
        self.parameters = parameters
        self.body = body


@dataclass
class StructDeclNode(DeclarationNode):
    """
    Объявление структуры: struct имя { поля }

    Пример:
        struct Point {
            int x;
            int y;
        }
    """
    name: str
    fields: List[VarDeclNode]

    def __init__(self, name: str, fields: List[VarDeclNode], line: int, column: int):
        super().__init__(NodeType.STRUCT_DECL, line, column)
        self.name = name
        self.fields = fields


# ============= Program Node (Корневой узел) =============

@dataclass
class ProgramNode(ASTNode):
    """
    Корневой узел всей программы.
    Содержит список всех объявлений верхнего уровня.
    """
    declarations: List[DeclarationNode]

    def __init__(self, declarations: List[DeclarationNode], line: int = 1, column: int = 1):
        super().__init__(NodeType.PROGRAM, line, column)
        self.declarations = declarations