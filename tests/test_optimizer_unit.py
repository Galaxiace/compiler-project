import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ir.optimizer import ConstantFolder, ConstantPropagator, JumpOptimizer
from ir.control_flow import IRProgram, IRFunction
from ir.basic_block import BasicBlock
from ir.ir_instructions import IRInstruction, IROpcode, IROperand, IROperandType, Temp, Lit, Label

def make_program():
    program = IRProgram()
    func = IRFunction("test", "int")
    block = BasicBlock("entry")
    func.blocks.append(block)
    func.entry_block = block
    program.functions.append(func)
    return program, func, block

class TestConstantFolder:
    def test_fold_add(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(2), Lit(3)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.MOVE
        assert instr.operands[1].value == 5

    def test_fold_sub(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.SUB, [
            Temp("%r1"), Lit(10), Lit(3)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.operands[1].value == 7

    def test_fold_mul(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.MUL, [
            Temp("%r1"), Lit(4), Lit(5)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.operands[1].value == 20

    def test_fold_division_by_zero(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.DIV, [
            Temp("%r1"), Lit(5), Lit(0)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.DIV

    def test_fold_comparison_true(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.CMP_GT, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.MOVE
        assert instr.operands[1].value == 1

    def test_fold_comparison_false(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.CMP_EQ, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.MOVE
        assert instr.operands[1].value == 0

    def test_fold_neg(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.NEG, [
            Temp("%r1"), Lit(42)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.operands[1].value == -42

    def test_fold_not(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.NOT, [
            Temp("%r1"), Lit(1)
        ]))
        folder = ConstantFolder()
        result = folder.fold(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.operands[1].value == 0

class TestJumpOptimizer:
    def test_optimize_always_true(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.JUMP_IF, [
            Lit(1), Label("target")
        ]))
        opt = JumpOptimizer()
        result = opt.optimize(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.JUMP

    def test_optimize_always_false(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.JUMP_IF, [
            Lit(0), Label("target")
        ]))
        opt = JumpOptimizer()
        result = opt.optimize(program)
        assert len(result.functions[0].blocks[0].instructions) == 0

    def test_optimize_not_true(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.JUMP_IF_NOT, [
            Lit(0), Label("target")
        ]))
        opt = JumpOptimizer()
        result = opt.optimize(program)
        instr = result.functions[0].blocks[0].instructions[0]
        assert instr.opcode == IROpcode.JUMP

    def test_optimize_not_false(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.JUMP_IF_NOT, [
            Lit(1), Label("target")
        ]))
        opt = JumpOptimizer()
        result = opt.optimize(program)
        assert len(result.functions[0].blocks[0].instructions) == 0

class TestConstantPropagator:
    def test_propagate_simple(self):
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%x"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%y"), Temp("%x"), Lit(8)
        ]))
        prop = ConstantPropagator()
        result = prop.propagate(program)
        instr = result.functions[0].blocks[0].instructions[1]
        # %x должен быть заменён на 42
        assert instr.operands[1].operand_type == IROperandType.LITERAL
        assert instr.operands[1].value == 42

class TestIROptimizer:
    def test_optimize_pipeline(self):
        from ir.optimizer import IROptimizer
        program = IRProgram()
        func = IRFunction("test", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(10), Lit(20)
        ]))
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%x"), Temp("%r1")
        ]))
        block.add_instruction(IRInstruction(IROpcode.MUL, [
            Temp("%y"), Temp("%x"), Lit(2)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%y")
        ]))
        func.blocks = [block]
        func.entry_block = block
        program.functions = [func]
        
        opt = IROptimizer(program)
        result = opt.optimize(max_passes=3)
        stats = opt.get_stats()
        assert stats['total_instructions_before'] > stats['total_instructions_after']
        assert stats['constant_folding'] > 0

    def test_optimize_stats(self):
        from ir.optimizer import IROptimizer
        program = IRProgram()
        func = IRFunction("test", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks = [block]
        func.entry_block = block
        program.functions = [func]
        
        opt = IROptimizer(program)
        result = opt.optimize()
        stats = opt.get_stats()
        assert 'reduction_percent' in stats
        assert 'constant_folding' in stats
        assert 'total_instructions_before' in stats
        assert 'total_instructions_after' in stats

class TestDeadCodeEliminator:
    def test_eliminate_unused(self):
        from ir.optimizer import DeadCodeEliminator
        program, func, block = make_program()
        # Переменная, которая не используется
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%unused"), Lit(999)
        ]))
        # Используемая переменная
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%used"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%used")
        ]))
        
        dce = DeadCodeEliminator()
        result = dce.eliminate(program)
        # %unused должен быть удалён
        remaining_temps = []
        for b in result.functions[0].blocks:
            for i in b.instructions:
                if len(i.operands) > 0:
                    remaining_temps.append(i.operands[0].value)
        assert '%unused' not in remaining_temps

    def test_preserve_side_effects(self):
        from ir.optimizer import DeadCodeEliminator
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.PARAM, [Lit(0), Lit(42)]))
        block.add_instruction(IRInstruction(IROpcode.CALL, [
            Temp("%result"), Lit("external_func")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [Lit(0)]))
        
        dce = DeadCodeEliminator()
        result = dce.eliminate(program)
        # CALL должен сохраниться (side effect)
        has_call = any(
            i.opcode == IROpcode.CALL
            for b in result.functions[0].blocks
            for i in b.instructions
        )
        assert has_call

class TestIROptimizerPrintStats:
    def test_print_stats(self):
        from ir.optimizer import IROptimizer
        program, func, block = make_program()
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(1), Lit(2)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [Temp("%r1")]))
        
        opt = IROptimizer(program)
        opt.optimize()
        stats_str = opt.print_stats()
        assert 'Optimization Report' in stats_str
        assert 'Constant folding' in stats_str
