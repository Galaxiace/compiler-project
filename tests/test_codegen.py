import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from codegen.x86_generator import X86Generator
from codegen.stack_frame import StackFrame
from ir.control_flow import IRProgram, IRFunction
from ir.basic_block import BasicBlock
from ir.ir_instructions import IRInstruction, IROpcode, IROperand, IROperandType, Temp, Lit, Label

class TestStackFrame:
    def test_allocate(self):
        sf = StackFrame()
        offset = sf.allocate("test_var", 4)
        assert offset is not None
        assert sf.get_offset("test_var") == offset

    def test_get_total_size(self):
        sf = StackFrame()
        sf.allocate("a", 4)
        sf.allocate("b", 8)
        assert sf.get_total_size() >= 12

    def test_multiple_allocations(self):
        sf = StackFrame()
        sf.allocate("x", 4)
        sf.allocate("y", 4)
        sf.allocate("z", 8)
        assert sf.get_offset("x") is not None
        assert sf.get_offset("y") is not None
        assert sf.get_offset("z") is not None

    def test_get_offset_nonexistent(self):
        sf = StackFrame()
        assert sf.get_offset("nonexistent") is None

class TestX86Generator:
    def test_generate_empty_program(self):
        program = IRProgram()
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'section .text' in asm

    def test_generate_simple_function(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%r1"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_arithmetic(self):
        program = IRProgram()
        func = IRFunction("add", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%r1"), Lit(2), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global add' in asm

    def test_generate_call(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.PARAM, [
            Lit(0), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.CALL, [
            Temp("%call1"), Lit("print_int")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'call print_int' in asm

    def test_generate_jump(self):
        program = IRProgram()
        func = IRFunction("loop", "int")
        entry = BasicBlock("entry")
        entry.add_instruction(IRInstruction(IROpcode.JUMP, [
            Label("loop_start")
        ]))
        loop = BasicBlock("loop_start")
        loop.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        func.blocks = [entry, loop]
        func.entry_block = entry
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'jmp' in asm.lower()

    def test_generate_comparison(self):
        program = IRProgram()
        func = IRFunction("cmp", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.CMP_LT, [
            Temp("%r1"), Lit(1), Lit(5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'setl' in asm or 'cmp' in asm

    def test_generate_multiple_blocks(self):
        program = IRProgram()
        func = IRFunction("test", "int")
        
        entry = BasicBlock("entry")
        entry.add_instruction(IRInstruction(IROpcode.JUMP_IF, [
            Lit(1), Label("then_block")
        ]))
        entry.add_instruction(IRInstruction(IROpcode.JUMP, [
            Label("else_block")
        ]))
        
        then_block = BasicBlock("then_block")
        then_block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(1)
        ]))
        
        else_block = BasicBlock("else_block")
        else_block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        
        func.blocks = [entry, then_block, else_block]
        func.entry_block = entry
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'then_block' in asm or 'test.then_block' in asm
        assert 'else_block' in asm or 'test.else_block' in asm

    def test_generate_store_load(self):
        program = IRProgram()
        func = IRFunction("test", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.STORE, [
            Temp("%addr"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.LOAD, [
            Temp("%val"), Temp("%addr")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%val")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global test' in asm

    def test_generate_sub(self):
        program = IRProgram()
        func = IRFunction("sub", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.SUB, [
            Temp("%r1"), Lit(10), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global sub' in asm

    def test_generate_mul(self):
        program = IRProgram()
        func = IRFunction("mul", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MUL, [
            Temp("%r1"), Lit(4), Lit(5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global mul' in asm

    def test_generate_neg(self):
        program = IRProgram()
        func = IRFunction("neg", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.NEG, [
            Temp("%r1"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global neg' in asm

    def test_generate_not(self):
        program = IRProgram()
        func = IRFunction("not_func", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.NOT, [
            Temp("%r1"), Lit(1)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global not_func' in asm

    def test_generate_and(self):
        program = IRProgram()
        func = IRFunction("and_func", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.AND, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global and_func' in asm

    def test_generate_or(self):
        program = IRProgram()
        func = IRFunction("or_func", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.OR, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global or_func' in asm

    def test_generate_xor(self):
        program = IRProgram()
        func = IRFunction("xor_func", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.XOR, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global xor_func' in asm

    def test_generate_mod(self):
        program = IRProgram()
        func = IRFunction("mod_func", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MOD, [
            Temp("%r1"), Lit(10), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global mod_func' in asm

    def test_generate_global_variable(self):
        program = IRProgram()
        from ir.ir_instructions import Global
        program.global_vars["g_var"] = Global("g_var", "int")
        
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.STORE, [
            Global("g_var"), Lit(42)
        ]))
        block.add_instruction(IRInstruction(IROpcode.LOAD, [
            Temp("%r1"), Global("g_var")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_string_literal(self):
        program = IRProgram()
        func = IRFunction("main", "void")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.PARAM, [
            Lit(0), Lit("Hello, World!")
        ]))
        block.add_instruction(IRInstruction(IROpcode.CALL, [
            Temp("%call1"), Lit("printf")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, []))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'str_0' in asm or 'Hello' in asm

    def test_generate_float_literal(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%f1"), Lit(3.14)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_float_add(self):
        program = IRProgram()
        func = IRFunction("fadd", "float")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.ADD, [
            Temp("%f1"), Lit(1.5), Lit(2.5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%f1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global fadd' in asm

    def test_generate_float_sub(self):
        program = IRProgram()
        func = IRFunction("fsub", "float")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.SUB, [
            Temp("%f1"), Lit(5.5), Lit(1.5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%f1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global fsub' in asm

    def test_generate_float_mul(self):
        program = IRProgram()
        func = IRFunction("fmul", "float")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MUL, [
            Temp("%f1"), Lit(2.0), Lit(3.0)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%f1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global fmul' in asm

    def test_generate_float_div(self):
        program = IRProgram()
        func = IRFunction("fdiv", "float")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.DIV, [
            Temp("%f1"), Lit(6.0), Lit(2.0)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%f1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global fdiv' in asm

    def test_generate_float_comparison(self):
        program = IRProgram()
        func = IRFunction("fcmp", "int")
        block = BasicBlock("entry")
        instr = IRInstruction(IROpcode.CMP_LT, [
            Temp("%r1"), Lit(1.5), Lit(2.5)
        ])
        instr.is_float_comparison = True
        block.add_instruction(instr)
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global fcmp' in asm

    def test_generate_jump_if_not(self):
        program = IRProgram()
        func = IRFunction("test", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.JUMP_IF_NOT, [
            Lit(0), Label("target")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'je' in asm or 'jmp' in asm.lower()

    def test_generate_multiple_params(self):
        program = IRProgram()
        func = IRFunction("many_params", "int")
        block = BasicBlock("entry")
        for i in range(8):
            block.add_instruction(IRInstruction(IROpcode.PARAM, [
                Lit(i), Lit(i * 10)
            ]))
        block.add_instruction(IRInstruction(IROpcode.CALL, [
            Temp("%call1"), Lit("sum_all")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%call1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global many_params' in asm

    def test_generate_extern_function(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.PARAM, [
            Lit(0), Lit("test message")
        ]))
        block.add_instruction(IRInstruction(IROpcode.CALL, [
            Temp("%call1"), Lit("external_func")
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Lit(0)
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'extern external_func' in asm

    def test_generate_bool_literal(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.MOVE, [
            Temp("%b1"), Lit(True)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%b1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_cmp_eq(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.CMP_EQ, [
            Temp("%r1"), Lit(5), Lit(5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_cmp_ne(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.CMP_NE, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_cmp_le(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.CMP_LE, [
            Temp("%r1"), Lit(5), Lit(5)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_cmp_ge(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.CMP_GE, [
            Temp("%r1"), Lit(5), Lit(3)
        ]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [
            Temp("%r1")
        ]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm

    def test_generate_global_vars_section(self):
        program = IRProgram()
        from ir.ir_instructions import Global
        program.global_vars["my_global"] = Global("my_global", "int")
        program.global_vars["my_float"] = Global("my_float", "float")
        
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.RETURN, [Lit(0)]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'section .bss' in asm or 'section .data' in asm
        assert 'my_global' in asm

    def test_generate_void_return(self):
        program = IRProgram()
        func = IRFunction("test", "void")
        block = BasicBlock("entry")
        block.add_instruction(IRInstruction(IROpcode.RETURN, []))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global test' in asm

    def test_generate_with_optimization_labels(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        
        entry = BasicBlock("entry")
        entry.add_instruction(IRInstruction(IROpcode.JUMP, [Label("target")]))
        
        target = BasicBlock("target")
        target.add_instruction(IRInstruction(IROpcode.RETURN, [Lit(42)]))
        
        func.blocks = [entry, target]
        func.entry_block = entry
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'main.target' in asm or 'target' in asm

    def test_generate_array_type(self):
        program = IRProgram()
        func = IRFunction("main", "int")
        block = BasicBlock("entry")
        from ir.ir_instructions import Temp
        # Создаём temp с типом-массивом
        t = Temp("%arr")
        block.add_instruction(IRInstruction(IROpcode.MOVE, [t, Lit(0)]))
        block.add_instruction(IRInstruction(IROpcode.RETURN, [Lit(0)]))
        func.blocks.append(block)
        func.entry_block = block
        program.functions.append(func)
        
        gen = X86Generator(program)
        asm = gen.generate()
        assert 'global main' in asm
