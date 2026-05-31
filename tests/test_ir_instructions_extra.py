"""Дополнительные тесты для IR инструкций"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ir.ir_instructions import (
    IRInstruction, IROpcode, IROperand, IROperandType,
    Temp, Lit, Label, Var, Global
)

class TestIROperand:
    def test_temp_operand(self):
        t = Temp("%1", "int")
        assert t.operand_type == IROperandType.TEMPORARY
        assert t.value == "%1"

    def test_lit_operand(self):
        l = Lit(42, "int")
        assert l.operand_type == IROperandType.LITERAL
        assert l.value == 42

    def test_label_operand(self):
        lbl = Label("loop_start")
        assert lbl.operand_type == IROperandType.LABEL
        assert lbl.value == "loop_start"

    def test_var_operand(self):
        v = Var("myvar", "int")
        assert v.operand_type == IROperandType.VARIABLE
        assert v.value == "myvar"

    def test_global_operand(self):
        g = Global("global_var")
        assert g.operand_type == IROperandType.GLOBAL
        assert g.value == "global_var"

class TestIRInstruction:
    def test_create_add(self):
        instr = IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(2), Lit(3)
        ])
        assert instr.opcode == IROpcode.ADD
        assert len(instr.operands) == 3

    def test_create_with_comment(self):
        instr = IRInstruction(IROpcode.RETURN, [Lit(0)], "return 0")
        assert instr.comment == "return 0"

    def test_all_opcodes_exist(self):
        opcodes = [
            IROpcode.MOVE, IROpcode.ADD, IROpcode.SUB, IROpcode.MUL,
            IROpcode.DIV, IROpcode.MOD, IROpcode.NEG, IROpcode.NOT,
            IROpcode.AND, IROpcode.OR, IROpcode.XOR,
            IROpcode.CMP_EQ, IROpcode.CMP_NE, IROpcode.CMP_LT,
            IROpcode.CMP_LE, IROpcode.CMP_GT, IROpcode.CMP_GE,
            IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT,
            IROpcode.CALL, IROpcode.PARAM, IROpcode.RETURN,
            IROpcode.LOAD, IROpcode.STORE, IROpcode.ALLOCA
        ]
        for op in opcodes:
            assert hasattr(IROpcode, op.name)

class TestIROperandType:
    def test_all_types(self):
        types = [
            IROperandType.TEMPORARY,
            IROperandType.LITERAL,
            IROperandType.LABEL,
            IROperandType.VARIABLE,
            IROperandType.GLOBAL
        ]
        for t in types:
            assert hasattr(IROperandType, t.name)
