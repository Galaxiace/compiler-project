# ir/basic_block.py
"""
Представление базового блока.
"""

from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass, field
from .ir_instructions import IRInstruction, IROpcode, LabelInst, PhiInst


class BasicBlock:
    """
    Базовый блок в CFG.
    Содержит последовательность инструкций, заканчивающуюся терминатором.
    """

    def __init__(self, name: str, label: Optional[str] = None):
        self.name = name
        self.label = label if label else name
        self.instructions: List[IRInstruction] = []
        self.predecessors: Set['BasicBlock'] = set()
        self.successors: Set['BasicBlock'] = set()

        # Для анализа
        self.dominators: Set['BasicBlock'] = set()
        self.idom: Optional['BasicBlock'] = None  # Immediate dominator

    def add_instruction(self, instr: IRInstruction):
        """Добавляет инструкцию в блок."""
        self.instructions.append(instr)
        return instr

    def get_terminator(self) -> Optional[IRInstruction]:
        """Возвращает последнюю инструкцию, если она терминатор."""
        if not self.instructions:
            return None
        last = self.instructions[-1]
        if last.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT,
                           IROpcode.RETURN):
            return last
        return None

    def is_terminated(self) -> bool:
        """Проверяет, заканчивается ли блок терминатором."""
        return self.get_terminator() is not None

    def __str__(self) -> str:
        lines = [f"{self.label}:"]
        for instr in self.instructions:
            if isinstance(instr, LabelInst):
                continue  # Уже есть метка блока
            lines.append(f"  {instr}")
        return "\n".join(lines)

    def get_all_vars_used(self) -> Set[str]:
        """Возвращает множество всех переменных, используемых в блоке."""
        # Базовая реализация
        return set()