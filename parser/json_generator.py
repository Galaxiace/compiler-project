"""
Генератор JSON представления AST.
Создает машиночитаемый формат для автоматического тестирования и интеграции.
"""

import json
from typing import Any, Dict, List
from .ast import *
from .visitor import Visitor


class ASTEncoder(json.JSONEncoder):
    """
    Специальный JSON encoder для сериализации узлов AST.
    """

    def default(self, obj):
        if isinstance(obj, ASTNode):
            # Базовые поля для всех узлов
            result = {
                'type': obj.node_type.name,
                'line': obj.line,
                'column': obj.column
            }

            # Добавляем специфичные поля в зависимости от типа узла
            if isinstance(obj, LiteralExprNode):
                result['value'] = obj.value

            elif isinstance(obj, IdentifierExprNode):
                result['name'] = obj.name

            elif isinstance(obj, BinaryExprNode):
                result['operator'] = obj.operator
                result['left'] = obj.left
                result['right'] = obj.right

            elif isinstance(obj, UnaryExprNode):
                result['operator'] = obj.operator
                result['operand'] = obj.operand

            elif isinstance(obj, CallExprNode):
                result['callee'] = obj.callee
                result['arguments'] = obj.arguments

            elif isinstance(obj, AssignmentExprNode):
                result['operator'] = obj.operator
                result['target'] = obj.target
                result['value'] = obj.value

            elif isinstance(obj, GroupingExprNode):
                result['expression'] = obj.expression

            elif isinstance(obj, CastExprNode):
                result['type_name'] = obj.type_name
                result['expression'] = obj.expression

            elif isinstance(obj, ProgramNode):
                result['declarations'] = obj.declarations

            elif isinstance(obj, FunctionDeclNode):
                result['name'] = obj.name
                result['return_type'] = obj.return_type
                result['parameters'] = obj.parameters
                result['body'] = obj.body

            elif isinstance(obj, StructDeclNode):
                result['name'] = obj.name
                result['fields'] = obj.fields

            elif isinstance(obj, VarDeclNode):
                result['type_name'] = obj.type_name
                result['name'] = obj.name
                result['initializer'] = obj.initializer

            elif isinstance(obj, ParamNode):
                result['type_name'] = obj.type_name
                result['name'] = obj.name

            elif isinstance(obj, BlockStmtNode):
                result['statements'] = obj.statements

            elif isinstance(obj, IfStmtNode):
                result['condition'] = obj.condition
                result['then_branch'] = obj.then_branch
                result['else_branch'] = obj.else_branch

            elif isinstance(obj, WhileStmtNode):
                result['condition'] = obj.condition
                result['body'] = obj.body

            elif isinstance(obj, ForStmtNode):
                result['init'] = obj.init
                result['condition'] = obj.condition
                result['update'] = obj.update
                result['body'] = obj.body

            elif isinstance(obj, ReturnStmtNode):
                result['value'] = obj.value

            elif isinstance(obj, ExprStmtNode):
                result['expression'] = obj.expression

            elif isinstance(obj, EmptyStmtNode):
                pass  # нет дополнительных полей

            return result

        # Для списков и других стандартных типов используем стандартную сериализацию
        return super().default(obj)


class JsonGenerator(Visitor):
    """
    Генератор JSON представления AST.
    Использует кастомный JSON encoder для сериализации узлов AST.
    """

    def __init__(self):
        self.result = None

    def generate(self, node: ASTNode) -> str:
        """
        Генерирует JSON представление AST.

        Args:
            node: Корневой узел AST

        Returns:
            str: JSON строка с отступами
        """
        self.result = None
        self.visit(node)

        # Используем кастомный encoder для сериализации
        return json.dumps(self.result, cls=ASTEncoder, ensure_ascii=False, indent=2)

    # ============= Методы визитера =============

    def visit_program(self, node: ProgramNode) -> Any:
        """Посещает узел Program"""
        # Просто сохраняем узел как результат - encoder сам разберет структуру
        self.result = node

    def visit_function_decl(self, node: FunctionDeclNode) -> Any:
        """Посещает узел FunctionDecl"""
        # Для функций обходим параметры и тело
        for param in node.parameters:
            self.visit(param)
        self.visit(node.body)

    def visit_struct_decl(self, node: StructDeclNode) -> Any:
        """Посещает узел StructDecl"""
        for field in node.fields:
            self.visit(field)

    def visit_var_decl(self, node: VarDeclNode) -> Any:
        """Посещает узел VarDecl"""
        if node.initializer:
            self.visit(node.initializer)

    def visit_param(self, node: ParamNode) -> Any:
        """Посещает узел Param"""
        pass  # параметры не имеют дочерних узлов

    def visit_block(self, node: BlockStmtNode) -> Any:
        """Посещает узел Block"""
        for stmt in node.statements:
            self.visit(stmt)

    def visit_if(self, node: IfStmtNode) -> Any:
        """Посещает узел If"""
        self.visit(node.condition)
        self.visit(node.then_branch)
        if node.else_branch:
            self.visit(node.else_branch)

    def visit_while(self, node: WhileStmtNode) -> Any:
        """Посещает узел While"""
        self.visit(node.condition)
        self.visit(node.body)

    def visit_for(self, node: ForStmtNode) -> Any:
        """Посещает узел For"""
        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
        if node.update:
            self.visit(node.update)
        self.visit(node.body)

    def visit_return(self, node: ReturnStmtNode) -> Any:
        """Посещает узел Return"""
        if node.value:
            self.visit(node.value)

    def visit_expr_stmt(self, node: ExprStmtNode) -> Any:
        """Посещает узел ExprStmt"""
        self.visit(node.expression)

    def visit_empty_stmt(self, node: EmptyStmtNode) -> Any:
        """Посещает узел EmptyStmt"""
        pass  # пустой оператор не имеет дочерних узлов

    def visit_literal(self, node: LiteralExprNode) -> Any:
        """Посещает узел Literal"""
        pass  # литерал не имеет дочерних узлов

    def visit_identifier(self, node: IdentifierExprNode) -> Any:
        """Посещает узел Identifier"""
        pass  # идентификатор не имеет дочерних узлов

    def visit_binary(self, node: BinaryExprNode) -> Any:
        """Посещает узел Binary"""
        self.visit(node.left)
        self.visit(node.right)

    def visit_unary(self, node: UnaryExprNode) -> Any:
        """Посещает узел Unary"""
        self.visit(node.operand)

    def visit_call(self, node: CallExprNode) -> Any:
        """Посещает узел Call"""
        self.visit(node.callee)
        for arg in node.arguments:
            self.visit(arg)

    def visit_assignment(self, node: AssignmentExprNode) -> Any:
        """Посещает узел Assignment"""
        self.visit(node.target)
        self.visit(node.value)

    def visit_grouping(self, node: GroupingExprNode) -> Any:
        """Посещает узел Grouping"""
        self.visit(node.expression)

    def visit_cast(self, node: CastExprNode) -> Any:
        """Посещает узел Cast"""
        self.visit(node.expression)