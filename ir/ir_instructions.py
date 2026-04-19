# ir/ir_instructions.py
"""
Определения инструкций промежуточного представления (IR).
"""

from enum import Enum, auto
from typing import List, Optional, Union, Any
from dataclasses import dataclass, field


class IROpcode(Enum):
    """Коды операций IR."""
    # Arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()  # Унарный минус

    # Logical
    AND = auto()
    OR = auto()
    NOT = auto()
    XOR = auto()

    # Comparisons
    CMP_EQ = auto()
    CMP_NE = auto()
    CMP_LT = auto()
    CMP_LE = auto()
    CMP_GT = auto()
    CMP_GE = auto()

    # Memory
    LOAD = auto()
    STORE = auto()
    ALLOCA = auto()  # Выделение памяти на стеке
    GEP = auto()     # Get Element Pointer

    # Control Flow
    JUMP = auto()
    JUMP_IF = auto()
    JUMP_IF_NOT = auto()
    LABEL = auto()   # Метка (не инструкция, а часть блока)
    PHI = auto()

    # Function
    CALL = auto()
    RETURN = auto()
    PARAM = auto()

    # Data Movement
    MOVE = auto()


class IROperandType(Enum):
    """Типы операндов IR."""
    TEMPORARY = auto()   # t1, t2, ...
    VARIABLE = auto()    # x, y, ...
    LITERAL = auto()     # 42, 3.14, true
    LABEL = auto()       # L1, L2, ...
    MEMORY = auto()      # [t1], [t2+4]
    GLOBAL = auto()      # @global_var


@dataclass
class IROperand:
    """Операнд инструкции IR."""
    operand_type: IROperandType
    value: Any  # Имя, номер или литерал
    ir_type: Optional[Any] = None  # Тип из семантического анализатора

    # Для адресной арифметики (MEMORY)
    base: Optional[str] = None
    offset: int = 0

    def __str__(self) -> str:
        if self.operand_type == IROperandType.TEMPORARY:
            return f"%{self.value}".replace(" ", "_")
        elif self.operand_type == IROperandType.VARIABLE:
            return f"@{self.value}"
        elif self.operand_type == IROperandType.LITERAL:
            if isinstance(self.value, bool):
                return "true" if self.value else "false"
            elif isinstance(self.value, str):
                return f'"{self.value}"'
            return str(self.value)
        elif self.operand_type == IROperandType.LABEL:
            return f"{self.value}"
        elif self.operand_type == IROperandType.MEMORY:
            if self.offset != 0:
                return f"[{self.base} + {self.offset}]"
            return f"[{self.base}]"
        elif self.operand_type == IROperandType.GLOBAL:
            return f"@{self.value}"
        return str(self.value)

    def __repr__(self):
        return self.__str__()


@dataclass
class IRInstruction:
    """Базовый класс для всех инструкций IR."""
    opcode: IROpcode
    operands: List[IROperand] = field(default_factory=list)
    comment: Optional[str] = None  # Для отладки (связь с исходным кодом)

    def __str__(self) -> str:
        # Определяем, нужен ли dest
        if self.opcode in (IROpcode.ADD, IROpcode.SUB, IROpcode.MUL, IROpcode.DIV,
                           IROpcode.MOD, IROpcode.AND, IROpcode.OR, IROpcode.XOR,
                           IROpcode.CMP_EQ, IROpcode.CMP_NE, IROpcode.CMP_LT,
                           IROpcode.CMP_LE, IROpcode.CMP_GT, IROpcode.CMP_GE,
                           IROpcode.LOAD, IROpcode.ALLOCA, IROpcode.GEP, IROpcode.MOVE):
            if len(self.operands) >= 3:
                dest = self.operands[0]
                op1 = self.operands[1]
                op2 = self.operands[2]
                instr_str = f"{dest} = {self.opcode.name} {op1}, {op2}"
            elif len(self.operands) >= 2:
                dest = self.operands[0]
                op1 = self.operands[1]
                instr_str = f"{dest} = {self.opcode.name} {op1}"
            else:
                instr_str = f"{self.opcode.name} " + ", ".join(str(op) for op in self.operands)
        elif self.opcode in (IROpcode.NEG, IROpcode.NOT):
            if len(self.operands) >= 2:
                dest = self.operands[0]
                op1 = self.operands[1]
                instr_str = f"{dest} = {self.opcode.name} {op1}"
            else:
                instr_str = f"{self.opcode.name} " + ", ".join(str(op) for op in self.operands)
        elif self.opcode == IROpcode.STORE:
            addr = self.operands[0]
            src = self.operands[1] if len(self.operands) > 1 else ""
            instr_str = f"STORE {addr}, {src}"
        elif self.opcode == IROpcode.JUMP:
            label = self.operands[0]
            instr_str = f"JUMP {label}"
        elif self.opcode == IROpcode.JUMP_IF:
            cond = self.operands[0]
            label = self.operands[1]
            instr_str = f"JUMP_IF {cond}, {label}"
        elif self.opcode == IROpcode.JUMP_IF_NOT:
            cond = self.operands[0]
            label = self.operands[1]
            instr_str = f"JUMP_IF_NOT {cond}, {label}"
        elif self.opcode == IROpcode.CALL:
            if len(self.operands) >= 3:
                dest = self.operands[0]
                callee = self.operands[1]
                arg_count = self.operands[2]
                instr_str = f"{dest} = CALL {callee}, {arg_count}"
            else:
                instr_str = f"CALL " + ", ".join(str(op) for op in self.operands)
        elif self.opcode == IROpcode.RETURN:
            if self.operands:
                instr_str = f"RETURN {self.operands[0]}"
            else:
                instr_str = "RETURN"
        elif self.opcode == IROpcode.PARAM:
            idx = self.operands[0]
            val = self.operands[1]
            instr_str = f"PARAM {idx}, {val}"
        else:
            instr_str = f"{self.opcode.name} " + ", ".join(str(op) for op in self.operands)

        if self.comment:
            instr_str += f"  # {self.comment}"
        return instr_str.strip()


# ============= Фабрики для создания операндов =============

def Temp(name: Union[str, int], ir_type=None) -> IROperand:
    return IROperand(IROperandType.TEMPORARY, str(name), ir_type)


def Var(name: str, ir_type=None) -> IROperand:
    return IROperand(IROperandType.VARIABLE, name, ir_type)


def Lit(value: Any, ir_type=None) -> IROperand:
    return IROperand(IROperandType.LITERAL, value, ir_type)


def Label(name: str) -> IROperand:
    return IROperand(IROperandType.LABEL, name)


def Mem(base: str, offset: int = 0, ir_type=None) -> IROperand:
    return IROperand(IROperandType.MEMORY, None, ir_type, base, offset)


def Global(name: str, ir_type=None) -> IROperand:
    return IROperand(IROperandType.GLOBAL, name, ir_type)


# ============= Конкретные инструкции (для удобства) =============

class LabelInst(IRInstruction):
    """Инструкция-метка."""
    def __init__(self, name: str):
        super().__init__(IROpcode.LABEL, [Label(name)])
        self.name = name

    def __str__(self):
        return f"{self.name}:"


class PhiInst(IRInstruction):
    """PHI инструкция."""
    def __init__(self, dest: IROperand, sources: List[tuple]):
        """
        sources: список кортежей (значение, имя_блока)
        """
        super().__init__(IROpcode.PHI, [dest])
        self.sources = sources

    def __str__(self):
        dest = self.operands[0]
        sources_str = ", ".join(f"[ {val}, %{block} ]" for val, block in self.sources)
        return f"{dest} = PHI {sources_str}"