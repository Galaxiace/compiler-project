"""Тесты для IR генератора"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ir.ir_generator import IRGenerator
from ir.control_flow import IRProgram, IRFunction
from semantic.symbol_table import SymbolTable
from parser.ast import (
    ProgramNode, FunctionDeclNode, BlockStmtNode, ReturnStmtNode,
    LiteralExprNode, ParamNode, VarDeclNode
)

class TestIRGenerator:
    def test_generate_empty_program(self):
        ast = ProgramNode([])
        symtab = SymbolTable()
        gen = IRGenerator(symtab)
        ir = gen.generate_from_ast(ast)
        assert isinstance(ir, IRProgram)
        assert len(ir.functions) == 0

    def test_generate_simple_function(self):
        body = BlockStmtNode([
            ReturnStmtNode(1, 1, LiteralExprNode(42, 1, 1))
        ], 1, 1)
        func = FunctionDeclNode("int", "main", [], body, 1, 1)
        ast = ProgramNode([func])
        symtab = SymbolTable()
        gen = IRGenerator(symtab)
        ir = gen.generate_from_ast(ast)
        assert len(ir.functions) == 1
        assert ir.functions[0].name == "main"

    def test_generate_function_with_params(self):
        body = BlockStmtNode([
            ReturnStmtNode(1, 1, LiteralExprNode(0, 1, 1))
        ], 1, 1)
        params = [
            ParamNode("int", "a", 1, 1),
            ParamNode("int", "b", 1, 1)
        ]
        func = FunctionDeclNode("int", "add", params, body, 1, 1)
        ast = ProgramNode([func])
        symtab = SymbolTable()
        gen = IRGenerator(symtab)
        ir = gen.generate_from_ast(ast)
        assert len(ir.functions) == 1
        assert ir.functions[0].name == "add"
        assert len(ir.functions[0].parameters) == 2

    def test_generate_void_function(self):
        body = BlockStmtNode([
            ReturnStmtNode(1, 1, None)
        ], 1, 1)
        func = FunctionDeclNode("void", "do_nothing", [], body, 1, 1)
        ast = ProgramNode([func])
        symtab = SymbolTable()
        gen = IRGenerator(symtab)
        ir = gen.generate_from_ast(ast)
        assert len(ir.functions) == 1
        assert ir.functions[0].name == "do_nothing"

    def test_generate_var_decl(self):
        body = BlockStmtNode([
            VarDeclNode("int", "x", 1, 1, LiteralExprNode(10, 1, 1)),
            ReturnStmtNode(1, 1, None)
        ], 1, 1)
        func = FunctionDeclNode("void", "test", [], body, 1, 1)
        ast = ProgramNode([func])
        symtab = SymbolTable()
        gen = IRGenerator(symtab)
        ir = gen.generate_from_ast(ast)
        assert len(ir.functions) == 1
