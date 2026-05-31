"""Дополнительные тесты для семантического анализатора"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from semantic.analyzer import SemanticAnalyzer
from semantic.symbol_table import SymbolTable
from parser.ast import (
    ProgramNode, FunctionDeclNode, BlockStmtNode, ReturnStmtNode,
    LiteralExprNode, ParamNode, VarDeclNode, IdentifierExprNode,
    BinaryExprNode, IfStmtNode, WhileStmtNode, ExprStmtNode,
    CallExprNode, AssignmentExprNode, UnaryExprNode
)

class TestSemanticAnalyzerExtra:
    def test_binary_operations(self):
        body = BlockStmtNode([
            VarDeclNode("int", "x", 1, 1, 
                BinaryExprNode(
                    LiteralExprNode(1, 1, 1), "+",
                    LiteralExprNode(2, 1, 1), 1, 1
                )
            ),
            ReturnStmtNode(1, 1, IdentifierExprNode("x", 1, 1))
        ], 1, 1)
        func = FunctionDeclNode("int", "main", [], body, 1, 1)
        ast = ProgramNode([func])
        analyzer = SemanticAnalyzer()
        decorated = analyzer.analyze(ast)
        errors = analyzer.get_errors()
        assert len(errors) == 0

    def test_unary_operations(self):
        body = BlockStmtNode([
            VarDeclNode("bool", "flag", 1, 1, LiteralExprNode(True, 1, 1)),
            VarDeclNode("bool", "not_flag", 1, 1,
                UnaryExprNode("!", IdentifierExprNode("flag", 1, 1), 1, 1)
            ),
            ReturnStmtNode(1, 1, LiteralExprNode(0, 1, 1))
        ], 1, 1)
        func = FunctionDeclNode("int", "main", [], body, 1, 1)
        ast = ProgramNode([func])
        analyzer = SemanticAnalyzer()
        decorated = analyzer.analyze(ast)
        assert len(analyzer.get_errors()) == 0

    def test_mixed_types_binary(self):
        body = BlockStmtNode([
            VarDeclNode("int", "x", 1, 1, LiteralExprNode(5, 1, 1)),
            VarDeclNode("float", "y", 1, 1, LiteralExprNode(3.14, 1, 1)),
            VarDeclNode("float", "z", 1, 1,
                BinaryExprNode(
                    IdentifierExprNode("x", 1, 1), "+",
                    IdentifierExprNode("y", 1, 1), 1, 1
                )
            ),
            ReturnStmtNode(1, 1, LiteralExprNode(0, 1, 1))
        ], 1, 1)
        func = FunctionDeclNode("int", "main", [], body, 1, 1)
        ast = ProgramNode([func])
        analyzer = SemanticAnalyzer()
        decorated = analyzer.analyze(ast)
        # int + float = float (должно работать)
        assert len(analyzer.get_errors()) == 0

    def test_comparison_operators(self):
        body = BlockStmtNode([
            VarDeclNode("int", "a", 1, 1, LiteralExprNode(5, 1, 1)),
            VarDeclNode("int", "b", 1, 1, LiteralExprNode(10, 1, 1)),
            VarDeclNode("bool", "result", 1, 1,
                BinaryExprNode(
                    IdentifierExprNode("a", 1, 1), "<",
                    IdentifierExprNode("b", 1, 1), 1, 1
                )
            ),
            ReturnStmtNode(1, 1, LiteralExprNode(0, 1, 1))
        ], 1, 1)
        func = FunctionDeclNode("int", "main", [], body, 1, 1)
        ast = ProgramNode([func])
        analyzer = SemanticAnalyzer()
        decorated = analyzer.analyze(ast)
        assert len(analyzer.get_errors()) == 0
