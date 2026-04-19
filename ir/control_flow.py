# ir/control_flow.py
"""
Управление Control Flow Graph (CFG) и функциями.
"""

from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from .basic_block import BasicBlock
from .ir_instructions import IRInstruction, IROpcode, IROperand, IROperandType, Temp


class IRFunction:
    """
    Представление функции в IR.
    """

    def __init__(self, name: str, return_type: Any = None):
        self.name = name
        self.return_type = return_type
        self.parameters: List[IROperand] = []
        self.blocks: List[BasicBlock] = []
        self.entry_block: Optional[BasicBlock] = None
        self.exit_block: Optional[BasicBlock] = None

        # Символьная таблица переменных -> временные
        self.var_to_temp: Dict[str, IROperand] = {}
        self.temp_counter = 0

        # Информация о типах
        self.local_vars: Dict[str, Any] = {}  # имя -> тип

    def new_temp(self, hint: str = "t", ir_type=None) -> IROperand:
        """Создает новый уникальный временный регистр."""
        self.temp_counter += 1
        return Temp(f"{hint}{self.temp_counter}", ir_type)

    def new_label(self, hint: str = "L") -> str:
        """Создает новую уникальную метку."""
        self.temp_counter += 1
        return f"{hint}{self.temp_counter}"

    def create_block(self, name: str = None) -> BasicBlock:
        """Создает и добавляет новый базовый блок."""
        if not name:
            name = self.new_label("B")
        block = BasicBlock(name)
        self.blocks.append(block)
        return block

    def set_entry(self, block: BasicBlock):
        self.entry_block = block

    def set_exit(self, block: BasicBlock):
        self.exit_block = block

    def add_edge(self, from_block: BasicBlock, to_block: BasicBlock):
        """Добавляет ребро CFG между блоками."""
        from_block.successors.add(to_block)
        to_block.predecessors.add(from_block)

    def __str__(self) -> str:
        params_str = ", ".join(str(p) for p in self.parameters)
        ret_str = str(self.return_type) if self.return_type else "void"
        lines = [f"function {self.name}({params_str}) -> {ret_str} {{"]
        for block in self.blocks:
            lines.append(str(block))
            lines.append("")
        lines.append("}")
        return "\n".join(lines)


class IRProgram:
    """
    Представление всей программы в IR.
    """

    def __init__(self):
        self.functions: List[IRFunction] = []
        self.global_vars: Dict[str, IROperand] = {}

    def add_function(self, func: IRFunction):
        self.functions.append(func)

    def __str__(self) -> str:
        lines = ["# IR Program", ""]
        # Глобальные переменные
        for name, var in self.global_vars.items():
            lines.append(f"@global {name} = {var}")
        if self.global_vars:
            lines.append("")
        # Функции
        for func in self.functions:
            lines.append(str(func))
            lines.append("")
        return "\n".join(lines)