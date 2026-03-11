"""
Модуль содержит базовый класс Visitor для обхода AST.
Реализует паттерн Visitor, позволяя добавлять новые операции
над AST без изменения классов узлов.
"""

from typing import Any
from .ast import *


class Visitor:
    """
    Базовый класс Visitor для обхода AST.

    Для каждого типа узла есть метод visit_<тип>.
    По умолчанию все методы вызывают visit_default.

    Пример использования:
        class MyVisitor(Visitor):
            def visit_function_decl(self, node):
                print(f"Найдена функция: {node.name}")
                self.visit(node.body)  # обходим тело
    """

    def visit(self, node: ASTNode) -> Any:
        """
        Посещает узел AST.

        Args:
            node: Узел для посещения

        Returns:
            Any: Результат обхода
        """
        return node.accept(self)

    # ============= Program =============

    def visit_program(self, node: ProgramNode) -> Any:
        """Посещает узел Program"""
        pass

    # ============= Declarations =============

    def visit_function_decl(self, node: FunctionDeclNode) -> Any:
        """Посещает узел FunctionDecl"""
        pass

    def visit_struct_decl(self, node: StructDeclNode) -> Any:
        """Посещает узел StructDecl"""
        pass

    def visit_var_decl(self, node: VarDeclNode) -> Any:
        """Посещает узел VarDecl"""
        pass

    def visit_param(self, node: ParamNode) -> Any:
        """Посещает узел Param"""
        pass

    # ============= Statements =============

    def visit_block(self, node: BlockStmtNode) -> Any:
        """Посещает узел Block"""
        pass

    def visit_if(self, node: IfStmtNode) -> Any:
        """Посещает узел If"""
        pass

    def visit_while(self, node: WhileStmtNode) -> Any:
        """Посещает узел While"""
        pass

    def visit_for(self, node: ForStmtNode) -> Any:
        """Посещает узел For"""
        pass

    def visit_return(self, node: ReturnStmtNode) -> Any:
        """Посещает узел Return"""
        pass

    def visit_expr_stmt(self, node: ExprStmtNode) -> Any:
        """Посещает узел ExprStmt"""
        pass

    def visit_empty_stmt(self, node: EmptyStmtNode) -> Any:
        """Посещает узел EmptyStmt"""
        pass

    # ============= Expressions =============

    def visit_literal(self, node: LiteralExprNode) -> Any:
        """Посещает узел Literal"""
        pass

    def visit_identifier(self, node: IdentifierExprNode) -> Any:
        """Посещает узел Identifier"""
        pass

    def visit_binary(self, node: BinaryExprNode) -> Any:
        """Посещает узел Binary"""
        pass

    def visit_unary(self, node: UnaryExprNode) -> Any:
        """Посещает узел Unary"""
        pass

    def visit_call(self, node: CallExprNode) -> Any:
        """Посещает узел Call"""
        pass

    def visit_assignment(self, node: AssignmentExprNode) -> Any:
        """Посещает узел Assignment"""
        pass

    def visit_grouping(self, node: GroupingExprNode) -> Any:
        """Посещает узел Grouping"""
        pass

    def visit_cast(self, node: CastExprNode) -> Any:
        """Посещает узел Cast"""
        pass

    # ============= Default =============

    def visit_default(self, node: ASTNode) -> Any:
        """
        Метод по умолчанию для неподдерживаемых узлов.

        Args:
            node: Неподдерживаемый узел
        """
        pass


class DepthFirstVisitor(Visitor):
    """
    Visitor для обхода AST в глубину.
    Автоматически обходит все дочерние узлы перед возвратом.

    Полезен как основа для других визитеров, которым нужно
    гарантированно обойти всё дерево.
    """

    def visit_program(self, node: ProgramNode) -> Any:
        for decl in node.declarations:
            self.visit(decl)

    def visit_function_decl(self, node: FunctionDeclNode) -> Any:
        for param in node.parameters:
            self.visit(param)
        self.visit(node.body)

    def visit_struct_decl(self, node: StructDeclNode) -> Any:
        for field in node.fields:
            self.visit(field)

    def visit_var_decl(self, node: VarDeclNode) -> Any:
        if node.initializer:
            self.visit(node.initializer)

    def visit_param(self, node: ParamNode) -> Any:
        pass  # параметры не имеют дочерних узлов

    def visit_block(self, node: BlockStmtNode) -> Any:
        for stmt in node.statements:
            self.visit(stmt)

    def visit_if(self, node: IfStmtNode) -> Any:
        self.visit(node.condition)
        self.visit(node.then_branch)
        if node.else_branch:
            self.visit(node.else_branch)

    def visit_while(self, node: WhileStmtNode) -> Any:
        self.visit(node.condition)
        self.visit(node.body)

    def visit_for(self, node: ForStmtNode) -> Any:
        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
        if node.update:
            self.visit(node.update)
        self.visit(node.body)

    def visit_return(self, node: ReturnStmtNode) -> Any:
        if node.value:
            self.visit(node.value)

    def visit_expr_stmt(self, node: ExprStmtNode) -> Any:
        self.visit(node.expression)

    def visit_empty_stmt(self, node: EmptyStmtNode) -> Any:
        pass  # пустой оператор не имеет дочерних узлов

    def visit_literal(self, node: LiteralExprNode) -> Any:
        pass  # литерал не имеет дочерних узлов

    def visit_identifier(self, node: IdentifierExprNode) -> Any:
        pass  # идентификатор не имеет дочерних узлов

    def visit_binary(self, node: BinaryExprNode) -> Any:
        self.visit(node.left)
        self.visit(node.right)

    def visit_unary(self, node: UnaryExprNode) -> Any:
        self.visit(node.operand)

    def visit_call(self, node: CallExprNode) -> Any:
        self.visit(node.callee)
        for arg in node.arguments:
            self.visit(arg)

    def visit_assignment(self, node: AssignmentExprNode) -> Any:
        self.visit(node.target)
        self.visit(node.value)

    def visit_grouping(self, node: GroupingExprNode) -> Any:
        self.visit(node.expression)

    def visit_cast(self, node: CastExprNode) -> Any:
        self.visit(node.expression)