from typing import Any, Dict, List, Set
from .ast import *
from .visitor import Visitor


class DotGenerator(Visitor):
    """
    Генератор Graphviz DOT для визуализации AST.
    Создает файл в формате DOT, который можно преобразовать в PNG с помощью dot.

    Пример использования:
        dot -Tpng ast.dot -o ast.png
    """

    def __init__(self):
        self.node_counter = 0
        self.nodes: List[str] = []
        self.edges: List[str] = []
        self.node_stack: List[int] = []

        # Цвета для разных типов узлов
        self.colors = {
            NodeType.PROGRAM: "lightblue",
            NodeType.FUNCTION_DECL: "lightgreen",
            NodeType.STRUCT_DECL: "lightcoral",
            NodeType.VAR_DECL: "lightskyblue",
            NodeType.PARAM: "lightyellow",
            NodeType.BLOCK: "lightgray",
            NodeType.IF: "orange",
            NodeType.WHILE: "orange",
            NodeType.FOR: "orange",
            NodeType.RETURN: "salmon",
            NodeType.EXPR_STMT: "white",
            NodeType.EMPTY_STMT: "white",
            NodeType.LITERAL: "palegreen",
            NodeType.IDENTIFIER: "palegreen",
            NodeType.BINARY: "yellow",
            NodeType.UNARY: "yellow",
            NodeType.CALL: "violet",
            NodeType.ASSIGNMENT: "pink",
            NodeType.GROUPING: "lightcyan",
            NodeType.CAST: "lightcyan",
        }

    def _new_node_id(self) -> int:
        """Создает новый уникальный идентификатор узла"""
        self.node_counter += 1
        return self.node_counter

    def _add_node(self, node: ASTNode, label: str) -> int:
        """
        Добавляет узел в граф.

        Args:
            node: Узел AST
            label: Метка узла

        Returns:
            int: ID узла
        """
        node_id = self._new_node_id()
        color = self.colors.get(node.node_type, "white")

        # Экранируем специальные символы в label
        label = label.replace('"', '\\"').replace('\n', '\\n')

        self.nodes.append(
            f'    node{node_id} [label="{label}", shape=box, style=filled, fillcolor={color}];'
        )

        # Добавляем связь с родительским узлом
        if self.node_stack:
            parent_id = self.node_stack[-1]
            self.edges.append(f'    node{parent_id} -> node{node_id};')

        return node_id

    def generate(self, node: ASTNode) -> str:
        """
        Генерирует DOT представление AST.

        Args:
            node: Корневой узел AST

        Returns:
            str: DOT граф
        """
        self.node_counter = 0
        self.nodes = []
        self.edges = []
        self.node_stack = []

        self.visit(node)

        # Собираем итоговый DOT файл
        dot = [
            "digraph AST {",
            "    node [fontname=\"Arial\"];",
            "    edge [fontname=\"Arial\"];",
            "    rankdir=TB;",
            ""
        ]

        dot.extend(self.nodes)
        if self.nodes:
            dot.append("")
        dot.extend(self.edges)
        dot.append("}")

        return "\n".join(dot)

    # ============= Методы визитера =============

    def visit_program(self, node: ProgramNode) -> Any:
        node_id = self._add_node(node, f"Program\n[line {node.line}]")
        self.node_stack.append(node_id)

        for decl in node.declarations:
            self.visit(decl)

        self.node_stack.pop()

    def visit_function_decl(self, node: FunctionDeclNode) -> Any:
        label = f"Function: {node.name}\n-> {node.return_type}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        # Параметры
        for param in node.parameters:
            self.visit(param)

        # Тело функции
        self.visit(node.body)

        self.node_stack.pop()

    def visit_struct_decl(self, node: StructDeclNode) -> Any:
        label = f"Struct: {node.name}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        for field in node.fields:
            self.visit(field)

        self.node_stack.pop()

    def visit_var_decl(self, node: VarDeclNode) -> Any:
        if node.initializer:
            label = f"Var: {node.type_name} {node.name} =\n[line {node.line}]"
        else:
            label = f"Var: {node.type_name} {node.name}\n[line {node.line}]"

        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        if node.initializer:
            self.visit(node.initializer)

        self.node_stack.pop()

    def visit_param(self, node: ParamNode) -> Any:
        label = f"Param: {node.type_name} {node.name}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)
        self.node_stack.pop()

    def visit_block(self, node: BlockStmtNode) -> Any:
        label = f"Block\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        for stmt in node.statements:
            self.visit(stmt)

        self.node_stack.pop()

    def visit_if(self, node: IfStmtNode) -> Any:
        label = f"If\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        # Условие
        self.visit(node.condition)

        # Then ветка
        self.visit(node.then_branch)

        # Else ветка
        if node.else_branch:
            self.visit(node.else_branch)

        self.node_stack.pop()

    def visit_while(self, node: WhileStmtNode) -> Any:
        label = f"While\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.condition)
        self.visit(node.body)

        self.node_stack.pop()

    def visit_for(self, node: ForStmtNode) -> Any:
        label = f"For\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
        if node.update:
            self.visit(node.update)
        self.visit(node.body)

        self.node_stack.pop()

    def visit_return(self, node: ReturnStmtNode) -> Any:
        if node.value:
            label = f"Return\n[line {node.line}]"
        else:
            label = f"Return void\n[line {node.line}]"

        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        if node.value:
            self.visit(node.value)

        self.node_stack.pop()

    def visit_expr_stmt(self, node: ExprStmtNode) -> Any:
        label = f"ExprStmt\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.expression)

        self.node_stack.pop()

    def visit_empty_stmt(self, node: EmptyStmtNode) -> Any:
        label = f"EmptyStmt\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)
        self.node_stack.pop()

    def visit_literal(self, node: LiteralExprNode) -> Any:
        value_str = str(node.value)
        if node.value is None:
            value_str = "null"
        elif isinstance(node.value, str):
            value_str = f'"{node.value}"'
        elif isinstance(node.value, bool):
            value_str = "true" if node.value else "false"

        label = f"Literal: {value_str}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)
        self.node_stack.pop()

    def visit_identifier(self, node: IdentifierExprNode) -> Any:
        label = f"Identifier: {node.name}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)
        self.node_stack.pop()

    def visit_binary(self, node: BinaryExprNode) -> Any:
        label = f"Binary: {node.operator}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.left)
        self.visit(node.right)

        self.node_stack.pop()

    def visit_unary(self, node: UnaryExprNode) -> Any:
        label = f"Unary: {node.operator}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.operand)

        self.node_stack.pop()

    def visit_call(self, node: CallExprNode) -> Any:
        label = f"Call\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.callee)

        for arg in node.arguments:
            self.visit(arg)

        self.node_stack.pop()

    def visit_assignment(self, node: AssignmentExprNode) -> Any:
        label = f"Assignment: {node.operator}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.target)
        self.visit(node.value)

        self.node_stack.pop()

    def visit_grouping(self, node: GroupingExprNode) -> Any:
        label = f"Grouping\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.expression)

        self.node_stack.pop()

    def visit_cast(self, node: CastExprNode) -> Any:
        label = f"Cast: {node.type_name}\n[line {node.line}]"
        node_id = self._add_node(node, label)
        self.node_stack.append(node_id)

        self.visit(node.expression)

        self.node_stack.pop()