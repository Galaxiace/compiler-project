# ir/ir_writer.py
"""
Вывод IR в текстовом формате.
"""

from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock
from .ir_instructions import IRInstruction, LabelInst, PhiInst, IROpcode


class IRWriter:
    """Записывает IR в человеко-читаемом формате."""

    def __init__(self):
        self.output = []

    def write_program(self, program: IRProgram) -> str:
        self.output = []
        self._write_program(program)
        return "\n".join(self.output)

    def _write_program(self, program: IRProgram):
        self.output.append("# IR Program")
        self.output.append("")

        # Глобальные переменные
        if program.global_vars:
            self.output.append("# Global Variables")
            for name, var in program.global_vars.items():
                type_name = var.ir_type.name if var.ir_type else 'unknown'
                self.output.append(f"@global {name} : {type_name}")
            self.output.append("")

        # Функции
        for i, func in enumerate(program.functions):
            if i > 0:
                self.output.append("")
            self._write_function(func)

    def _write_function(self, func: IRFunction):
        params_str = []
        for p in func.parameters:
            type_name = p.ir_type.name if p.ir_type else '?'
            params_str.append(f"{p} : {type_name}")
        params = ", ".join(params_str)
        ret = func.return_type.name if func.return_type else "void"

        self.output.append(f"function {func.name}({params}) -> {ret} {{")

        for block in func.blocks:
            self._write_block(block)

        self.output.append("}")

    def _write_block(self, block: BasicBlock):
        # Метка блока
        self.output.append(f"{block.label}:")

        # Инструкции
        if block.instructions:
            for instr in block.instructions:
                if isinstance(instr, LabelInst):
                    continue
                elif isinstance(instr, PhiInst):
                    self.output.append(f"  {instr}")
                else:
                    self.output.append(f"  {instr}")
        else:
            self.output.append("  # empty block")